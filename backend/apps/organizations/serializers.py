"""
Serializers per Unità Organizzative (RF-021..RF-027).
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import OrganizationalUnit, OrganizationalUnitMembership, OU_ROLE_CHOICES

User = get_user_model()


class OrganizationalUnitMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = OrganizationalUnitMembership
        fields = ["id", "user", "user_email", "user_name", "role", "joined_at", "is_active"]


class OrganizationalUnitSerializer(serializers.ModelSerializer):
    """Lista/dettaglio con children solo primo livello."""

    children = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationalUnit
        fields = [
            "id",
            "name",
            "code",
            "description",
            "parent",
            "is_active",
            "created_at",
            "updated_at",
            "children",
            "members_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_children(self, obj):
        if not obj.is_active:
            return []
        children = obj.children.filter(is_active=True)
        return OrganizationalUnitSerializer(children, many=True).data

    def get_members_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class OrganizationalUnitDetailSerializer(OrganizationalUnitSerializer):
    """Dettaglio con membri."""

    members = serializers.SerializerMethodField()

    class Meta(OrganizationalUnitSerializer.Meta):
        fields = OrganizationalUnitSerializer.Meta.fields + ["members"]

    def get_members(self, obj):
        return OrganizationalUnitMembershipSerializer(
            obj.memberships.filter(is_active=True), many=True
        ).data


class OrganizationalUnitCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationalUnit
        fields = ["name", "code", "description", "parent"]


class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=OU_ROLE_CHOICES)
