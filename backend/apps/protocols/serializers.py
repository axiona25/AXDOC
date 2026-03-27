"""
Serializers protocolli (RF-058..RF-063).
"""
from rest_framework import serializers
from .models import Protocol


class ProtocolListSerializer(serializers.ModelSerializer):
    organizational_unit_name = serializers.SerializerMethodField()
    protocol_display = serializers.SerializerMethodField()
    segnatura = serializers.SerializerMethodField()

    class Meta:
        model = Protocol
        fields = [
            "id", "protocol_id", "segnatura", "number", "year", "direction", "subject",
            "sender_receiver", "organizational_unit", "organizational_unit_name",
            "registered_at", "registered_by", "status", "document", "protocol_display",
            "category",
        ]

    def get_organizational_unit_name(self, obj):
        return obj.organizational_unit.name if obj.organizational_unit else None

    def get_protocol_display(self, obj):
        return obj.protocol_id or obj.protocol_number

    def get_segnatura(self, obj):
        """Segnatura AGID: identificativo univoco protocollo (anno/codice UO/numero)."""
        return obj.protocol_id or obj.protocol_number or ""


class ProtocolDetailSerializer(serializers.ModelSerializer):
    organizational_unit_name = serializers.SerializerMethodField()
    document_title = serializers.SerializerMethodField()
    attachment_ids = serializers.SerializerMethodField()
    dossier_ids = serializers.SerializerMethodField()
    segnatura = serializers.SerializerMethodField()

    class Meta:
        model = Protocol
        fields = [
            "id", "protocol_id", "segnatura", "number", "year", "direction", "subject",
            "sender_receiver", "organizational_unit", "organizational_unit_name",
            "registered_at", "registered_by", "status", "notes", "category", "description",
            "document", "document_title", "attachment_ids", "dossier_ids",
            "protocol_number", "document_file", "created_at",
        ]

    def get_organizational_unit_name(self, obj):
        return obj.organizational_unit.name if obj.organizational_unit else None

    def get_document_title(self, obj):
        return obj.document.title if obj.document else None

    def get_attachment_ids(self, obj):
        return list(obj.attachments.values_list("id", flat=True))

    def get_dossier_ids(self, obj):
        """Fascicoli collegati (through DossierProtocol)."""
        return [str(x) for x in obj.dossier_links.values_list("dossier_id", flat=True)]

    def get_segnatura(self, obj):
        return obj.protocol_id or obj.protocol_number or ""


class ProtocolCreateSerializer(serializers.ModelSerializer):
    attachment_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, write_only=True
    )
    dossier_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, write_only=True
    )
    file_upload = serializers.FileField(required=False, write_only=True)

    class Meta:
        model = Protocol
        fields = [
            "direction", "document", "subject", "sender_receiver",
            "organizational_unit", "notes", "category", "description",
            "attachment_ids", "dossier_ids", "file_upload",
        ]

    def validate_organizational_unit(self, value):
        if not value:  # pragma: no cover — campo obbligatorio sul modello
            raise serializers.ValidationError("Unità organizzativa obbligatoria.")
        return value

    def validate_subject(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("Oggetto obbligatorio.")
        return (value or "").strip()
