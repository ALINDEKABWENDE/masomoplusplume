from django.urls import path

from . import views

app_name = "messagerie"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("non-lus/", views.non_lus, name="non_lus"),
    path("avec/<str:username>/", views.ouvrir, name="ouvrir"),
    path("<int:pk>/", views.conversation, name="conversation"),
    path("<int:pk>/envoyer/", views.envoyer, name="envoyer"),
    path("<int:pk>/nouveaux/", views.nouveaux, name="nouveaux"),
    path("<int:pk>/lire/", views.lire, name="lire"),
]
