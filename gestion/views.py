"""Espace d'administration : utilisateurs, publications, commentaires, catégories, signalements."""
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from comptes.models import Utilisateur
from django.db.models import ProtectedError

from plume.forms import CategorieForm, MotifSignalementForm, ParametreSiteForm, PlateformePartageForm
from plume.models import (
    Categorie, Commentaire, Like, MotifSignalement, ParametreSite, Partage, PlateformePartage, Publication, Signalement,
)

PAR_PAGE = 15


def admin_requis(vue):
    @wraps(vue)
    def _vue(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.est_admin:
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return _vue


def _retour(request, defaut):
    """Retourne à la page d'origine si elle est sûre."""
    suivant = request.POST.get("next", "")
    if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
        return redirect(suivant)
    return redirect(defaut)


def _page(request, qs):
    page = Paginator(qs, PAR_PAGE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()


def _serie(qs, champ, jours=14):
    """Nombre d'objets créés par jour sur les `jours` derniers jours."""
    fin = timezone.localdate()
    debut = fin - timedelta(days=jours - 1)
    lignes = (
        qs.filter(**{f"{champ}__date__gte": debut})
        .annotate(j=TruncDate(champ)).values("j").annotate(n=Count("pk")).order_by()
    )
    par_jour = {ligne["j"]: ligne["n"] for ligne in lignes}
    points = [{"jour": debut + timedelta(days=i)} for i in range(jours)]
    for p in points:
        p["n"] = par_jour.get(p["jour"], 0)
    maxi = max([p["n"] for p in points] + [1])
    for p in points:
        p["pct"] = round(p["n"] * 100 / maxi)
    return points


# --------------------------------------------------------------------------- tableau de bord
@admin_requis
def tableau_de_bord(request):
    publiees = Publication.objects.filter(statut=Publication.Statut.PUBLIE, masquee=False)
    stats = {
        "utilisateurs": Utilisateur.objects.exclude(statut="supprime").count(),
        "auteurs": Utilisateur.objects.filter(publications__isnull=False).distinct().count(),
        "publiees": publiees.count(),
        "brouillons": Publication.objects.filter(statut=Publication.Statut.BROUILLON).count(),
        "vues": publiees.aggregate(t=Sum("nombre_vues"))["t"] or 0,
        "likes": Like.objects.count(),
        "commentaires": Commentaire.objects.filter(statut="visible").count(),
        "partages": Partage.objects.count(),
        "signalements": Signalement.objects.filter(statut="en_attente").count(),
    }
    return render(request, "gestion/tableau.html", {
        "stats": stats,
        "serie_textes": _serie(Publication.objects.filter(date_publication__isnull=False), "date_publication"),
        "serie_inscrits": _serie(Utilisateur.objects.all(), "date_joined"),
        "derniers_inscrits": Utilisateur.objects.order_by("-date_joined")[:5],
        "top_textes": publiees.avec_compteurs().select_related("auteur").order_by("-nombre_vues")[:5],
    })


# --------------------------------------------------------------------------- utilisateurs
@admin_requis
def utilisateurs(request):
    qs = Utilisateur.objects.annotate(nb_textes=Count("publications", distinct=True)).order_by("-date_joined")
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    role = request.GET.get("role", "")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if statut:
        qs = qs.filter(statut=statut)
    if role:
        qs = qs.filter(role=role)
    page, params = _page(request, qs)
    return render(request, "gestion/utilisateurs.html", {
        "page_obj": page, "params": params, "q": q, "statut": statut, "role": role,
        "statuts": Utilisateur.Statut.choices, "roles": Utilisateur.Role.choices,
    })


@admin_requis
@require_POST
def utilisateur_statut(request, pk, statut):
    cible = get_object_or_404(Utilisateur, pk=pk)
    if statut not in Utilisateur.Statut.values:
        raise Http404
    if cible == request.user or cible.is_superuser:
        messages.error(request, "Ce compte ne peut pas être modifié depuis cette page.")
    else:
        cible.statut = statut
        cible.save()
        messages.success(request, f"Statut de @{cible.username} : {cible.get_statut_display().lower()}.")
    return _retour(request, "gestion:utilisateurs")


@admin_requis
@require_POST
def utilisateur_role(request, pk, role):
    cible = get_object_or_404(Utilisateur, pk=pk)
    if role not in Utilisateur.Role.values:
        raise Http404
    if cible == request.user or cible.is_superuser:
        messages.error(request, "Ce compte ne peut pas être modifié depuis cette page.")
    else:
        cible.role = role
        cible.save()
        messages.success(request, f"@{cible.username} est maintenant {cible.get_role_display().lower()}.")
    return _retour(request, "gestion:utilisateurs")


# --------------------------------------------------------------------------- publications
@admin_requis
def publications(request):
    qs = Publication.objects.avec_compteurs().select_related("auteur", "categorie").order_by("-date_modification")
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(auteur__username__icontains=q))
    if statut == "masquee":
        qs = qs.filter(masquee=True)
    elif statut:
        qs = qs.filter(statut=statut)
    page, params = _page(request, qs)
    return render(request, "gestion/publications.html", {
        "page_obj": page, "params": params, "q": q, "statut": statut,
        "statuts": Publication.Statut.choices,
    })


@admin_requis
@require_POST
def publication_action(request, pk, action):
    pub = get_object_or_404(Publication, pk=pk)
    if action == "masquer":
        pub.statut, pub.masquee = Publication.Statut.ARCHIVE, True
        pub.save()
        messages.success(request, "Publication masquée.")
    elif action == "restaurer":
        pub.masquee = False
        pub.statut = Publication.Statut.PUBLIE if pub.date_publication else Publication.Statut.BROUILLON
        pub.save()
        messages.success(request, "Publication restaurée.")
    elif action == "supprimer":
        pub.delete()
        messages.success(request, "Publication supprimée.")
    else:
        raise Http404
    return _retour(request, "gestion:publications")


# --------------------------------------------------------------------------- commentaires
@admin_requis
def commentaires(request):
    qs = Commentaire.objects.select_related("utilisateur", "publication").order_by("-date_creation")
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")
    if q:
        qs = qs.filter(Q(contenu__icontains=q) | Q(utilisateur__username__icontains=q))
    if statut:
        qs = qs.filter(statut=statut)
    page, params = _page(request, qs)
    return render(request, "gestion/commentaires.html", {
        "page_obj": page, "params": params, "q": q, "statut": statut,
        "statuts": Commentaire.Statut.choices,
    })


@admin_requis
@require_POST
def commentaire_action(request, pk, action):
    commentaire = get_object_or_404(Commentaire, pk=pk)
    nouveau = {"masquer": "masque", "afficher": "visible", "supprimer": "supprime"}.get(action)
    if nouveau is None:
        raise Http404
    commentaire.statut = nouveau
    commentaire.save(update_fields=["statut"])
    messages.success(request, "Commentaire mis à jour.")
    return _retour(request, "gestion:commentaires")


# --------------------------------------------------------------------------- catégories
@admin_requis
def categories(request):
    form = CategorieForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Catégorie ajoutée.")
        return redirect("gestion:categories")
    liste = Categorie.objects.annotate(nb=Count("publications")).order_by("nom")
    return render(request, "gestion/categories.html", {"form": form, "categories": liste})


@admin_requis
def categorie_modifier(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    form = CategorieForm(request.POST or None, instance=categorie)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Catégorie mise à jour.")
        return redirect("gestion:categories")
    return render(request, "gestion/categorie_form.html", {"form": form, "categorie": categorie})


@admin_requis
@require_POST
def categorie_supprimer(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    categorie.delete()
    messages.success(request, "Catégorie supprimée. Ses textes restent publiés sans catégorie.")
    return redirect("gestion:categories")


# --------------------------------------------------------------------------- signalements
@admin_requis
def signalements(request):
    statut = request.GET.get("statut", "en_attente")
    qs = Signalement.objects.select_related("motif", "utilisateur", "publication", "publication__auteur", "traite_par")
    if statut:
        qs = qs.filter(statut=statut)
    page, params = _page(request, qs)
    return render(request, "gestion/signalements.html", {
        "page_obj": page, "params": params, "statut": statut,
        "statuts": Signalement.Statut.choices,
    })


@admin_requis
@require_POST
def signalement_action(request, pk, action):
    """MCT « Modération » : rejeter le signalement, ou masquer la publication puis le clôturer."""
    signalement = get_object_or_404(Signalement.objects.select_related("publication"), pk=pk)
    maintenant = timezone.now()
    if action == "rejeter":
        signalement.statut = Signalement.Statut.REJETE
        signalement.traite_par, signalement.date_traitement = request.user, maintenant
        signalement.save()
        messages.success(request, "Signalement rejeté : le contenu est conforme.")
    elif action == "masquer":
        pub = signalement.publication
        pub.statut, pub.masquee = Publication.Statut.ARCHIVE, True
        pub.save()
        Signalement.objects.filter(publication=pub, statut=Signalement.Statut.EN_ATTENTE).update(
            statut=Signalement.Statut.TRAITE, traite_par=request.user, date_traitement=maintenant
        )
        messages.success(request, "Publication masquée et signalements clôturés.")
    else:
        raise Http404
    return _retour(request, "gestion:signalements")


# --------------------------------------------------------------------------- contenus dynamiques
@admin_requis
def parametres(request):
    form = ParametreSiteForm(request.POST or None, instance=ParametreSite.charger())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Paramètres du site enregistrés.")
        return redirect("gestion:parametres")
    return render(request, "gestion/parametres.html", {"form": form})


REFERENTIELS = {
    "plateformes": {
        "modele": PlateformePartage, "form": PlateformePartageForm, "titre": "Plateformes de partage",
        "intro": "Boutons du menu « Partager ». Le lien utilise {url} et {titre}.",
    },
    "motifs": {
        "modele": MotifSignalement, "form": MotifSignalementForm, "titre": "Motifs de signalement",
        "intro": "Choix proposés aux lecteurs qui signalent un texte.",
    },
}


def _referentiel(request, cle):
    conf = REFERENTIELS[cle]
    form = conf["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Élément ajouté.")
        return redirect(f"gestion:{cle}")
    return render(request, "gestion/referentiel.html", {
        "cle": cle, "titre": conf["titre"], "intro": conf["intro"],
        "form": form, "items": conf["modele"].objects.all(),
    })


@admin_requis
def plateformes(request):
    return _referentiel(request, "plateformes")


@admin_requis
def motifs(request):
    return _referentiel(request, "motifs")


@admin_requis
@require_POST
def referentiel_action(request, cle, pk, action):
    if cle not in REFERENTIELS:
        raise Http404
    element = get_object_or_404(REFERENTIELS[cle]["modele"], pk=pk)
    if action == "basculer":
        element.actif = not element.actif
        element.save()
        messages.success(request, "Élément activé." if element.actif else "Élément désactivé.")
    elif action == "supprimer":
        try:
            element.delete()
            messages.success(request, "Élément supprimé.")
        except ProtectedError:
            messages.error(request, "Cet élément est utilisé par des signalements : désactivez-le plutôt.")
    else:
        raise Http404
    return redirect(f"gestion:{cle}")
