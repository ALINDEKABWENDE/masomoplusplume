from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("utilisateur_1", "utilisateur_2", "date_dernier_message")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("expediteur", "conversation", "date_envoi", "lu")
    search_fields = ("contenu",)
