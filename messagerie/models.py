"""Messagerie privée entre deux utilisateurs."""
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Conversation(models.Model):
    """Conversation entre deux utilisateurs (utilisateur_1.pk < utilisateur_2.pk)."""

    utilisateur_1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_1")
    utilisateur_2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_2")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_dernier_message = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-date_dernier_message"]
        constraints = [models.UniqueConstraint(fields=["utilisateur_1", "utilisateur_2"], name="une_conversation_par_paire")]

    def __str__(self):
        return f"{self.utilisateur_1} ↔ {self.utilisateur_2}"

    @classmethod
    def entre(cls, a, b):
        premier, second = sorted([a, b], key=lambda u: u.pk)
        conversation, _ = cls.objects.get_or_create(utilisateur_1=premier, utilisateur_2=second)
        return conversation

    @classmethod
    def de(cls, utilisateur):
        return cls.objects.filter(Q(utilisateur_1=utilisateur) | Q(utilisateur_2=utilisateur))

    def a_pour_participant(self, utilisateur):
        return utilisateur.pk in (self.utilisateur_1_id, self.utilisateur_2_id)

    def autre(self, utilisateur):
        return self.utilisateur_2 if utilisateur.pk == self.utilisateur_1_id else self.utilisateur_1


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    expediteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_envoyes")
    contenu = models.TextField(max_length=2000)
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["conversation", "id"])]

    def __str__(self):
        return f"{self.expediteur}: {self.contenu[:40]}"


def compter_non_lus(utilisateur):
    return (
        Message.objects.filter(lu=False)
        .filter(Q(conversation__utilisateur_1=utilisateur) | Q(conversation__utilisateur_2=utilisateur))
        .exclude(expediteur=utilisateur)
        .count()
    )
