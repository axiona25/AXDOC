"""
Serializers fascicoli (RF-064..RF-069, FASE 22).
"""
from rest_framework import serializers
from .models import (
    Dossier,
    DossierDocument,
    DossierProtocol,
    DossierPermission,
    DossierOUPermission,
    DossierFolder,
    DossierEmail,
    DossierFile,
)


class DossierListSerializer(serializers.ModelSerializer):
    responsible_email = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    protocol_count = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = [
            "id", "title", "identifier", "status", "responsible", "responsible_email",
            "created_at", "updated_at", "document_count", "protocol_count",
        ]

    def get_responsible_email(self, obj):
        return obj.responsible.email if obj.responsible else None

    def get_document_count(self, obj):
        return obj.dossier_documents.count()

    def get_protocol_count(self, obj):
        return obj.dossier_protocols.count()


class DossierDocumentEntrySerializer(serializers.ModelSerializer):
    document_title = serializers.SerializerMethodField()
    document_id = serializers.SerializerMethodField()

    class Meta:
        model = DossierDocument
        fields = ["id", "document", "document_id", "document_title", "added_at", "notes"]

    def get_document_title(self, obj):
        return obj.document.title if obj.document else None

    def get_document_id(self, obj):
        return str(obj.document_id) if obj.document_id else None


class DossierProtocolEntrySerializer(serializers.ModelSerializer):
    protocol_display = serializers.SerializerMethodField()
    protocol_id = serializers.SerializerMethodField()

    class Meta:
        model = DossierProtocol
        fields = ["id", "protocol", "protocol_id", "protocol_display", "added_at"]

    def get_protocol_display(self, obj):
        return obj.protocol.protocol_id if obj.protocol else None

    def get_protocol_id(self, obj):
        return str(obj.protocol_id) if obj.protocol_id else None


class DossierFolderSerializer(serializers.ModelSerializer):
    folder_name = serializers.SerializerMethodField()

    class Meta:
        model = DossierFolder
        fields = ["id", "folder", "folder_name", "added_by", "added_at"]

    def get_folder_name(self, obj):
        return obj.folder.name if obj.folder else None


class DossierEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DossierEmail
        fields = [
            "id", "email_type", "from_address", "to_addresses", "subject", "body",
            "received_at", "message_id", "raw_file", "added_by", "added_at",
        ]


class DossierFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DossierFile
        fields = [
            "id", "file", "file_name", "file_size", "file_type", "checksum",
            "uploaded_by", "uploaded_at", "notes",
        ]


class DossierDetailSerializer(serializers.ModelSerializer):
    responsible_email = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    protocols = serializers.SerializerMethodField()
    dossier_folders = serializers.SerializerMethodField()
    dossier_emails = serializers.SerializerMethodField()
    dossier_files = serializers.SerializerMethodField()
    allowed_user_ids = serializers.SerializerMethodField()
    allowed_ou_ids = serializers.SerializerMethodField()
    organizational_unit_code = serializers.SerializerMethodField()

    class Meta:
        model = Dossier
        fields = [
            "id", "title", "identifier", "description", "status", "responsible", "responsible_email",
            "organizational_unit", "organizational_unit_code",
            "created_by", "created_at", "updated_at", "archived_at",
            "metadata_structure", "metadata_values",
            "classification_code", "classification_label", "retention_years", "retention_basis",
            "archive_stage", "closed_at", "closed_by", "index_generated_at", "index_file",
            "documents", "protocols", "dossier_folders", "dossier_emails", "dossier_files",
            "allowed_user_ids", "allowed_ou_ids",
        ]

    def get_organizational_unit_code(self, obj):
        return obj.organizational_unit.code if getattr(obj, "organizational_unit", None) else None


    def get_responsible_email(self, obj):
        return obj.responsible.email if obj.responsible else None

    def get_documents(self, obj):
        return DossierDocumentEntrySerializer(obj.dossier_documents.all(), many=True).data

    def get_protocols(self, obj):
        return DossierProtocolEntrySerializer(obj.dossier_protocols.all(), many=True).data

    def get_dossier_folders(self, obj):
        return DossierFolderSerializer(getattr(obj, "dossier_folders", obj.dossier_folders).all(), many=True).data

    def get_dossier_emails(self, obj):
        return DossierEmailSerializer(getattr(obj, "dossier_emails", obj.dossier_emails).all(), many=True).data

    def get_dossier_files(self, obj):
        return DossierFileSerializer(getattr(obj, "dossier_files", obj.dossier_files).all(), many=True).data

    def get_allowed_user_ids(self, obj):
        return list(obj.user_permissions.values_list("user_id", flat=True))

    def get_allowed_ou_ids(self, obj):
        return list(obj.ou_permissions.values_list("organizational_unit_id", flat=True))


class DossierCreateSerializer(serializers.ModelSerializer):
    allowed_users = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    allowed_ous = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )

    class Meta:
        model = Dossier
        fields = [
            "title", "identifier", "description", "responsible", "organizational_unit",
            "classification_code", "classification_label", "retention_years", "retention_basis",
            "allowed_users", "allowed_ous",
        ]

    def validate_identifier(self, value):
        value = (value or "").strip()
        if not value:
            return value  # Vuoto: verrà generato da pre_save se c'è organizational_unit
        qs = Dossier.objects.filter(identifier=value, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Identificatore già esistente.")
        return value
