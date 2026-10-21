from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from comptes.models import Utilisateur

from .diffusion import diffuser
from .models import Conversation, Message, compter_non_lus

LIMITE = 2000


def _serialiser(m):
    date = timezone.localtime(m.date_envoi)
    return {
        "id": m.pk,
        "conversation": m.conversation_id,
        "expediteur_id": m.expediteur_id,
        "expediteur": m.expediteur.nom_affiche,
        "contenu": m.contenu,
        "heure": date.strftime("%H:%M"),
        "url": reverse("messagerie:conversation", args=[m.conversation_id]),
    }


def _resumes(utilisateur):
    """Conversations de l'utilisateur avec dernier message et nombre de non-lus (tout vient de la base)."""
    dernier = Message.objects.filter(conversation=OuterRef("pk")).order_by("-id")
    conversations = list(
        Conversation.de(utilisateur)
        .select_related("utilisateur_1", "utilisateur_2")
        .annotate(
            dernier_contenu=Subquery(dernier.values("contenu")[:1]),
            dernier_expediteur=Subquery(dernier.values("expediteur_id")[:1]),
        )
        .order_by("-date_dernier_message")
    )
    non_lus = dict(
        Message.objects.filter(conversation__in=conversations, lu=False)
        .exclude(expediteur=utilisateur)
        .values_list("conversation_id")
        .annotate(n=Count("id"))
    )
    for c in conversations:
        c.autre_utilisateur = c.utilisateur_2 if c.utilisateur_1_id == utilisateur.pk else c.utilisateur_1
        c.non_lus = non_lus.get(c.pk, 0)
        c.dernier_moi = c.dernier_expediteur == utilisateur.pk
    return conversations


def _conversation_ou_404(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("utilisateur_1", "utilisateur_2"), pk=pk
    )
    if not conversation.a_pour_participant(request.user):
        raise Http404
    return conversation


@login_required
def liste(request):
    q = request.GET.get("q", "").strip()
    resultats, suggestions = [], []
    if q:
        resultats = (
            Utilisateur.objects.filter(statut="actif").exclude(pk=request.user.pk)
            .filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))[:12]
        )
    else:
        suggestions = (
            Utilisateur.objects.filter(statut="actif", abonnes__abonne=request.user)
            .exclude(pk=request.user.pk).distinct()[:8]
        )
    return render(request, "messagerie/liste.html", {
        "conversations": _resumes(request.user), "q": q, "resultats": resultats, "suggestions": suggestions,
    })


@login_required
def ouvrir(request, username):
    autre = get_object_or_404(Utilisateur, username=username, statut="actif")
    if autre == request.user:
        messages.info(request, "Vous ne pouvez pas vous écrire à vous-même.")
        return redirect("messagerie:liste")
    conversation = Conversation.entre(request.user, autre)
    return redirect("messagerie:conversation", pk=conversation.pk)


@login_required
def conversation(request, pk):
    conv = _conversation_ou_404(request, pk)
    conv.messages.filter(lu=False).exclude(expediteur=request.user).update(lu=True)
    recents = list(conv.messages.select_related("expediteur").order_by("-id")[:80])
    recents.reverse()
    return render(request, "messagerie/conversation.html", {
        "conv": conv,
        "autre": conv.autre(request.user),
        "messages_chat": recents,
        "conversations": _resumes(request.user),
    })


@login_required
@require_POST
def envoyer(request, pk):
    conv = _conversation_ou_404(request, pk)
    autre = conv.autre(request.user)
    contenu = request.POST.get("contenu", "").strip()
    if not contenu:
        return JsonResponse({"erreur": "Le message est vide."}, status=400)
    if len(contenu) > LIMITE:
        return JsonResponse({"erreur": f"{LIMITE} caractères maximum."}, status=400)
    if autre.statut != "actif":
        return JsonResponse({"erreur": "Cet utilisateur n'est plus disponible."}, status=403)
    message = Message.objects.create(conversation=conv, expediteur=request.user, contenu=contenu)
    Conversation.objects.filter(pk=conv.pk).update(date_dernier_message=message.date_envoi)
    donnees = _serialiser(message)
    diffuser(donnees, {request.user.pk, autre.pk})
    return JsonResponse({"message": donnees})


@login_required
def nouveaux(request, pk):
    """Sondage de secours : messages plus récents que `apres` (utilisé si les WebSocket sont indisponibles)."""
    conv = _conversation_ou_404(request, pk)
    apres = request.GET.get("apres", "0")
    apres = int(apres) if apres.isdigit() else 0
    liste_messages = list(conv.messages.filter(id__gt=apres).select_related("expediteur").order_by("id")[:100])
    conv.messages.filter(lu=False).exclude(expediteur=request.user).update(lu=True)
    return JsonResponse({"messages": [_serialiser(m) for m in liste_messages]})


@login_required
@require_POST
def lire(request, pk):
    conv = _conversation_ou_404(request, pk)
    conv.messages.filter(lu=False).exclude(expediteur=request.user).update(lu=True)
    return JsonResponse({"total": compter_non_lus(request.user)})


@login_required
def non_lus(request):
    return JsonResponse({"total": compter_non_lus(request.user)})
