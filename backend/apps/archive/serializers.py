from rest_framework import serializers
from .models import DocumentArchive, RetentionRule, InformationPackage, PackageDocument


class DocumentArchiveSerializer(serializers.ModelSerializer):
    document_title = serializers.SerializerMethodField()
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)

    class Meta:
        model = DocumentArchive
        fields = [
            "id", "document", "document_title", "stage", "stage_display",
            "classification_code", "classification_label", "retention_years", "retention_rule",
            "archive_date", "archive_by", "historical_date", "historical_by",
            "discard_date", "discard_approved", "conservation_package_id", "conservation_sent_at",
            "conservation_status", "conservation_response", "notes", "created_at", "updated_at",
        ]

    def get_document_title(self, obj):
        return obj.document.title if obj.document else None


class RetentionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionRule
        fields = [
            "id", "classification_code", "classification_label", "document_types",
            "retention_years", "retention_basis", "action_after_retention",
            "notes", "is_active", "created_at", "updated_at",
        ]


class InformationPackageSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField()
    protocol_count = serializers.SerializerMethodField()
    dossier_count = serializers.SerializerMethodField()

    class Meta:
        model = InformationPackage
        fields = [
            "id", "package_type", "package_id", "created_at", "created_by",
            "package_file", "manifest_file", "checksum", "signed_at", "timestamp_token",
            "status", "conservation_response", "document_count", "protocol_count", "dossier_count",
        ]

    def get_document_count(self, obj):
        if hasattr(obj, "doc_link_count"):
            return obj.doc_link_count
        return obj.documents.count() if hasattr(obj, "documents") else 0

    def get_protocol_count(self, obj):
        if hasattr(obj, "proto_link_count"):
            return obj.proto_link_count
        return obj.protocols.count() if hasattr(obj, "protocols") else 0

    def get_dossier_count(self, obj):
        if hasattr(obj, "dossier_link_count"):
            return obj.dossier_link_count
        return obj.dossiers.count() if hasattr(obj, "dossiers") else 0
