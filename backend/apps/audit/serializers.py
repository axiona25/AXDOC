from rest_framework import serializers
from apps.authentication.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "user_id", "user_email", "action", "detail", "ip_address", "timestamp"]

    def get_user_email(self, obj):
        return obj.user.email if obj.user_id else None
