"""
Serializers firma e conservazione (RF-075..RF-080, FASE 20).
"""
import re
from rest_framework import serializers
from .models import SignatureRequest, SignatureSequenceStep, ConservationRequest


class SignatureSequenceStepSerializer(serializers.ModelSerializer):
    signer_email = serializers.SerializerMethodField()

    class Meta:
        model = SignatureSequenceStep
        fields = [
            "id", "order", "signer", "signer_email", "role_required",
            "status", "signed_at", "rejection_reason", "certificate_info",
        ]

    def get_signer_email(self, obj):
        return obj.signer.email if obj.signer else None


class SignatureRequestSerializer(serializers.ModelSerializer):
    signer_email = serializers.SerializerMethodField()
    requested_by_email = serializers.SerializerMethodField()
    document_title = serializers.SerializerMethodField()
    sequence_steps = SignatureSequenceStepSerializer(many=True, read_only=True)
    current_signer = serializers.SerializerMethodField()

    class Meta:
        model = SignatureRequest
        fields = [
            "id", "target_type", "document", "document_version", "document_title",
            "protocol", "dossier", "requested_by", "requested_by_email",
            "signer", "signer_email", "format", "status", "signature_reason",
            "signed_at", "created_at", "otp_expires_at", "error_message",
            "sign_all_documents", "signed_document_ids", "signature_sequence",
            "current_signer_index", "require_sequential",
            "sequence_steps", "current_signer",
        ]

    def get_signer_email(self, obj):
        return obj.signer.email if obj.signer else None

    def get_requested_by_email(self, obj):
        return obj.requested_by.email if obj.requested_by else None

    def get_document_title(self, obj):
        return obj.document.title if obj.document else None

    def get_current_signer(self, obj):
        user = obj.get_current_signer()
        return {"id": str(user.id), "email": user.email} if user else None


class SignatureRequestDetailSerializer(SignatureRequestSerializer):
    class Meta(SignatureRequestSerializer.Meta):
        fields = SignatureRequestSerializer.Meta.fields + [
            "provider_request_id", "otp_sent_at", "otp_attempts",
            "signed_file", "signed_file_name", "signature_location",
        ]


class RequestSignatureSerializer(serializers.Serializer):
    signer_id = serializers.UUIDField()
    format = serializers.ChoiceField(choices=["cades", "pades_invisible", "pades_graphic"])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    graphic_signature = serializers.CharField(required=False, allow_blank=True)


class OTPVerifySerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=10)

    def validate_otp_code(self, value):
        if not re.match(r"^\d{6}$", value.strip()):
            raise serializers.ValidationError("L'OTP deve essere di 6 cifre.")
        return value.strip()


class ConservationRequestSerializer(serializers.ModelSerializer):
    document_title = serializers.SerializerMethodField()

    class Meta:
        model = ConservationRequest
        fields = [
            "id", "document", "document_title", "document_version",
            "status", "document_type", "document_date", "reference_number",
            "conservation_class", "submitted_at", "completed_at",
            "certificate_url", "error_message", "created_at",
        ]

    def get_document_title(self, obj):
        return obj.document.title if obj.document else None


class SendToConservationSerializer(serializers.Serializer):
    document_type = serializers.CharField(max_length=200)
    document_date = serializers.DateField()
    reference_number = serializers.CharField(required=False, allow_blank=True, max_length=200)
    conservation_class = serializers.ChoiceField(choices=[("1", "10 anni"), ("2", "30 anni"), ("3", "Permanente")], default="1")
