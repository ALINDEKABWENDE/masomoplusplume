from django import forms

from comptes.forms import BootstrapMixin

from .models import (
    Categorie, Commentaire, MotifSignalement, ParametreSite, PlateformePartage, Publication, Signalement,
)


class PublicationForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Publication
        fields = ("titre", "categorie", "contenu")
        labels = {"titre": "Titre", "categorie": "Catégorie", "contenu": "Votre texte"}
        widgets = {
            "titre": forms.TextInput(attrs={"placeholder": "Le titre de votre texte", "maxlength": 200, "class": "champ-titre"}),
            "contenu": forms.Textarea(attrs={"rows": 16, "placeholder": "Écrivez ici…", "class": "champ-texte", "data-compte-mots": ""}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categorie"].required = False
        self.fields["categorie"].empty_label = "Choisir une catégorie"


class CommentaireForm(BootstrapMixin, forms.ModelForm):
    contenu = forms.CharField(
        label="Votre commentaire", max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Partagez votre avis avec respect…", "aria-label": "Votre commentaire"}),
    )

    class Meta:
        model = Commentaire
        fields = ("contenu",)


class SignalementForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Signalement
        fields = ("motif", "description")
        labels = {"motif": "Motif du signalement", "description": "Explication (facultative)"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3, "placeholder": "Dites-nous ce qui pose problème."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["motif"].queryset = MotifSignalement.objects.filter(actif=True)
        self.fields["motif"].empty_label = "Choisir un motif"


class CategorieForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ("nom", "description", "icone")
        labels = {"nom": "Nom", "description": "Description", "icone": "Icône Bootstrap"}
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "icone": forms.TextInput(attrs={"placeholder": "bi-book"}),
        }

    def clean_icone(self):
        icone = (self.cleaned_data.get("icone") or "bi-tag").strip()
        if not icone.startswith("bi-") or not icone.replace("-", "").isalnum():
            raise forms.ValidationError("Utilisez une classe Bootstrap Icons, par exemple « bi-book ».")
        return icone


def _verifier_icone(valeur):
    valeur = (valeur or "bi-tag").strip()
    if not valeur.startswith("bi-") or not valeur.replace("-", "").isalnum():
        raise forms.ValidationError("Utilisez une classe Bootstrap Icons, par exemple « bi-book ».")
    return valeur


class ParametreSiteForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ParametreSite
        fields = ("nom_site", "sous_titre", "slogan", "description", "texte_pied", "min_caracteres", "textes_par_page")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_textes_par_page(self):
        valeur = self.cleaned_data["textes_par_page"]
        if not 3 <= valeur <= 50:
            raise forms.ValidationError("Choisissez une valeur entre 3 et 50.")
        return valeur


class PlateformePartageForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PlateformePartage
        fields = ("nom", "cle", "icone", "url_modele", "ordre", "actif")
        widgets = {"url_modele": forms.TextInput(attrs={"placeholder": "https://exemple.com/partager?u={url}&t={titre}"})}

    def clean_icone(self):
        return _verifier_icone(self.cleaned_data.get("icone"))

    def clean_url_modele(self):
        valeur = self.cleaned_data["url_modele"].strip()
        if not valeur.startswith("https://") or "{url}" not in valeur:
            raise forms.ValidationError("Le lien doit commencer par https:// et contenir {url}.")
        return valeur


class MotifSignalementForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = MotifSignalement
        fields = ("nom", "ordre", "actif")
