from django.urls import path

from . import views

app_name = "plume"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("explorer/", views.recherche, name="recherche"),
    path("ecrire/", views.ecrire, name="ecrire"),
    path("mes-textes/", views.mes_textes, name="mes_textes"),
    path("texte/<slug:slug>/", views.detail, name="detail"),
    path("texte/<slug:slug>/modifier/", views.modifier, name="modifier"),
    path("texte/<slug:slug>/supprimer/", views.supprimer, name="supprimer"),
    path("texte/<slug:slug>/statut/<str:action>/", views.changer_statut, name="changer_statut"),
    path("texte/<slug:slug>/aimer/", views.aimer, name="aimer"),
    path("texte/<slug:slug>/commenter/", views.commenter, name="commenter"),
    path("texte/<slug:slug>/signaler/", views.signaler, name="signaler"),
    path("texte/<slug:slug>/partager/", views.partager, name="partager"),
    path("commentaire/<int:pk>/supprimer/", views.supprimer_commentaire, name="supprimer_commentaire"),
    path("auteur/<str:username>/", views.profil, name="profil"),
    path("auteur/<str:username>/suivre/", views.suivre, name="suivre"),
]
