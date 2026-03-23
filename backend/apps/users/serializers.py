"""
Serializers per l'app users (RF-011..RF-020, RF-016 gruppi).
"""
import re
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import UserGroup, UserGroupMembership, ROLE_CHOICES

User = get_user_model()


class UserOUSerializer(serializers.Serializer):
    """Serializer nested per l'unità organizzativa dell'utente."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    """Serializer in lettura: nessun campo password."""

    get_full_name = serializers.ReadOnlyField()
    is_guest = serializers.ReadOnlyField()
    organizational_unit = serializers.SerializerMethodField()
    organizational_units = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "is_guest",
            "role",
            "is_active",
            "is_deleted",
            "date_joined",
            "avatar",
            "phone",
            "get_full_name",
            "mfa_enabled",
            "organizational_unit",
            "organizational_units",
        ]
        read_only_fields = ["id", "email", "date_joined", "is_deleted"]

    def get_organizational_unit(self, obj):
        """Retrocompatibilità: ritorna la prima UO attiva o None."""
        from apps.organizations.models import OrganizationalUnitMembership

        membership = (
            OrganizationalUnitMembership.objects.filter(user=obj, is_active=True)
            .select_related("organizational_unit")
            .first()
        )
        if membership:
            return UserOUSerializer(membership.organizational_unit).data
        return None

    def get_organizational_units(self, obj):
        """Tutte le UO attive dell'utente."""
        from apps.organizations.models import OrganizationalUnitMembership

        memberships = (
            OrganizationalUnitMembership.objects.filter(user=obj, is_active=True)
            .select_related("organizational_unit")
        )
        return [
            UserOUSerializer(m.organizational_unit).data
            for m in memberships
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """Creazione utente (admin): password casuale, must_change_password=True."""

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "user_type", "role", "phone"]

    def validate_email(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email__iexact=value, is_deleted=False).exists():
            raise serializers.ValidationError(
                "Esiste già un utente con questa email."
            )
        return value.lower()

    def create(self, validated_data):
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(16))
        user = User.objects.create_user(
            password=password,
            must_change_password=True,
            **validated_data,
        )
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Aggiornamento parziale: admin può cambiare role, user_type, is_active, organizational_unit_id."""

    organizational_unit_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar", "role", "user_type", "is_active", "organizational_unit_id"]

    def update(self, instance, validated_data):
        ou_id = validated_data.pop("organizational_unit_id", -1)
        instance = super().update(instance, validated_data)
        if ou_id != -1:
            from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership

            # Disattiva tutte le membership esistenti
            OrganizationalUnitMembership.objects.filter(user=instance).update(is_active=False)
            if ou_id:
                try:
                    ou = OrganizationalUnit.objects.get(id=ou_id)
                    # Usa update_or_create per gestire unique_together
                    OrganizationalUnitMembership.objects.update_or_create(
                        user=instance,
                        organizational_unit=ou,
                        defaults={"role": "OPERATOR", "is_active": True},
                    )
                except OrganizationalUnit.DoesNotExist:
                    pass
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """Profilo modificabile dall'utente (no email, no role)."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar"]


class UserCreateManualSerializer(serializers.Serializer):
    """Creazione manuale utente (senza invito email). FASE 17."""

    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    user_type = serializers.ChoiceField(choices=["internal", "guest"], default="internal")
    role = serializers.ChoiceField(choices=[r[0] for r in ROLE_CHOICES], required=False)
    organizational_unit_id = serializers.UUIDField(required=False, allow_null=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    send_welcome_email = serializers.BooleanField(default=True)

    def validate_email(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email__iexact=value, is_deleted=False).exists():
            raise serializers.ValidationError(
                "Esiste già un utente con questa email."
            )
        return value.lower()

    def validate_organizational_unit_id(self, value):
        if value is None:
            return value
        from apps.organizations.models import OrganizationalUnit
        if not OrganizationalUnit.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Unità organizzativa non trovata o non attiva.")
        return value

    def validate(self, data):
        user_type = data.get("user_type", "internal")
        if user_type == "guest":
            data["role"] = "OPERATOR"
            data["organizational_unit_id"] = None
        elif not data.get("role"):
            data["role"] = "OPERATOR"
        return data

    def create(self, validated_data):
        import secrets
        import string
        send_welcome_email = validated_data.pop("send_welcome_email", True)
        ou_id = validated_data.pop("organizational_unit_id", None)
        password = (validated_data.pop("password", None) or "").strip()
        if not password:
            alphabet = string.ascii_letters + string.digits
            password = "".join(secrets.choice(alphabet) for _ in range(16))
        user = User.objects.create_user(
            password=password,
            must_change_password=True,
            **validated_data,
        )
        if ou_id and user.user_type == "internal":
            from apps.organizations.models import OrganizationalUnitMembership
            OrganizationalUnitMembership.objects.get_or_create(
                user=user,
                organizational_unit_id=ou_id,
                defaults={"is_active": True},
            )
        if send_welcome_email and user.email:
            # Placeholder: invio email di benvenuto (integrazione email FASE)
            pass
        return user


def _validate_password_strength(value):
    """Requisiti: min 8 char, 1 numero, 1 maiuscola."""
    if len(value) < 8:
        raise serializers.ValidationError("La password deve avere almeno 8 caratteri.")
    if not re.search(r"[A-Z]", value):
        raise serializers.ValidationError(
            "La password deve contenere almeno una lettera maiuscola."
        )
    if not re.search(r"\d", value):
        raise serializers.ValidationError(
            "La password deve contenere almeno un numero."
        )
    return value


class ChangePasswordSerializer(serializers.Serializer):
    """Cambio password: vecchia + nuova + conferma."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return _validate_password_strength(value)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Le password non coincidono."}
            )
        return data


class UserGroupMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = UserGroupMembership
        fields = ["id", "user", "user_email", "user_name", "added_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class UserGroupSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()
    organizational_unit_name = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        fields = [
            "id",
            "name",
            "description",
            "organizational_unit",
            "organizational_unit_name",
            "created_at",
            "updated_at",
            "is_active",
            "members_count",
        ]

    def get_members_count(self, obj):
        return obj.memberships.count()

    def get_organizational_unit_name(self, obj):
        return obj.organizational_unit.name if obj.organizational_unit else None


class UserGroupDetailSerializer(UserGroupSerializer):
    members = UserGroupMembershipSerializer(many=True, read_only=True, source="memberships")

    class Meta(UserGroupSerializer.Meta):
        fields = list(UserGroupSerializer.Meta.fields) + ["members", "created_by"]
