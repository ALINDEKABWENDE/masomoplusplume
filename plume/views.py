"""Vues publiques et espace auteur de MasomoPlus Plume."""
from collections import Counter
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Exists, F, OuterRef, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from comptes.models import Utilisateur

from .forms import CommentaireForm, PublicationForm, SignalementForm
from .models import (
    Abonnement, Categorie, Commentaire, Like, ParametreSite, Partage, PlateformePartage, Publication, Signalement,
)



# --------------------------------------------------------------------------- outils
def _par_page():
    return ParametreSite.charger().textes_par_page


def _avec_etat_aime(qs, utilisateur):
    if utilisateur.is_authenticated:
        return qs.annotate(
            est_aime=Exists(
                Like.objects.filter(publication_id=OuterRef("pk"), utilisateur=utilisateur)
            )
        )
    return qs


def _est_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _qs(request, **changements):
    """Reconstruit la chaîne de requête courante en modifiant quelques paramètres."""
    params = request.GET.copy()
    params.pop("page", None)
    for cle, valeur in changements.items():
        if valeur in (None, ""):
            params.pop(cle, None)
        else:
            params[cle] = valeur
    chaine = params.urlencode()
    return f"?{chaine}" if chaine else "?"


def _params_sans_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def _arbre_commentaires(publication):
    """Charge les commentaires visibles en une requête et construit l'arbre des réponses."""
    commentaires = list(
        publication.commentaires.filter(statut=Commentaire.Statut.VISIBLE).select_related("utilisateur")
    )
    par_id = {c.pk: c for c in commentaires}
    for c in commentaires:
        c.enfants = []
    racines = []
    for c in commentaires:
        if c.parent_id is None:
            racines.append(c)
        elif c.parent_id in par_id:
            par_id[c.parent_id].enfants.append(c)
    return racines


def _liens_partage(request, pub):
    url = quote(request.build_absolute_uri(pub.get_absolute_url()), safe="")
    titre = quote(pub.titre, safe="")
    return [
        {"cle": p.cle, "nom": p.nom, "icone": p.icone, "url": p.lien(url, titre)}
        for p in PlateformePartage.objects.filter(actif=True)
    ]


def _contexte_liste(request):
    """Liste filtrable des textes publiés (accueil et recherche)."""
    qs = _avec_etat_aime(
        Publication.objects.publies().avec_compteurs().select_related("auteur", "categorie"),
        request.user,
    )
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("categorie", "").strip()
    tri = request.GET.get("tri", "recent")

    for terme in q.split():
        qs = qs.filter(
            Q(titre__icontains=terme)
            | Q(contenu__icontains=terme)
            | Q(auteur__username__icontains=terme)
            | Q(auteur__first_name__icontains=terme)
            | Q(auteur__last_name__icontains=terme)
            | Q(categorie__nom__icontains=terme)
        )
    categorie_active = None
    if cat:
        categorie_active = Categorie.objects.filter(slug=cat).first()
        qs = qs.filter(categorie__slug=cat)
    if tri == "suivis" and request.user.is_authenticated:
        qs = qs.filter(auteur_id__in=request.user.abonnements.values("auteur_id"))
    elif tri == "populaires":
        qs = qs.order_by("-nb_likes", "-nombre_vues", "-pk")
    else:
        tri = "recent"
        qs = qs.order_by("-date_publication", "-pk")

    onglets = [
        {"cle": "recent", "nom": "Récents", "icone": "bi-clock-history", "url": _qs(request, tri=None)},
        {"cle": "populaires", "nom": "Populaires", "icone": "bi-fire", "url": _qs(request, tri="populaires")},
    ]
    if request.user.is_authenticated:
        onglets.append({"cle": "suivis", "nom": "Abonnements", "icone": "bi-person-check", "url": _qs(request, tri="suivis")})

    page = Paginator(qs, _par_page()).get_page(request.GET.get("page"))
    return {
        "page_obj": page,
        "params": _params_sans_page(request),
        "q": q,
        "tri": tri,
        "categorie_active": categorie_active,
        "onglets": onglets,
        "url_toutes": _qs(request, categorie=None),
        "filtres_actifs": bool(q or cat or tri != "recent"),
    }


# --------------------------------------------------------------------------- lecture
def accueil(request):
    contexte = _contexte_liste(request)
    contexte["auteurs_suggeres"] = (
        Utilisateur.objects.filter(statut="actif", publications__statut="publie", publications__masquee=False)
        .annotate(
            nb_abonnes=Count("abonnes", distinct=True),
            nb_textes=Count("publications", filter=Q(publications__statut="publie"), distinct=True),
        )
        .order_by("-nb_abonnes", "-nb_textes")[:5]
    )
    return render(request, "plume/accueil.html", contexte)


def recherche(request):
    return render(request, "plume/recherche.html", _contexte_liste(request))


