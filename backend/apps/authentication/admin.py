from django.contrib import admin
from .models import PasswordResetToken, AuditLog, UserInvitation


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "expires_at", "used"]
    list_filter = ["used"]
    search_fields = ["user__email"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "ip_address", "timestamp"]
    list_filter = ["action"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "user", "action", "detail", "ip_address", "user_agent", "timestamp"]
    date_hierarchy = "timestamp"


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "invited_by", "organizational_unit", "role", "is_used", "expires_at", "created_at"]
    list_filter = ["is_used", "role"]
    search_fields = ["email"]
