"""Modèle de données de MasomoPlus Plume (dictionnaire de données §3 du dossier)."""
from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def slug_unique(modele, base, pk=None, longueur=190):
    """Génère un slug unique pour `modele` à partir de `base`."""
    base = slugify(base)[: longueur - 8].strip("-") or "texte"
    slug, n = base, 2
    existants = modele.objects.all()
    if pk:
        existants = existants.exclude(pk=pk)
    while existants.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Categorie(models.Model):
    nom = models.CharField("nom", max_length=80, unique=True)
    description = models.TextField("description", blank=True)
    slug = models.SlugField("identifiant URL", max_length=100, unique=True, blank=True)
    icone = models.CharField(
        "icône", max_length=40, default="bi-tag", help_text="Classe Bootstrap Icons, par exemple bi-book"
    )
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unique(Categorie, self.nom, self.pk, 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class PublicationQuerySet(models.QuerySet):
    def publies(self):
        return self.filter(
            statut=self.model.Statut.PUBLIE, masquee=False, auteur__statut="actif"
        )

    def avec_compteurs(self):
        return self.annotate(
            nb_likes=Count("likes", distinct=True),
            nb_commentaires=Count(
                "commentaires", filter=Q(commentaires__statut="visible"), distinct=True
            ),
        )


class Publication(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        PUBLIE = "publie", "Publié"
        ARCHIVE = "archive", "Archivé"

    titre = models.CharField("titre", max_length=200)
    contenu = models.TextField("contenu")
    slug = models.SlugField("identifiant URL", max_length=200, unique=True, blank=True)
    statut = models.CharField("statut", max_length=10, choices=Statut.choices, default=Statut.BROUILLON)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    date_publication = models.DateTimeField("date de publication", null=True, blank=True)
    date_modification = models.DateTimeField("dernière modification", auto_now=True)
    nombre_vues = models.PositiveIntegerField("nombre de vues", default=0)
    masquee = models.BooleanField("masquée par la modération", default=False)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="publications", verbose_name="auteur"
    )
    categorie = models.ForeignKey(
        Categorie, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="publications", verbose_name="catégorie",
    )

    objects = PublicationQuerySet.as_manager()

    class Meta:
        ordering = ["-date_publication", "-date_creation"]
        verbose_name = "publication"
        verbose_name_plural = "publications"

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unique(Publication, self.titre, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("plume:detail", args=[self.slug])

    @property
    def temps_lecture(self):
        return max(1, round(len(self.contenu.split()) / 200))

    @property
    def est_en_ligne(self):
        return self.statut == self.Statut.PUBLIE and not self.masquee

    def verifier_publication(self):
        """MCT « Publication » : renvoie la liste des raisons pour lesquelles le texte n'est pas conforme."""
        erreurs = []
        if len((self.titre or "").strip()) < 3:
            erreurs.append("Ajoutez un titre d'au moins 3 caractères.")
        minimum = ParametreSite.charger().min_caracteres
        if len((self.contenu or "").strip()) < minimum:
            erreurs.append(f"Le texte doit contenir au moins {minimum} caractères pour être publié.")
        if not self.categorie_id:
            erreurs.append("Choisissez une catégorie avant de publier.")
        if self.masquee:
            erreurs.append("Ce texte a été masqué par la modération et ne peut pas être republié.")
        return erreurs

    def mettre_en_ligne(self):
        self.statut = self.Statut.PUBLIE
        if not self.date_publication:
            self.date_publication = timezone.now()


class Commentaire(models.Model):
    class Statut(models.TextChoices):
        VISIBLE = "visible", "Visible"
        MASQUE = "masque", "Masqué"
        SUPPRIME = "supprime", "Supprimé"

    contenu = models.TextField("commentaire")
    date_creation = models.DateTimeField("date de création", auto_now_add=True)
    statut = models.CharField("statut", max_length=10, choices=Statut.choices, default=Statut.VISIBLE)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commentaires"
    )
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="commentaires")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="reponses",
        verbose_name="commentaire parent",
    )

    class Meta:
        ordering = ["date_creation"]
        verbose_name = "commentaire"
        verbose_name_plural = "commentaires"

    def __str__(self):
        return f"{self.utilisateur} — {self.contenu[:40]}"