def detail(request, slug):
    pub = get_object_or_404(
        Publication.objects.avec_compteurs().select_related("auteur", "categorie"), slug=slug
    )
    user = request.user
    en_ligne = pub.est_en_ligne and pub.auteur.statut == "actif"
    if not en_ligne and not (user.is_authenticated and (user == pub.auteur or user.est_admin)):
        raise Http404("Texte introuvable")

    # Une vue est comptée une seule fois par session, jamais pour l'auteur.
    if en_ligne and user != pub.auteur:
        vues = request.session.get("vues", [])
        if pub.pk not in vues:
            Publication.objects.filter(pk=pub.pk).update(nombre_vues=F("nombre_vues") + 1)
            pub.nombre_vues += 1
            request.session["vues"] = (vues + [pub.pk])[-200:]

    similaires = []
    if pub.categorie_id:
        similaires = list(
            _avec_etat_aime(
                Publication.objects.publies().avec_compteurs().select_related("auteur", "categorie"),
                user,
            )
            .filter(categorie=pub.categorie).exclude(pk=pub.pk).order_by("-date_publication")[:3]
        )

    return render(request, "plume/detail.html", {
        "pub": pub,
        "apercu": not en_ligne,
        "commentaires": _arbre_commentaires(pub),
        "form_commentaire": CommentaireForm(),
        "form_signalement": SignalementForm(),
        "liens_partage": _liens_partage(request, pub),
        "url_absolue": request.build_absolute_uri(pub.get_absolute_url()),
        "est_aime": user.is_authenticated and pub.likes.filter(utilisateur=user).exists(),
        "est_abonne": user.is_authenticated and Abonnement.objects.filter(abonne=user, auteur=pub.auteur).exists(),
        "nb_abonnes": pub.auteur.abonnes.count(),
        "nb_partages": pub.partages.count(),
        "similaires": similaires,
    })


def profil(request, username):
    auteur = get_object_or_404(Utilisateur, username=username, statut="actif")
    textes = Publication.objects.publies().filter(auteur=auteur)
    liste = _avec_etat_aime(
        textes.avec_compteurs().select_related("auteur", "categorie"), request.user
    ).order_by("-date_publication")
    page = Paginator(liste, _par_page()).get_page(request.GET.get("page"))
    return render(request, "plume/profil.html", {
        "auteur": auteur,
        "page_obj": page,
        "params": _params_sans_page(request),
        "nb_textes": textes.count(),
        "nb_abonnes": auteur.abonnes.count(),
        "nb_abonnements": auteur.abonnements.count(),
        "nb_likes": Like.objects.filter(publication__in=textes).count(),
        "est_abonne": request.user.is_authenticated
        and Abonnement.objects.filter(abonne=request.user, auteur=auteur).exists(),
    })


# --------------------------------------------------------------------------- interactions
@login_required
@require_POST
def aimer(request, slug):
    pub = get_object_or_404(Publication.objects.publies(), slug=slug)
    like, cree = Like.objects.get_or_create(utilisateur=request.user, publication=pub)
    if not cree:
        like.delete()
    if _est_ajax(request):
        return JsonResponse({"actif": cree, "total": pub.likes.count()})
    return redirect(pub)


@login_required
@require_POST
def suivre(request, username):
    auteur = get_object_or_404(Utilisateur, username=username, statut="actif")
    if auteur == request.user:
        if _est_ajax(request):
            return JsonResponse({"erreur": "Vous ne pouvez pas vous suivre vous-même."}, status=400)
        messages.error(request, "Vous ne pouvez pas vous suivre vous-même.")
        return redirect(auteur)
    abonnement, cree = Abonnement.objects.get_or_create(abonne=request.user, auteur=auteur)
    if not cree:
        abonnement.delete()
    if _est_ajax(request):
        return JsonResponse({"actif": cree, "total": auteur.abonnes.count()})
    return redirect(request.POST.get("next") or auteur)


@login_required
@require_POST
def commenter(request, slug):
    pub = get_object_or_404(Publication.objects.publies(), slug=slug)
    form = CommentaireForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Écrivez un commentaire (2000 caractères maximum) avant de l'envoyer.")
        return redirect(pub)
    commentaire = form.save(commit=False)
    commentaire.utilisateur = request.user
    commentaire.publication = pub
    parent_id = request.POST.get("parent", "")
    if parent_id.isdigit():
        commentaire.parent = Commentaire.objects.filter(
            pk=int(parent_id), publication=pub, statut=Commentaire.Statut.VISIBLE
        ).first()
    commentaire.save()
    messages.success(request, "Commentaire publié.")
    return redirect(f"{pub.get_absolute_url()}#commentaire-{commentaire.pk}")


@login_required
@require_POST
def supprimer_commentaire(request, pk):
    commentaire = get_object_or_404(Commentaire.objects.select_related("publication"), pk=pk)
    pub = commentaire.publication
    user = request.user
    if user == commentaire.utilisateur or user == pub.auteur or user.est_admin:
        commentaire.statut = Commentaire.Statut.SUPPRIME
        commentaire.save(update_fields=["statut"])
        messages.success(request, "Commentaire supprimé.")
    else:
        messages.error(request, "Vous ne pouvez pas supprimer ce commentaire.")
    return redirect(f"{pub.get_absolute_url()}#commentaires")


