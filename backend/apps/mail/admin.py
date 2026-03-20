from django.contrib import admin

from .models import MailAccount, MailAttachment, MailMessage


@admin.register(MailAccount)
class MailAccountAdmin(admin.ModelAdmin):
    list_display = ["name", "account_type", "email_address", "is_active", "is_default", "last_fetch_at"]
    list_filter = ["account_type", "is_active"]


@admin.register(MailMessage)
class MailMessageAdmin(admin.ModelAdmin):
    list_display = ["subject", "from_address", "direction", "status", "sent_at", "account"]
    list_filter = ["direction", "status", "account"]
    search_fields = ["subject", "from_address"]


@admin.register(MailAttachment)
class MailAttachmentAdmin(admin.ModelAdmin):
    list_display = ["filename", "content_type", "size", "message"]