class Like(models.Model):
    """J'aime : un utilisateur ne peut aimer qu'une fois la même publication."""

    date_creation = models.DateTimeField(auto_now_add=True)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["utilisateur", "publication"], name="un_like_par_utilisateur")
        ]
        verbose_name = "J'aime"
        verbose_name_plural = "J'aime"

    def __str__(self):
        return f"{self.utilisateur} aime {self.publication}"


class Abonnement(models.Model):
    """Relation réflexive : un utilisateur (abonné) suit un auteur."""

    date_creation = models.DateTimeField(auto_now_add=True)
    abonne = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="abonnements"
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="abonnes"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["abonne", "auteur"], name="un_abonnement_par_auteur")
        ]
        verbose_name = "abonnement"
        verbose_name_plural = "abonnements"

    def __str__(self):
        return f"{self.abonne} suit {self.auteur}"


class Partage(models.Model):
    plateforme = models.CharField(max_length=30, default="autre")
    date_creation = models.DateTimeField(auto_now_add=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="partages"
    )
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="partages")

    class Meta:
        verbose_name = "partage"
        verbose_name_plural = "partages"

    def __str__(self):
        return f"{self.publication} → {self.plateforme}"


class Signalement(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        TRAITE = "traite", "Traité"
        REJETE = "rejete", "Rejeté"

    motif = models.ForeignKey(
        "MotifSignalement", on_delete=models.PROTECT, related_name="signalements", verbose_name="motif"
    )
    description = models.TextField("explication", blank=True)
    statut = models.CharField("statut", max_length=10, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_creation = models.DateTimeField("date du signalement", auto_now_add=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="signalements"
    )
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="signalements")
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    date_traitement = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "signalement"
        verbose_name_plural = "signalements"

    def __str__(self):
        return f"{self.motif.nom} — {self.publication}"


# ----------------------------------------------------------------------------
# Contenus configurables depuis la base de données (modifiables dans /gestion/)
# ----------------------------------------------------------------------------
class ParametreSite(models.Model):
    """Réglages uniques du site : textes d'identité et règles de publication."""

    nom_site = models.CharField("nom du site", max_length=60, default="Plume")
    sous_titre = models.CharField("marque / sous-titre", max_length=60, blank=True, default="MasomoPlus")
    slogan = models.CharField("titre de la page d'accueil", max_length=120, default="Ce que vous savez mérite d'être lu.")
    description = models.TextField(
        "texte d'introduction", default="Publiez vos textes, découvrez ceux des autres auteurs, commentez et partagez."
    )
    texte_pied = models.CharField(
        "texte du pied de page", max_length=200, default="Plateforme de publication et d'échange de textes"
    )
    min_caracteres = models.PositiveIntegerField("longueur minimale d'un texte publié (caractères)", default=100)
    textes_par_page = models.PositiveIntegerField("textes par page", default=9)

    class Meta:
        verbose_name = "paramètres du site"
        verbose_name_plural = "paramètres du site"

    def save(self, *args, **kwargs):
        self.pk = 1  # un seul enregistrement
        super().save(*args, **kwargs)

    @classmethod
    def charger(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def nom_complet(self):
        return f"{self.sous_titre} {self.nom_site}".strip()

    def __str__(self):
        return self.nom_complet


class PlateformePartage(models.Model):
    """Plateforme proposée dans le menu « Partager »."""

    cle = models.SlugField("clé", max_length=30, unique=True)
    nom = models.CharField("nom", max_length=60)
    icone = models.CharField("icône Bootstrap", max_length=40, default="bi-share")
    url_modele = models.CharField(
        "modèle de lien", max_length=500, help_text="Utilisez {url} et {titre}. Doit commencer par https://"
    )
    actif = models.BooleanField("actif", default=True)
    ordre = models.PositiveIntegerField("ordre", default=0)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "plateforme de partage"
        verbose_name_plural = "plateformes de partage"

    def lien(self, url_encodee, titre_encode):
        return self.url_modele.replace("{url}", url_encodee).replace("{titre}", titre_encode)

    def __str__(self):
        return self.nom


class MotifSignalement(models.Model):
    """Motif proposé lors du signalement d'un texte."""

    nom = models.CharField("motif", max_length=80, unique=True)
    actif = models.BooleanField("actif", default=True)
    ordre = models.PositiveIntegerField("ordre", default=0)

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "motif de signalement"
        verbose_name_plural = "motifs de signalement"

    def __str__(self):
        return self.nom
