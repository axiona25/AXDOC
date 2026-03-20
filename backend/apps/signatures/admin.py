from django.contrib import admin
from .models import SignatureRequest, ConservationRequest


@admin.register(SignatureRequest)
class SignatureRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "document", "signer", "format", "status", "created_at"]
    list_filter = ["status", "format"]


@admin.register(ConservationRequest)
class ConservationRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "document", "status", "document_type", "submitted_at", "completed_at"]
    list_filter = ["status"]
