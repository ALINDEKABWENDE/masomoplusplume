from django.urls import path

from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.tableau_de_bord, name="tableau"),
    path("utilisateurs/", views.utilisateurs, name="utilisateurs"),
    path("utilisateurs/<int:pk>/statut/<str:statut>/", views.utilisateur_statut, name="utilisateur_statut"),
    path("utilisateurs/<int:pk>/role/<str:role>/", views.utilisateur_role, name="utilisateur_role"),
    path("publications/", views.publications, name="publications"),
    path("publications/<int:pk>/<str:action>/", views.publication_action, name="publication_action"),
    path("commentaires/", views.commentaires, name="commentaires"),
    path("commentaires/<int:pk>/<str:action>/", views.commentaire_action, name="commentaire_action"),
    path("categories/", views.categories, name="categories"),
    path("categories/<int:pk>/modifier/", views.categorie_modifier, name="categorie_modifier"),
    path("categories/<int:pk>/supprimer/", views.categorie_supprimer, name="categorie_supprimer"),
    path("parametres/", views.parametres, name="parametres"),
    path("plateformes/", views.plateformes, name="plateformes"),
    path("motifs/", views.motifs, name="motifs"),
    path("referentiel/<str:cle>/<int:pk>/<str:action>/", views.referentiel_action, name="referentiel_action"),
    path("signalements/", views.signalements, name="signalements"),
    path("signalements/<int:pk>/<str:action>/", views.signalement_action, name="signalement_action"),
]
