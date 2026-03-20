from django.contrib import admin
from .models import DocumentIndex


@admin.register(DocumentIndex)
class DocumentIndexAdmin(admin.ModelAdmin):
    list_display = ["document", "indexed_at", "error_message"]
