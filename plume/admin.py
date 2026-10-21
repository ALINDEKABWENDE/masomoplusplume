from django.contrib import admin

from .models import (
    Abonnement, Categorie, Commentaire, Like, MotifSignalement, ParametreSite, Partage, PlateformePartage, Publication,
    Signalement,
)


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "icone", "date_creation")
    search_fields = ("nom",)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("titre", "auteur", "categorie", "statut", "masquee", "nombre_vues", "date_publication")
    list_filter = ("statut", "masquee", "categorie")
    search_fields = ("titre", "contenu", "auteur__username")
    prepopulated_fields = {}


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "publication", "statut", "date_creation")
    list_filter = ("statut",)


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    list_display = ("publication", "motif", "statut", "utilisateur", "date_creation")
    list_filter = ("statut", "motif")


admin.site.register(Like)
admin.site.register(Abonnement)
admin.site.register(Partage)

admin.site.register(ParametreSite)
admin.site.register(PlateformePartage)
admin.site.register(MotifSignalement)
