from channels.generic.websocket import AsyncJsonWebsocketConsumer


class MessagerieConsumer(AsyncJsonWebsocketConsumer):
    """Chaque utilisateur connecté écoute son propre groupe « user_<id> »."""

    async def connect(self):
        utilisateur = self.scope.get("user")
        if utilisateur is None or not utilisateur.is_authenticated:
            await self.close(code=4401)
            return
        self.groupe = f"user_{utilisateur.pk}"
        await self.channel_layer.group_add(self.groupe, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "groupe"):
            await self.channel_layer.group_discard(self.groupe, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def nouveau_message(self, evenement):
        await self.send_json({"type": "message", "message": evenement["message"]})
