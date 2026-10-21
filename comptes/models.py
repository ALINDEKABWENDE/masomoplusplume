from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class Utilisateur(AbstractUser):
    """Utilisateur de la plateforme (dictionnaire de données §3.1).

    nom -> last_name, prenom -> first_name, password -> haché par Django,
    date_inscription -> date_joined.
    """

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"
        SUPPRIME = "supprime", "Supprimé"

    class Role(models.TextChoices):
        UTILISATEUR = "utilisateur", "Utilisateur"
        AUTEUR = "auteur", "Auteur"
        ADMINISTRATEUR = "administrateur", "Administrateur"

    email = models.EmailField("adresse e-mail", unique=True)
    photo_profil = models.ImageField("photo de profil", upload_to="profils/", blank=True, null=True)
    biographie = models.TextField("biographie", max_length=500, blank=True)
    profession = models.CharField("profession ou domaine", max_length=100, blank=True)
    localisation = models.CharField("ville / pays", max_length=100, blank=True)
    site_web = models.URLField("site web", blank=True)
    statut = models.CharField("statut", max_length=10, choices=Statut.choices, default=Statut.ACTIF)
    role = models.CharField("rôle", max_length=14, choices=Role.choices, default=Role.UTILISATEUR)

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def save(self, *args, **kwargs):
        # Un compte suspendu ou supprimé ne peut plus se connecter.
        self.is_active = self.statut == self.Statut.ACTIF
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse("plume:profil", args=[self.username])

    @property
    def nom_affiche(self):
        return self.get_full_name().strip() or self.username

    @property
    def initiales(self):
        if self.first_name and self.last_name:
            return (self.first_name[0] + self.last_name[0]).upper()
        return self.username[:2].upper()

    @property
    def date_inscription(self):
        return self.date_joined

    @property
    def est_admin(self):
        return self.is_superuser or self.role == self.Role.ADMINISTRATEUR

    @property
    def est_auteur(self):
        return self.role == self.Role.AUTEUR or self.est_admin
