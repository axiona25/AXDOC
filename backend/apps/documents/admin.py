from django.contrib import admin
from .models import (
    Document,
    DocumentVersion,
    DocumentAttachment,
    DocumentPermission,
    DocumentOUPermission,
    Folder,
)


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "created_by", "is_deleted", "created_at"]
    list_filter = ["is_deleted"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "folder", "status", "current_version", "created_by", "locked_by", "created_at"]
    list_filter = ["status", "is_deleted"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["document", "version_number", "file_name", "is_current", "is_encrypted", "created_at"]


@admin.register(DocumentAttachment)
class DocumentAttachmentAdmin(admin.ModelAdmin):
    list_display = ["document", "file_name", "uploaded_by", "uploaded_at"]


@admin.register(DocumentPermission)
class DocumentPermissionAdmin(admin.ModelAdmin):
    list_display = ["document", "user", "can_read", "can_write", "can_delete"]


@admin.register(DocumentOUPermission)
class DocumentOUPermissionAdmin(admin.ModelAdmin):
    list_display = ["document", "organizational_unit", "can_read", "can_write"]
