from django.core.management.base import BaseCommand

from comptes.models import Utilisateur
from plume.defauts import creer_valeurs_par_defaut
from plume.models import Categorie, Commentaire, Like, Abonnement, Publication

TEXTES = [
    ("amina", "Éducation", "Apprendre à lire, c'est apprendre à choisir",
     "Dans beaucoup de classes, la lecture reste un exercice scolaire avant d'être un plaisir. Pourtant, un enfant qui découvre "
     "qu'un livre peut raconter son quotidien change de rapport à l'école.\n\nLes bibliothèques de quartier, même modestes, font "
     "une différence immense. Quelques étagères, un adulte qui lit à voix haute et des histoires en langues locales suffisent à "
     "créer une habitude.\n\nLire, c'est aussi apprendre à douter, à comparer et à choisir. C'est une compétence civique autant que "
     "scolaire, et elle se cultive dès le plus jeune âge."),
    ("joseph", "Technologie", "Le téléphone, première salle de classe numérique",
     "Pour des millions de jeunes, le smartphone est le premier et parfois le seul accès à internet. Il serait absurde de "
     "l'ignorer quand on conçoit des outils d'apprentissage.\n\nDes cours courts, utilisables hors connexion et légers en données, "
     "changent la donne. Il faut penser pour l'écran de cinq pouces, pas pour l'ordinateur que l'on n'a pas.\n\nLa technologie "
     "éducative utile est simple, sobre et pensée avec ceux qui l'utilisent."),
    ("grace", "Entrepreneuriat", "Lancer son activité avec peu de moyens",
     "On croit souvent qu'il faut un gros capital pour démarrer. L'expérience de nombreux petits commerçants montre l'inverse : "
     "la première clé est de comprendre un besoin précis.\n\nCommencez petit, testez auprès de dix clients, notez ce qu'ils "
     "disent et ajustez. Chaque franc dépensé doit apprendre quelque chose.\n\nLa régularité compte plus que l'idée parfaite. "
     "Les entreprises durables se construisent client après client."),
    ("amina", "Poésie", "Lettre au lac au petit matin",
     "Le lac se lève avant nous, couvert de brume fine, et garde pour lui les secrets de la nuit. Nous marchons sur la rive "
     "comme on entre dans une prière sans mots.\n\nLes pêcheurs partent déjà, silhouettes minces sur l'eau argentée. Chaque "
     "geste répète un très vieux contrat entre les hommes et l'horizon.\n\nIci, le temps se mesure au rythme des vagues, "
     "et l'on repart avec la certitude simple d'avoir été accueilli."),
    ("joseph", "Opinion", "Pourquoi nos écoles ont besoin de plus d'écriture",
     "On évalue beaucoup, on fait peu écrire. Pourtant, écrire oblige à clarifier sa pensée, à hiérarchiser ses idées et à "
     "assumer une position.\n\nUn court texte hebdomadaire, lu et commenté par d'autres élèves, développerait l'esprit critique "
     "bien mieux qu'un énième questionnaire à choix multiples.\n\nDonner la parole écrite aux jeunes, c'est leur dire que leurs "
     "idées méritent d'être lues. Les plateformes de publication peuvent y contribuer."),
]


class Command(BaseCommand):
    help = "Crée les catégories de base. Avec --demo : comptes et textes d'exemple."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Ajoute des données d'exemple.")
        parser.add_argument("--vider-demo", action="store_true", dest="vider_demo",
                            help="Supprime les comptes et textes d'exemple (amina, joseph, grace, lecteur).")

    def handle(self, *args, **options):
        if options["vider_demo"]:
            supprimes, _ = Utilisateur.objects.filter(username__in=["amina", "joseph", "grace", "lecteur"]).delete()
            self.stdout.write(self.style.SUCCESS(f"Données d'exemple supprimées ({supprimes} enregistrements, textes et commentaires inclus)."))
            return
        creer_valeurs_par_defaut()
        self.stdout.write(self.style.SUCCESS("Réglages, catégories, plateformes de partage et motifs prêts."))
        if not options["demo"]:
            return

        if not Utilisateur.objects.filter(username="admin").exists():
            Utilisateur.objects.create_superuser(
                "admin", "admin@plume.local", "admin12345",
                first_name="Équipe", last_name="Plume", role=Utilisateur.Role.ADMINISTRATEUR,
            )
        comptes = {}
        for username, prenom, nom, bio in [
            ("amina", "Amina", "Kavira", "Enseignante et amoureuse des mots. J'écris sur l'école et la poésie."),
            ("joseph", "Joseph", "Mbusa", "Développeur et formateur. Je m'intéresse au numérique éducatif."),
            ("grace", "Grâce", "Neema", "Entrepreneure à Goma. Je partage ce que j'apprends."),
            ("lecteur", "Paul", "Lecteur", "Simple lecteur curieux."),
        ]:
            user, cree = Utilisateur.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@plume.local", "first_name": prenom, "last_name": nom,
                          "biographie": bio, "role": Utilisateur.Role.UTILISATEUR if username == "lecteur" else Utilisateur.Role.AUTEUR},
            )
            if cree:
                user.set_password("plume12345")
                user.save()
            comptes[username] = user

        for username, nom_cat, titre, contenu in TEXTES:
            if Publication.objects.filter(titre=titre).exists():
                continue
            pub = Publication(titre=titre, contenu=contenu, auteur=comptes[username],
                              categorie=Categorie.objects.get(nom=nom_cat))
            pub.mettre_en_ligne()
            pub.nombre_vues = 12 + len(titre)
            pub.save()
            for lecteur in ("lecteur", "grace", "joseph", "amina"):
                if comptes[lecteur] != pub.auteur:
                    Like.objects.get_or_create(utilisateur=comptes[lecteur], publication=pub)
            racine = Commentaire.objects.create(
                utilisateur=comptes["lecteur"], publication=pub, contenu="Merci pour ce texte, très inspirant !")
            Commentaire.objects.create(
                utilisateur=pub.auteur, publication=pub, parent=racine, contenu="Merci à vous pour votre lecture.")
        from messagerie.models import Conversation, Message
        conv = Conversation.entre(comptes["lecteur"], comptes["amina"])
        if not conv.messages.exists():
            Message.objects.create(conversation=conv, expediteur=comptes["lecteur"], contenu="Bonjour Amina, j'ai adoré votre texte sur la lecture !")
            Message.objects.create(conversation=conv, expediteur=comptes["amina"], contenu="Merci beaucoup, ça me fait très plaisir.", lu=True)
        for suiveur in ("lecteur", "grace"):
            for auteur in ("amina", "joseph"):
                Abonnement.objects.get_or_create(abonne=comptes[suiveur], auteur=comptes[auteur])
        self.stdout.write(self.style.SUCCESS(
            "Données d'exemple créées. Admin : admin / admin12345 — autres comptes : amina, joseph, grace, lecteur / plume12345"))
