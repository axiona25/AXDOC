from django.contrib import admin
from .models import DocumentArchive, RetentionRule, InformationPackage, PackageDocument, PackageProtocolLink, PackageDossierLink


@admin.register(DocumentArchive)
class DocumentArchiveAdmin(admin.ModelAdmin):
    list_display = ["document", "stage", "classification_code", "archive_date", "conservation_status"]
    list_filter = ["stage", "conservation_status"]
    search_fields = ["document__title", "classification_code"]


@admin.register(RetentionRule)
class RetentionRuleAdmin(admin.ModelAdmin):
    list_display = ["classification_code", "classification_label", "retention_years", "action_after_retention", "is_active"]
    list_filter = ["is_active", "action_after_retention"]


@admin.register(InformationPackage)
class InformationPackageAdmin(admin.ModelAdmin):
    list_display = ["package_id", "package_type", "status", "created_at", "created_by"]
    list_filter = ["package_type", "status"]


admin.site.register(PackageDocument)
admin.site.register(PackageProtocolLink)
admin.site.register(PackageDossierLink)
