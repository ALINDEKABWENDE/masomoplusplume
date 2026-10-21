from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from plume.models import ParametreSite

from .forms import ConnexionForm, InscriptionForm, MotDePasseForm, ProfilForm


class ConnexionView(LoginView):
    template_name = "comptes/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True


def inscription(request):
    """MCT « Inscription » : vérifier les données, créer le compte, envoyer la confirmation."""
    if request.user.is_authenticated:
        return redirect("plume:accueil")
    form = InscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        site = ParametreSite.charger()
        send_mail(
            f"Bienvenue sur {site.nom_complet}",
            f"Bonjour {user.nom_affiche},\n\nVotre compte {site.nom_complet} est activé. "
            f"Vous pouvez dès maintenant lire, commenter et publier des textes.\n\nL'équipe {site.nom_site}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
        login(request, user, backend="comptes.backends.EmailOuUsernameBackend")
        messages.success(
            request, f"Bienvenue sur {site.nom_site} ! Ajoutez une photo et présentez-vous pour que les autres vous reconnaissent."
        )
        return redirect("comptes:modifier_profil")
    return render(request, "comptes/inscription.html", {"form": form})


@login_required
def modifier_profil(request):
    form = ProfilForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil mis à jour." + (" Votre photo est enregistrée." if request.FILES.get("photo_profil") else ""))
        return redirect("plume:profil", username=request.user.username)
    return render(request, "comptes/profil_form.html", {"form": form})


class MotDePasseView(PasswordChangeView):
    template_name = "comptes/mot_de_passe.html"
    form_class = MotDePasseForm
    success_url = reverse_lazy("comptes:modifier_profil")

    def form_valid(self, form):
        messages.success(self.request, "Mot de passe modifié.")
        return super().form_valid(form)
