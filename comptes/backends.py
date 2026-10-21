from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOuUsernameBackend(ModelBackend):
    """Permet de se connecter avec son nom d'utilisateur OU son e-mail."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        Utilisateur = get_user_model()
        if username is None:
            username = kwargs.get(Utilisateur.USERNAME_FIELD)
        if not username or password is None:
            return None
        user = (
            Utilisateur.objects.filter(Q(username__iexact=username) | Q(email__iexact=username))
            .order_by("id")
            .first()
        )
        if user is None:
            Utilisateur().set_password(password)  # limite les attaques par chronométrage
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
