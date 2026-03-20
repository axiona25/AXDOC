from rest_framework import serializers
from .models import ChatRoom, ChatMessage, ChatMembership, UserPresence


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id", "room", "sender_id", "sender_email", "message_type", "content",
            "file", "file_name", "file_size", "image", "sent_at", "edited_at",
            "reply_to_id",
        ]

    def get_sender_email(self, obj):
        return obj.sender.email if obj.sender_id else None


class ChatMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = ChatMembership
        fields = ["user_id", "user_email", "joined_at", "last_read_at", "is_admin", "is_online"]

    def get_user_email(self, obj):
        return obj.user.email if obj.user_id else None

    def get_is_online(self, obj):
        try:
            return UserPresence.objects.filter(user_id=obj.user_id).values_list("is_online", flat=True).first() or False
        except Exception:
            return False


class ChatRoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id", "room_type", "name", "document_id", "dossier_id", "protocol_id",
            "created_at", "last_message", "unread_count", "members",
        ]

    def get_last_message(self, obj):
        last = obj.messages.filter(is_deleted=False).order_by("-sent_at").first()
        if not last:
            return None
        return {
            "id": str(last.id),
            "content": (last.content or "")[:100],
            "sender_id": str(last.sender_id) if last.sender_id else None,
            "sent_at": last.sent_at.isoformat(),
        }

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return 0
        mem = obj.memberships.filter(user=request.user).first()
        if not mem or not mem.last_read_at:
            return obj.messages.filter(is_deleted=False).count()
        return obj.messages.filter(is_deleted=False, sent_at__gt=mem.last_read_at).count()

    def get_members(self, obj):
        return ChatMembershipSerializer(obj.memberships.all(), many=True).data
