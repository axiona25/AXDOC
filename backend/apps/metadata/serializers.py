"""
Serializers strutture metadati (RF-040..RF-042).
"""
from rest_framework import serializers
from .models import MetadataStructure, MetadataField, MetadataStructureOU, FIELD_TYPES


class MetadataFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetadataField
        fields = [
            "id", "name", "label", "field_type", "is_required", "is_searchable",
            "order", "options", "default_value", "validation_rules", "help_text",
        ]
        read_only_fields = ["id"]


class MetadataStructureListSerializer(serializers.ModelSerializer):
    field_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = MetadataStructure
        fields = [
            "id", "name", "description", "allowed_file_extensions",
            "is_active", "applicable_to", "created_at", "updated_at",
            "signature_enabled", "signature_format", "conservation_enabled", "conservation_class", "conservation_document_type",
            "field_count", "document_count",
        ]

    def get_field_count(self, obj):
        return obj.fields.count()

    def get_document_count(self, obj):
        return obj.documents.filter(is_deleted=False).count()


class MetadataStructureDetailSerializer(serializers.ModelSerializer):
    fields = MetadataFieldSerializer(many=True, read_only=True)
    field_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    allowed_organizational_units = serializers.SerializerMethodField()

    allowed_signers = serializers.SerializerMethodField()

    class Meta:
        model = MetadataStructure
        fields = [
            "id", "name", "description", "allowed_file_extensions",
            "allowed_organizational_units", "is_active", "applicable_to",
            "signature_enabled", "signature_format", "allowed_signers",
            "conservation_enabled", "conservation_class", "conservation_document_type",
            "created_by", "created_at", "updated_at",
            "fields", "field_count", "document_count",
        ]

    def get_allowed_signers(self, obj):
        return list(obj.allowed_signers.values_list("id", flat=True))

    def get_field_count(self, obj):
        return obj.fields.count()

    def get_document_count(self, obj):
        return obj.documents.filter(is_deleted=False).count()

    def get_allowed_organizational_units(self, obj):
        return list(
            obj.allowed_organizational_units.values_list("organizational_unit_id", flat=True)
        )


class MetadataStructureCreateSerializer(serializers.ModelSerializer):
    fields = MetadataFieldSerializer(many=True, required=False, default=list)
    allowed_organizational_units = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        write_only=True,
    )
    allowed_signers = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        write_only=True,
    )

    class Meta:
        model = MetadataStructure
        fields = [
            "name", "description", "allowed_file_extensions",
            "allowed_organizational_units", "is_active", "fields",
            "signature_enabled", "signature_format", "allowed_signers",
            "conservation_enabled", "conservation_class", "conservation_document_type",
        ]

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Il nome è obbligatorio.")
        qs = MetadataStructure.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Esiste già una struttura con questo nome.")
        return value

    def create(self, validated_data):
        allowed_ous = validated_data.pop("allowed_organizational_units", [])
        allowed_signers = validated_data.pop("allowed_signers", [])
        fields_data = validated_data.pop("fields", [])
        structure = MetadataStructure.objects.create(
            **validated_data,
            created_by=self.context["request"].user,
        )
        if allowed_signers:
            structure.allowed_signers.set(allowed_signers)
        for ou_id in allowed_ous:
            MetadataStructureOU.objects.get_or_create(
                structure=structure,
                organizational_unit_id=ou_id,
            )
        for i, fd in enumerate(fields_data):
            fd["order"] = fd.get("order", i)
            MetadataField.objects.create(structure=structure, **fd)
        return structure

    def update(self, instance, validated_data):
        allowed_ous = validated_data.pop("allowed_organizational_units", None)
        allowed_signers = validated_data.pop("allowed_signers", None)
        fields_data = validated_data.pop("fields", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if allowed_signers is not None:
            instance.allowed_signers.set(allowed_signers)
        if allowed_ous is not None:
            instance.allowed_organizational_units.through.objects.filter(structure=instance).delete()
            for ou_id in allowed_ous:
                MetadataStructureOU.objects.get_or_create(
                    structure=instance,
                    organizational_unit_id=ou_id,
                )
        if fields_data is not None:
            for i, fd in enumerate(fields_data):
                fd["order"] = fd.get("order", i)
                fid = fd.pop("id", None)
                if fid and instance.fields.filter(id=fid).exists():
                    MetadataField.objects.filter(id=fid, structure=instance).update(
                        label=fd.get("label"),
                        is_required=fd.get("is_required", False),
                        is_searchable=fd.get("is_searchable", True),
                        order=fd.get("order", i),
                        options=fd.get("options", []),
                        default_value=fd.get("default_value"),
                        validation_rules=fd.get("validation_rules", {}),
                        help_text=fd.get("help_text", ""),
                    )
                else:
                    MetadataField.objects.create(
                        structure=instance,
                        name=fd.get("name", f"field_{i}"),
                        label=fd.get("label", ""),
                        field_type=fd.get("field_type", "text"),
                        is_required=fd.get("is_required", False),
                        is_searchable=fd.get("is_searchable", True),
                        order=fd.get("order", i),
                        options=fd.get("options", []),
                        default_value=fd.get("default_value"),
                        validation_rules=fd.get("validation_rules", {}),
                        help_text=fd.get("help_text", ""),
                    )
        return instance
