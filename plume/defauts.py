"""Valeurs initiales des contenus configurables (créées une seule fois, ensuite gérées en base)."""
from django.db.utils import OperationalError, ProgrammingError

CATEGORIES = [
    ("Éducation", "bi-mortarboard", "Apprendre, enseigner et transmettre."),
    ("Technologie", "bi-cpu", "Numérique, innovation et usages."),
    ("Société", "bi-people", "Vie collective, enjeux et débats."),
    ("Entrepreneuriat", "bi-rocket-takeoff", "Créer, gérer et faire grandir un projet."),
    ("Recherche", "bi-lightbulb", "Travaux, méthodes et découvertes."),
    ("Littérature", "bi-book", "Récits, nouvelles et critiques."),
    ("Poésie", "bi-feather", "Vers, images et musique des mots."),
    ("Opinion", "bi-chat-quote", "Points de vue argumentés."),
    ("Culture", "bi-palette", "Arts, traditions et patrimoine."),
]

PLATEFORMES = [
    ("whatsapp", "WhatsApp", "bi-whatsapp", "https://wa.me/?text={titre}%20{url}"),
    ("facebook", "Facebook", "bi-facebook", "https://www.facebook.com/sharer/sharer.php?u={url}"),
    ("x", "X", "bi-twitter-x", "https://twitter.com/intent/tweet?text={titre}&url={url}"),
    ("linkedin", "LinkedIn", "bi-linkedin", "https://www.linkedin.com/sharing/share-offsite/?url={url}"),
    ("telegram", "Telegram", "bi-telegram", "https://t.me/share/url?url={url}&text={titre}"),
]

MOTIFS = [
    "Spam ou publicité", "Propos haineux ou violents", "Harcèlement",
    "Plagiat", "Contenu inapproprié", "Autre raison",
]


def creer_valeurs_par_defaut(sender=None, **kwargs):
    """Remplit les tables vides après `migrate` ; ne touche jamais aux données existantes."""
    from .models import Categorie, MotifSignalement, ParametreSite, PlateformePartage

    try:
        ParametreSite.charger()
        if not PlateformePartage.objects.exists():
            for i, (cle, nom, icone, modele) in enumerate(PLATEFORMES):
                PlateformePartage.objects.create(cle=cle, nom=nom, icone=icone, url_modele=modele, ordre=i)
        if not MotifSignalement.objects.exists():
            for i, nom in enumerate(MOTIFS):
                MotifSignalement.objects.create(nom=nom, ordre=i)
        if not Categorie.objects.exists():
            for nom, icone, description in CATEGORIES:
                Categorie.objects.create(nom=nom, icone=icone, description=description)
    except (OperationalError, ProgrammingError):
        pass  # tables pas encore créées
