from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "comptes"

urlpatterns = [
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", LogoutView.as_view(), name="deconnexion"),
    path("inscription/", views.inscription, name="inscription"),
    path("profil/modifier/", views.modifier_profil, name="modifier_profil"),
    path("mot-de-passe/", views.MotDePasseView.as_view(), name="mot_de_passe"),
]
