"""
Serializers per autenticazione (login, reset password, change password).
"""
import re
from django.conf import settings
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """Credenziali login."""

    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class PasswordResetRequestSerializer(serializers.Serializer):
    """Richiesta reset password (solo email)."""

    email = serializers.EmailField(write_only=True)


def _validate_password(value):
    """Min 8 char, 1 maiuscola, 1 numero."""
    if len(value) < 8:
        raise serializers.ValidationError("La password deve avere almeno 8 caratteri.")
    if not re.search(r"[A-Z]", value):
        raise serializers.ValidationError(
            "La password deve contenere almeno una lettera maiuscola."
        )
    if not re.search(r"\d", value):
        raise serializers.ValidationError("La password deve contenere almeno un numero.")
    return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Conferma reset password con token."""

    token = serializers.UUIDField(write_only=True)
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_new_password(self, value):
        return _validate_password(value)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Le password non coincidono."}
            )
        return data


class InviteUserSerializer(serializers.Serializer):
    """Payload per invito utente (RF-018)."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[("OPERATOR", "Operatore"), ("REVIEWER", "Revisore"), ("APPROVER", "Approvatore"), ("ADMIN", "Amministratore")],
        default="OPERATOR",
    )
    organizational_unit_id = serializers.UUIDField(required=False, allow_null=True)
    ou_role = serializers.ChoiceField(
        choices=[("OPERATOR", "Operatore"), ("REVIEWER", "Revisore"), ("APPROVER", "Approvatore")],
        default="OPERATOR",
        required=False,
    )


class AcceptInvitationSerializer(serializers.Serializer):
    """Payload per accettazione invito."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_password(self, value):
        return _validate_password(value)

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Le password non coincidono."})
        return data


class ChangePasswordRequiredSerializer(serializers.Serializer):
    """Cambio password obbligatorio per utenti con must_change_password=True."""

    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_new_password(self, value):
        return _validate_password(value)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Le password non coincidono."}
            )
        return data
