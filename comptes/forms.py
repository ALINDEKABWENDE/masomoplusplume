import uuid
from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from .models import Utilisateur


class BootstrapMixin:
    """Ajoute les classes Bootstrap à tous les champs d'un formulaire."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            widget = champ.widget
            if isinstance(widget, forms.CheckboxInput):
                classe = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                classe = "form-select"
            else:
                classe = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {classe}".strip()

    def full_clean(self):
        super().full_clean()
        for nom in (self._errors or {}):
            if nom in self.fields:
                widget = self.fields[nom].widget
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()


class InscriptionForm(BootstrapMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Utilisateur
        fields = ("first_name", "last_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].label = "Prénom"
        self.fields["last_name"].label = "Nom"
        self.fields["username"].label = "Nom d'utilisateur public"
        self.fields["username"].help_text = "Lettres, chiffres et @/./+/-/_ uniquement."
        self.fields["email"].label = "Adresse e-mail"
        self.fields["password1"].label = "Mot de passe"
        self.fields["password2"].label = "Confirmer le mot de passe"
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["first_name"].widget.attrs["autocomplete"] = "given-name"
        self.fields["last_name"].widget.attrs["autocomplete"] = "family-name"
        self.fields["email"].widget.attrs["autocomplete"] = "email"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Utilisateur.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return email


class ConnexionForm(BootstrapMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Nom d'utilisateur ou e-mail"
        self.fields["username"].widget.attrs.update({"autofocus": True, "autocomplete": "username"})
        self.fields["password"].label = "Mot de passe"


class ProfilForm(BootstrapMixin, forms.ModelForm):
    supprimer_photo = forms.BooleanField(required=False, label="Supprimer ma photo actuelle")

    class Meta:
        model = Utilisateur
        fields = ("first_name", "last_name", "profession", "localisation", "site_web",
                  "email", "photo_profil", "biographie")
        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
            "profession": "Profession ou domaine",
            "localisation": "Ville / pays",
            "site_web": "Site web",
            "email": "Adresse e-mail",
            "photo_profil": "Photo de profil",
            "biographie": "Biographie",
        }
        widgets = {
            "photo_profil": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp,image/gif", "class": "d-none"}),
            "biographie": forms.Textarea(attrs={"rows": 4, "maxlength": 500, "placeholder": "Présentez-vous en quelques lignes…"}),
            "profession": forms.TextInput(attrs={"placeholder": "Enseignant, étudiant, développeur…"}),
            "localisation": forms.TextInput(attrs={"placeholder": "Goma, RD Congo"}),
            "site_web": forms.URLInput(attrs={"placeholder": "https://"}),
        }

    def clean_photo_profil(self):
        photo = self.cleaned_data.get("photo_profil")
        if photo and hasattr(photo, "size") and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La photo ne doit pas dépasser 5 Mo.")
        return photo

    @staticmethod
    def _normaliser(fichier, utilisateur):
        """Redresse, recadre en carré 512×512 et compresse la photo (JPEG)."""
        image = Image.open(fichier)
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = ImageOps.fit(image, (512, 512), Image.LANCZOS)
        tampon = BytesIO()
        image.save(tampon, "JPEG", quality=85, optimize=True)
        return ContentFile(tampon.getvalue(), name=f"{utilisateur.pk}-{uuid.uuid4().hex[:8]}.jpg")

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        ancienne = None
        if utilisateur.pk:
            ancienne = Utilisateur.objects.filter(pk=utilisateur.pk).values_list("photo_profil", flat=True).first()
        nouvelle = self.files.get("photo_profil")
        if nouvelle:
            utilisateur.photo_profil = self._normaliser(nouvelle, utilisateur)
        elif self.cleaned_data.get("supprimer_photo"):
            utilisateur.photo_profil = None
        if commit:
            utilisateur.save()
            actuelle = utilisateur.photo_profil.name if utilisateur.photo_profil else None
            if ancienne and ancienne != actuelle:
                Utilisateur._meta.get_field("photo_profil").storage.delete(ancienne)
        return utilisateur


class MotDePasseForm(BootstrapMixin, PasswordChangeForm):
    pass
