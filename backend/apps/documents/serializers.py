"""
Serializers per cartelle e documenti (FASE 05).
"""
from rest_framework import serializers
from .models import Folder, Document, DocumentVersion, DocumentAttachment
from apps.metadata.models import MetadataStructure


class FolderListSerializer(serializers.ModelSerializer):
    """Lista cartelle: id, name, parent_id, subfolder_count, document_count, created_at."""
    parent_id = serializers.SerializerMethodField()
    subfolder_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ["id", "name", "parent_id", "subfolder_count", "document_count", "created_at"]

    def get_parent_id(self, obj):
        return str(obj.parent_id) if obj.parent_id else None

    def get_subfolder_count(self, obj):
        return obj.subfolders.filter(is_deleted=False).count()

    def get_document_count(self, obj):
        return obj.documents.filter(is_deleted=False).count()


class FolderDetailSerializer(FolderListSerializer):
    """Dettaglio cartella con subfolders e metadati (FASE 18)."""
    subfolders = serializers.SerializerMethodField()
    metadata_structure = serializers.PrimaryKeyRelatedField(allow_null=True, read_only=True)
    metadata_values = serializers.JSONField(read_only=True, default=dict)

    class Meta(FolderListSerializer.Meta):
        fields = FolderListSerializer.Meta.fields + ["subfolders", "metadata_structure", "metadata_values"]

    def get_subfolders(self, obj):
        children = obj.subfolders.filter(is_deleted=False).order_by("name")
        return FolderListSerializer(children, many=True).data


class FolderCreateSerializer(serializers.ModelSerializer):
    """Creazione cartella: name, parent_id."""
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.filter(is_deleted=False),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Folder
        fields = ["name", "parent_id"]

    def validate(self, data):
        parent = data.get("parent_id")
        name = (data.get("name") or "").strip()
        if not name:
            raise serializers.ValidationError({"name": "Il nome è obbligatorio."})
        qs = Folder.objects.filter(parent=parent, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if name and qs.filter(name__iexact=name).exists():
            raise serializers.ValidationError(
                {"name": "Esiste già una cartella con questo nome in questa posizione."}
            )
        return data


# --- Document serializers ---

class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = [
            "id", "version_number", "file_name", "file_size", "file_type",
            "created_by", "created_at", "change_description", "is_current",
        ]
        read_only_fields = fields


class DocumentAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentAttachment
        fields = ["id", "file_name", "file_size", "file_type", "uploaded_by", "uploaded_at", "description"]
        read_only_fields = ["id", "file_name", "file_size", "file_type", "uploaded_by", "uploaded_at"]


class DocumentListSerializer(serializers.ModelSerializer):
    folder_id = serializers.SerializerMethodField()
    folder_name = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "description", "folder_id", "folder_name", "status", "current_version",
            "created_by", "created_by_email", "created_at", "updated_at",
            "locked_by", "locked_at", "visibility", "owner",
        ]
        read_only_fields = fields

    def get_folder_id(self, obj):
        return str(obj.folder_id) if obj.folder_id else None

    def get_folder_name(self, obj):
        return obj.folder.name if obj.folder else None

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None


class DocumentDetailSerializer(serializers.ModelSerializer):
    folder_id = serializers.SerializerMethodField()
    versions = DocumentVersionSerializer(many=True, read_only=True)
    attachments = DocumentAttachmentSerializer(many=True, read_only=True)
    can_read = serializers.SerializerMethodField()
    can_write = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "description", "folder_id", "status", "current_version",
            "created_by", "created_at", "updated_at", "metadata_structure", "metadata_values",
            "locked_by", "locked_at", "is_protocolled", "visibility", "owner",
            "versions", "attachments",
            "can_read", "can_write", "can_delete",
        ]
        read_only_fields = fields

    def get_folder_id(self, obj):
        return str(obj.folder_id) if obj.folder_id else None

    def _user_perms(self, obj, user):
        if not user or not user.is_authenticated:
            return False, False, False
        if getattr(user, "role", None) == "ADMIN":
            return True, True, True
        if obj.created_by_id == user.id:
            return True, True, True
        perm = obj.user_permissions.filter(user=user).first()
        if perm:
            return perm.can_read, perm.can_write, perm.can_delete
        from apps.organizations.models import OrganizationalUnitMembership
        ou_ids = OrganizationalUnitMembership.objects.filter(user=user).values_list("organizational_unit_id", flat=True)
        ou_perm = obj.ou_permissions.filter(organizational_unit_id__in=ou_ids).first()
        if ou_perm:
            return ou_perm.can_read, ou_perm.can_write, False
        return False, False, False

    def get_can_read(self, obj):
        req = self.context.get("request")
        return self._user_perms(obj, req.user if req else None)[0]

    def get_can_write(self, obj):
        req = self.context.get("request")
        return self._user_perms(obj, req.user if req else None)[1]

    def get_can_delete(self, obj):
        req = self.context.get("request")
        return self._user_perms(obj, req.user if req else None)[2]


class DocumentCreateSerializer(serializers.ModelSerializer):
    folder_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.filter(is_deleted=False),
        source="folder",
        allow_null=True,
        required=False,
    )
    metadata_structure_id = serializers.PrimaryKeyRelatedField(
        queryset=MetadataStructure.objects.all(),
        source="metadata_structure",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Document
        fields = [
            "title", "description", "folder_id", "metadata_structure_id", "metadata_values",
        ]
