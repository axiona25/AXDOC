from django.contrib import admin
from .models import ChatRoom, ChatMessage, ChatMembership, UserPresence


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["id", "room_type", "name", "created_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "sender", "message_type", "sent_at"]


@admin.register(ChatMembership)
class ChatMembershipAdmin(admin.ModelAdmin):
    list_display = ["room", "user", "joined_at", "last_read_at"]


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ["user", "is_online", "last_seen"]
