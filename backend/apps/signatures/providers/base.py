"""
Provider di firma e conservazione: interfacce astratte (RF-078..RF-080).
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class BaseSignatureProvider(ABC):
    """Provider per firma digitale remota (CAdES, PAdES)."""

    @abstractmethod
    def request_signature(
        self,
        document_path: str,
        signer_phone: str,
        format: str,
        reason: str = "",
        location: str = "",
        graphic_image_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Invia documento al provider per firma e manda OTP all'utente.
        Ritorna: {
            "provider_request_id": str,
            "otp_expires_at": datetime,
            "message": str
        }
        """
        pass  # pragma: no cover

    @abstractmethod
    def confirm_signature(
        self,
        provider_request_id: str,
        otp_code: str,
    ) -> dict[str, Any]:
        """
        Conferma firma con OTP inserito dall'utente.
        Ritorna: {
            "success": bool,
            "signed_file_base64": str | None,
            "error": str | None
        }
        """
        pass  # pragma: no cover

    @abstractmethod
    def verify_signature(self, signed_file_path: str) -> dict[str, Any]:
        """
        Verifica validità di un file firmato.
        Ritorna: {
            "valid": bool,
            "signer_name": str,
            "signed_at": datetime,
            "certificate_info": dict
        }
        """
        pass  # pragma: no cover


class BaseConservationProvider(ABC):
    """Provider per conservazione digitale a norma AGID."""

    @abstractmethod
    def submit_for_conservation(
        self,
        document_path: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Invia documento in conservazione.
        metadata: document_type, document_date, reference_number, conservation_class, ecc.
        Ritorna: {
            "provider_request_id": str,
            "provider_package_id": str,
            "status": str
        }
        """
        pass  # pragma: no cover

    @abstractmethod
    def check_conservation_status(self, provider_request_id: str) -> dict[str, Any]:
        """
        Controlla lo stato di una richiesta di conservazione.
        Ritorna: {
            "status": str,
            "message": str,
            "certificate_url": str | None
        }
        """
        pass  # pragma: no cover
