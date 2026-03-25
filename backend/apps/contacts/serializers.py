from rest_framework import serializers

from .models import Contact


class ContactListSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id",
            "contact_type",
            "first_name",
            "last_name",
            "company_name",
            "email",
            "pec",
            "phone",
            "display_name",
            "is_favorite",
            "tags",
        ]


class ContactDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    primary_email = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id",
            "contact_type",
            "first_name",
            "last_name",
            "company_name",
            "job_title",
            "tax_code",
            "email",
            "pec",
            "phone",
            "mobile",
            "address",
            "city",
            "province",
            "zip_code",
            "country",
            "notes",
            "tags",
            "is_favorite",
            "is_shared",
            "organizational_unit",
            "source",
            "display_name",
            "primary_email",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "source"]
