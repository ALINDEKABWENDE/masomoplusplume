from django.db.models import Count, Q

from .models import Categorie, ParametreSite, Publication, Signalement


def globales(request):
    """Variables disponibles dans tous les gabarits."""
    contexte = {
        "site": ParametreSite.charger(),
        "categories_nav": Categorie.objects.annotate(
            nb=Count("publications", filter=Q(publications__statut=Publication.Statut.PUBLIE, publications__masquee=False))
        ).order_by("nom"),
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.est_admin:
        contexte["nb_signalements_attente"] = Signalement.objects.filter(
            statut=Signalement.Statut.EN_ATTENTE
        ).count()
    return contexte
