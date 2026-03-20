from django.contrib import admin
from .models import Dossier, DossierDocument, DossierProtocol, DossierPermission, DossierOUPermission


class DossierDocumentInline(admin.TabularInline):
    model = DossierDocument
    extra = 0


class DossierProtocolInline(admin.TabularInline):
    model = DossierProtocol
    extra = 0


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = ["identifier", "title", "status", "responsible", "created_at"]
    list_filter = ["status"]
    search_fields = ["identifier", "title"]
    inlines = [DossierDocumentInline, DossierProtocolInline]


@admin.register(DossierPermission)
class DossierPermissionAdmin(admin.ModelAdmin):
    list_display = ["dossier", "user", "can_read", "can_write"]


@admin.register(DossierOUPermission)
class DossierOUPermissionAdmin(admin.ModelAdmin):
    list_display = ["dossier", "organizational_unit", "can_read"]
