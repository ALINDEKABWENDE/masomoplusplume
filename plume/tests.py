from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from comptes.models import Utilisateur

from .models import Categorie, Commentaire, Like, Publication


class InteractionsPublicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.auteur = Utilisateur.objects.create_user(
            username="auteur_test",
            email="auteur@example.com",
            password="motdepasse-test",
        )
        cls.lecteur = Utilisateur.objects.create_user(
            username="lecteur_test",
            email="lecteur@example.com",
            password="motdepasse-test",
        )
        cls.categorie = Categorie.objects.create(nom="Catégorie de test")
        cls.publication = Publication.objects.create(
            titre="Texte enregistré en base",
            contenu="Contenu du texte de test.",
            auteur=cls.auteur,
            categorie=cls.categorie,
            statut=Publication.Statut.PUBLIE,
            date_publication=timezone.now(),
        )

    def test_flux_affiche_publication_de_la_base_et_actions_cliquables(self):
        self.client.force_login(self.lecteur)

        response = self.client.get(reverse("plume:accueil"))

        self.assertContains(response, self.publication.titre)
        self.assertContains(
            response,
            reverse("plume:aimer", args=[self.publication.slug]),
        )
        self.assertContains(
            response,
            f'{self.publication.get_absolute_url()}#commentaires',
        )

    def test_j_aime_est_enregistre_et_bascule_en_ajax(self):
        self.client.force_login(self.lecteur)
        url = reverse("plume:aimer", args=[self.publication.slug])

        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"actif": True, "total": 1})
        self.assertTrue(
            Like.objects.filter(
                utilisateur=self.lecteur,
                publication=self.publication,
            ).exists()
        )

        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.json(), {"actif": False, "total": 0})
        self.assertFalse(Like.objects.filter(publication=self.publication).exists())

    def test_commentaire_est_enregistre_et_affiche_apres_envoi(self):
        self.client.force_login(self.lecteur)
        url = reverse("plume:commenter", args=[self.publication.slug])

        response = self.client.post(url, {"contenu": "Un commentaire de test."})

        self.assertEqual(response.status_code, 302)
        commentaire = Commentaire.objects.get(publication=self.publication)
        self.assertEqual(
            response.url,
            f"{self.publication.get_absolute_url()}#commentaire-{commentaire.pk}",
        )
        self.assertEqual(commentaire.utilisateur, self.lecteur)
        self.assertEqual(commentaire.contenu, "Un commentaire de test.")
