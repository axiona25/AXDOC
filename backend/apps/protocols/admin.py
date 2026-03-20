from django.contrib import admin
from .models import Protocol, ProtocolCounter


@admin.register(ProtocolCounter)
class ProtocolCounterAdmin(admin.ModelAdmin):
    list_display = ["organizational_unit", "year", "last_number"]
    list_filter = ["year"]


@admin.register(Protocol)
class ProtocolAdmin(admin.ModelAdmin):
    list_display = ["protocol_id", "protocol_number", "number", "year", "direction", "subject", "organizational_unit", "status", "registered_at"]
    list_filter = ["direction", "status"]
    search_fields = ["protocol_id", "protocol_number", "subject", "sender_receiver"]
