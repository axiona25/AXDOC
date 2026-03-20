"""
Provider mock per sviluppo e test (RF-078). OTP fisso: 123456.
"""
import base64
import logging
from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from .base import BaseSignatureProvider, BaseConservationProvider

logger = logging.getLogger(__name__)


class MockSignatureProvider(BaseSignatureProvider):
    """Simula Aruba senza chiamate reali. OTP: 123456."""

    def request_signature(
        self,
        document_path: str,
        signer_phone: str,
        format: str,
        reason: str = "",
        location: str = "",
        graphic_image_path: str | None = None,
    ) -> dict:
        masked = signer_phone[-4:].rjust(10, "*") if len(signer_phone) >= 4 else "****"
        logger.info("[MOCK] OTP inviato a %s: 123456", masked)
        return {
            "provider_request_id": f"MOCK-{uuid4()}",
            "otp_expires_at": timezone.now() + timedelta(minutes=10),
            "message": f"OTP inviato a {masked}",
        }

    def confirm_signature(self, provider_request_id: str, otp_code: str) -> dict:
        if otp_code != "123456":
            return {
                "success": False,
                "signed_file_base64": None,
                "error": "OTP non valido",
            }
        mock_content = b"MOCK_SIGNED_FILE_CONTENT"
        return {
            "success": True,
            "signed_file_base64": base64.b64encode(mock_content).decode(),
            "error": None,
        }

    def verify_signature(self, signed_file_path: str) -> dict:
        return {
            "valid": True,
            "signer_name": "Mock Signer",
            "signed_at": timezone.now(),
            "certificate_info": {"issuer": "Mock CA", "serial": "12345"},
        }


class MockConservationProvider(BaseConservationProvider):
    """Simula invio in conservazione; check_status ritorna completed."""

    def submit_for_conservation(self, document_path: str, metadata: dict) -> dict:
        logger.info("[MOCK] Documento inviato in conservazione: %s", document_path)
        return {
            "provider_request_id": f"CONS-MOCK-{uuid4()}",
            "provider_package_id": f"PKG-{uuid4()}",
            "status": "pending",
        }

    def check_conservation_status(self, provider_request_id: str) -> dict:
        return {
            "status": "completed",
            "message": "Documento conservato con successo (MOCK)",
            "certificate_url": f"https://mock-conservation.example.com/cert/{provider_request_id}",
        }
