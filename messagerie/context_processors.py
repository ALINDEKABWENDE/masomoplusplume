from .models import compter_non_lus


def messagerie(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return {"nb_messages_non_lus": compter_non_lus(user)}
    return {}
