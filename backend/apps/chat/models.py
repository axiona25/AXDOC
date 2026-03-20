"""
Chat e videochiamata (FASE 13).
"""
import uuid
from django.db import models
from django.conf import settings


ROOM_TYPE = [
    ("direct", "Chat diretta 1-to-1"),
    ("group", "Chat di gruppo"),
    ("document", "Chat documento"),
    ("dossier", "Chat fascicolo"),
    ("protocol", "Chat protocollo"),
]


class ChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE)
    name = models.CharField(max_length=255, blank=True)
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chat_rooms",
    )
    dossier = models.ForeignKey(
        "dossiers.Dossier",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chat_rooms",
    )
    protocol = models.ForeignKey(
        "protocols.Protocol",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chat_rooms",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_chat_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"Chat {self.room_type} {self.id}"

    @classmethod
    def get_or_create_direct(cls, user1, user2):
        u1, u2 = user1.id, user2.id
        from django.db.models import Count
        direct_rooms = cls.objects.filter(room_type="direct", is_active=True).annotate(
            mc=Count("memberships"),
        ).filter(mc=2)
        for room in direct_rooms:
            user_ids = set(room.memberships.values_list("user_id", flat=True))
            if user_ids == {u1, u2}:
                return room
        room = cls.objects.create(room_type="direct", is_active=True)
        ChatMembership.objects.create(room=room, user_id=u1)
        ChatMembership.objects.create(room=room, user_id=u2)
        return room

    @classmethod
    def get_or_create_for_document(cls, document):
        room = cls.objects.filter(document=document, is_active=True).first()
        if room:
            return room
        room = cls.objects.create(room_type="document", document=document, name=f"Chat: {document.title[:100]}")
        if document.created_by_id:
            ChatMembership.objects.get_or_create(room=room, user=document.created_by, defaults={"is_admin": True})
        return room

    @classmethod
    def get_or_create_for_dossier(cls, dossier):
        room = cls.objects.filter(dossier=dossier, is_active=True).first()
        if room:
            return room
        room = cls.objects.create(room_type="dossier", dossier=dossier, name=f"Chat: {dossier.title[:100]}")
        if dossier.responsible_id:
            ChatMembership.objects.get_or_create(room=room, user=dossier.responsible, defaults={"is_admin": True})
        return room


class ChatMembership(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = [["room", "user"]]


class ChatMessage(models.Model):
    MESSAGE_TYPE = [
        ("text", "Testo"),
        ("file", "File"),
        ("image", "Immagine"),
        ("system", "Sistema"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_messages",
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE, default="text")
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="chat_files/%Y/%m/", null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    image = models.ImageField(upload_to="chat_images/%Y/%m/", null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )

    class Meta:
        ordering = ["sent_at"]


class UserPresence(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_presence",
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    current_room = models.ForeignKey(
        ChatRoom,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