@login_required
@require_POST
def signaler(request, slug):
    pub = get_object_or_404(Publication.objects.publies(), slug=slug)
    if pub.auteur == request.user:
        messages.info(request, "Vous ne pouvez pas signaler votre propre texte.")
        return redirect(pub)
    form = SignalementForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choisissez un motif pour envoyer votre signalement.")
        return redirect(pub)
    if Signalement.objects.filter(
        utilisateur=request.user, publication=pub, statut=Signalement.Statut.EN_ATTENTE
    ).exists():
        messages.info(request, "Vous avez déjà signalé ce texte : il est en cours d'examen.")
        return redirect(pub)
    signalement = form.save(commit=False)
    signalement.utilisateur = request.user
    signalement.publication = pub
    signalement.save()
    messages.success(request, "Merci. Votre signalement a été transmis à l'équipe de modération.")
    return redirect(pub)


@require_POST
def partager(request, slug):
    pub = get_object_or_404(Publication.objects.publies(), slug=slug)
    plateforme = request.POST.get("plateforme", "autre")
    if plateforme not in ("lien", "autre") and not PlateformePartage.objects.filter(cle=plateforme).exists():
        plateforme = "autre"
    Partage.objects.create(
        publication=pub,
        plateforme=plateforme,
        utilisateur=request.user if request.user.is_authenticated else None,
    )
    return JsonResponse({"ok": True, "total": pub.partages.count()})


# --------------------------------------------------------------------------- espace auteur
def _editeur(request, instance=None):
    """Création et modification d'un texte (MCT « Publication d'un texte »)."""
    action = request.POST.get("action", "brouillon")
    form = PublicationForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        pub = form.save(commit=False)
        nouveau = pub.pk is None
        if nouveau:
            pub.auteur = request.user
        if action == "publier":
            erreurs = pub.verifier_publication()
            if erreurs:
                for erreur in erreurs:
                    form.add_error(None, erreur)
            else:
                pub.mettre_en_ligne()
                pub.save()
                messages.success(request, "Texte publié.")
                return redirect(pub)
        else:
            pub.save()
            if nouveau and request.user.role == Utilisateur.Role.UTILISATEUR:
                request.user.role = Utilisateur.Role.AUTEUR
                request.user.save(update_fields=["role"])
            messages.success(
                request, "Brouillon enregistré." if pub.statut == Publication.Statut.BROUILLON else "Modifications enregistrées."
            )
            return redirect("plume:modifier", slug=pub.slug)
    return render(request, "plume/editeur.html", {"form": form, "pub": instance})


@login_required
def ecrire(request):
    return _editeur(request)


@login_required
def modifier(request, slug):
    pub = get_object_or_404(Publication, slug=slug, auteur=request.user)
    return _editeur(request, pub)


@login_required
@require_POST
def changer_statut(request, slug, action):
    pub = get_object_or_404(Publication, slug=slug, auteur=request.user)
    if action == "publier":
        erreurs = pub.verifier_publication()
        if erreurs:
            messages.error(request, " ".join(erreurs))
            return redirect("plume:modifier", slug=pub.slug)
        pub.mettre_en_ligne()
        messages.success(request, "Texte publié.")
    elif action == "depublier":
        pub.statut = Publication.Statut.BROUILLON
        messages.success(request, "Texte dépublié : il est redevenu un brouillon.")
    elif action == "archiver":
        pub.statut = Publication.Statut.ARCHIVE
        messages.success(request, "Texte archivé.")
    else:
        raise Http404
    pub.save()
    return redirect(request.POST.get("next") or "plume:mes_textes")


@login_required
def supprimer(request, slug):
    pub = get_object_or_404(Publication, slug=slug, auteur=request.user)
    if request.method == "POST":
        pub.delete()
        messages.success(request, "Texte supprimé.")
        return redirect("plume:mes_textes")
    return render(request, "plume/supprimer.html", {"pub": pub})


@login_required
def mes_textes(request):
    """Textes de l'auteur et statistiques (cas d'utilisation « Consulter les statistiques de ses textes »)."""
    base = (
        Publication.objects.filter(auteur=request.user)
        .avec_compteurs()
        .annotate(nb_partages=Count("partages", distinct=True))
        .select_related("categorie")
        .order_by("-date_modification")
    )
    tous = list(base)
    onglet = request.GET.get("statut", "")
    liste = [p for p in tous if not onglet or p.statut == onglet]
    totaux = {
        "vues": sum(p.nombre_vues for p in tous),
        "likes": sum(p.nb_likes for p in tous),
        "commentaires": sum(p.nb_commentaires for p in tous),
        "partages": sum(p.nb_partages for p in tous),
        "abonnes": request.user.abonnes.count(),
    }
    return render(request, "plume/mes_textes.html", {
        "textes": liste,
        "onglet": onglet,
        "compteurs": Counter(p.statut for p in tous),
        "nb_total": len(tous),
        "totaux": totaux,
    })
