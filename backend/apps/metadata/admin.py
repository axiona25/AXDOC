from django.contrib import admin
from .models import MetadataStructure, MetadataField, MetadataStructureOU


class MetadataFieldInline(admin.TabularInline):
    model = MetadataField
    extra = 0


@admin.register(MetadataStructure)
class MetadataStructureAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    inlines = [MetadataFieldInline]


@admin.register(MetadataField)
class MetadataFieldAdmin(admin.ModelAdmin):
    list_display = ["structure", "name", "label", "field_type", "is_required", "order"]


@admin.register(MetadataStructureOU)
class MetadataStructureOUAdmin(admin.ModelAdmin):
    list_display = ["structure", "organizational_unit"]
