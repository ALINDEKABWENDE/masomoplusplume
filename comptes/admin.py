from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Utilisateur


class AjoutUtilisateurForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Utilisateur
        fields = ("username", "email")


class ModifUtilisateurForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    form = ModifUtilisateurForm
    add_form = AjoutUtilisateurForm
    fieldsets = UserAdmin.fieldsets + (("Plume", {"fields": ("photo_profil", "biographie", "statut", "role")}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ("email", "role")}),)
    list_display = ("username", "email", "role", "statut", "date_joined")
    list_filter = ("role", "statut", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
