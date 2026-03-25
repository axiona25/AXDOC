from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserGroup, UserGroupMembership, ConsentRecord


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    filter_horizontal = []
    readonly_fields = ["id", "date_joined", "last_login", "updated_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Anagrafica",
            {"fields": ("first_name", "last_name", "phone", "avatar")},
        ),
        (
            "Permessi",
            {"fields": ("role", "is_active", "is_staff", "is_superuser")},
        ),
        (
            "Sicurezza",
            {
                "fields": (
                    "failed_login_attempts",
                    "locked_until",
                    "must_change_password",
                    "is_deleted",
                )
            },
        ),
        (
            "Sistema",
            {"fields": ("id", "date_joined", "last_login", "updated_at", "created_by")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]


@admin.register(UserGroupMembership)
class UserGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ["group", "user", "added_at"]
    list_filter = ["group"]


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "consent_type", "version", "granted", "created_at"]
    list_filter = ["consent_type", "granted"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "created_at"]
