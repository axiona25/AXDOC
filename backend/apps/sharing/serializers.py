"""
Serializers condivisione (FASE 11).
"""
from django.conf import settings
from rest_framework import serializers
from .models import ShareLink, ShareAccessLog


class ShareLinkSerializer(serializers.ModelSerializer):
    recipient_display = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = ShareLink
        fields = [
            "id", "token", "target_type", "document", "protocol",
            "recipient_type", "recipient_user", "recipient_email", "recipient_name",
            "recipient_display", "can_download", "password_protected",
            "expires_at", "max_accesses", "access_count",
            "is_active", "created_at", "last_accessed_at",
            "is_valid", "url",
        ]

    def get_recipient_display(self, obj):
        if obj.recipient_user:
            return obj.recipient_user.email
        return obj.recipient_email or "—"

    def get_is_valid(self, obj):
        return obj.is_valid()

    def get_url(self, obj):
        frontend = getattr(settings, "FRONTEND_URL", "") or ""
        return f"{frontend}/share/{obj.token}"


class ShareLinkCreateSerializer(serializers.Serializer):
    recipient_type = serializers.ChoiceField(choices=["internal", "external"])
    recipient_user_id = serializers.UUIDField(required=False, allow_null=True)
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    recipient_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    can_download = serializers.BooleanField(default=True)
    expires_in_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    max_accesses = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, data):
        if data["recipient_type"] == "internal":
            if not data.get("recipient_user_id"):
                raise serializers.ValidationError({"recipient_user_id": "Obbligatorio per utente interno."})
        else:
            if not (data.get("recipient_email") or "").strip():
                raise serializers.ValidationError({"recipient_email": "Obbligatorio per utente esterno."})
        return data


class PublicShareSerializer(serializers.Serializer):
    """Dati esposti al link pubblico (no sensibili)."""
    document = serializers.SerializerMethodField()
    shared_by = serializers.SerializerMethodField()
    can_download = serializers.BooleanField()
    expires_at = serializers.DateTimeField(allow_null=True)
    accesses_remaining = serializers.SerializerMethodField()

    def get_document(self, obj):
        if obj.document_id:
            return {
                "id": str(obj.document_id),
                "title": obj.document.title,
                "description": (obj.document.description or "")[:500],
                "status": obj.document.status,
                "current_version": obj.document.current_version,
            }
        if obj.protocol_id:
            return {
                "id": str(obj.protocol_id),
                "title": obj.protocol.subject or obj.protocol.protocol_id,
                "description": "",
                "status": "protocol",
                "current_version": 1,
            }
        return None

    def get_shared_by(self, obj):
        u = obj.shared_by
        return {"name": f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip() or u.email, "email": u.email}

    def get_accesses_remaining(self, obj):
        if obj.max_accesses is None:
            return None
        return max(0, obj.max_accesses - obj.access_count)


class ShareAccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareAccessLog
        fields = ["id", "accessed_at", "action", "ip_address"]
