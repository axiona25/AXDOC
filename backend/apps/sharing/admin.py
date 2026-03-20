from django.contrib import admin
from .models import ShareLink, ShareAccessLog


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ["token", "target_type", "recipient_type", "shared_by", "is_active", "created_at", "expires_at"]
    list_filter = ["target_type", "recipient_type", "is_active"]
    search_fields = ["token", "recipient_email", "recipient_user__email"]


@admin.register(ShareAccessLog)
class ShareAccessLogAdmin(admin.ModelAdmin):
    list_display = ["share_link", "action", "accessed_at", "ip_address"]
