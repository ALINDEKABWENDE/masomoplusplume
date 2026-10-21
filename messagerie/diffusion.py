"""Diffusion temps réel via Django Channels (silencieuse si Channels n'est pas installé)."""


def diffuser(message, identifiants):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        couche = get_channel_layer()
        if couche is None:
            return
        for uid in identifiants:
            async_to_sync(couche.group_send)(f"user_{uid}", {"type": "nouveau.message", "message": message})
    except Exception:  # le message est déjà enregistré ; le sondage prendra le relais
        pass
