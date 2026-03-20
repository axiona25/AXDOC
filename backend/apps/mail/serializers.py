"""
Serializers per il modulo posta PEC/Email.
"""
from rest_framework import serializers

from .models import MailAccount, MailAttachment, MailMessage


class MailAccountSerializer(serializers.ModelSerializer):
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = MailAccount
        fields = [
            "id",
            "name",
            "account_type",
            "email_address",
            "imap_host",
            "imap_port",
            "imap_use_ssl",
            "smtp_host",
            "smtp_port",
            "smtp_use_ssl",
            "smtp_use_tls",
            "is_active",
            "is_default",
            "last_fetch_at",
            "unread_count",
            "created_at",
        ]
        read_only_fields = ["id", "last_fetch_at", "created_at"]

    def get_unread_count(self, obj):
        return obj.messages.filter(status="unread", direction="in").count()


class MailAccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MailAccount
        fields = [
            "name",
            "account_type",
            "email_address",
            "imap_host",
            "imap_port",
            "imap_use_ssl",
            "imap_username",
            "imap_password",
            "smtp_host",
            "smtp_port",
            "smtp_use_ssl",
            "smtp_use_tls",
            "smtp_username",
            "smtp_password",
            "is_default",
        ]


class MailAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MailAttachment
        fields = ["id", "filename", "content_type", "size", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class MailMessageListSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_type = serializers.CharField(source="account.account_type", read_only=True)
    attachment_count = serializers.SerializerMethodField()

    class Meta:
        model = MailMessage
        fields = [
            "id",
            "account",
            "account_name",
            "account_type",
            "direction",
            "from_address",
            "from_name",
            "to_addresses",
            "subject",
            "status",
            "is_starred",
            "has_attachments",
            "attachment_count",
            "sent_at",
            "folder",
            "protocol",
        ]

    def get_attachment_count(self, obj):
        return obj.attachments.count()


class MailMessageDetailSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_type = serializers.CharField(source="account.account_type", read_only=True)
    attachments = MailAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = MailMessage
        fields = [
            "id",
            "account",
            "account_name",
            "account_type",
            "direction",
            "message_id",
            "in_reply_to",
            "from_address",
            "from_name",
            "to_addresses",
            "cc_addresses",
            "bcc_addresses",
            "subject",
            "body_text",
            "body_html",
            "has_attachments",
            "attachments",
            "status",
            "is_starred",
            "folder",
            "sent_at",
            "fetched_at",
            "protocol",
        ]


class SendMailSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    to = serializers.ListField(child=serializers.EmailField(), min_length=1)
    cc = serializers.ListField(child=serializers.EmailField(), required=False, default=list)
    bcc = serializers.ListField(child=serializers.EmailField(), required=False, default=list)
    subject = serializers.CharField(max_length=1000)
    body_text = serializers.CharField(required=False, default="")
    body_html = serializers.CharField(required=False, default="")
    reply_to_message_id = serializers.UUIDField(required=False, allow_null=True)
    protocol_id = serializers.UUIDField(required=False, allow_null=True)
