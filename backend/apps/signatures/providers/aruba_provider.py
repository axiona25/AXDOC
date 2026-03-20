"""
Stub integrazione Aruba (RF-078). Richiede contratto e credenziali.
"""
from django.conf import settings

from .base import BaseSignatureProvider, BaseConservationProvider


class ArubaSignatureProvider(BaseSignatureProvider):
    """Integrazione reale con Aruba Sign. Stub: NotImplementedError."""

    def __init__(self):
        self.api_url = getattr(settings, "ARUBA_SIGN_API_URL", "")
        self.api_key = getattr(settings, "ARUBA_SIGN_API_KEY", "")
        self.user_id = getattr(settings, "ARUBA_SIGN_USER_ID", "")

    def request_signature(self, document_path, signer_phone, format, **kwargs):
        raise NotImplementedError(
            "Implementare chiamata API Aruba RemoteSign. "
            "Usa ARUBA_SIGN_API_URL e ARUBA_SIGN_API_KEY da settings."
        )

    def confirm_signature(self, provider_request_id, otp_code):
        raise NotImplementedError("Implementare conferma firma Aruba")

    def verify_signature(self, signed_file_path):
        raise NotImplementedError("Implementare verifica firma Aruba")


class ArubaConservationProvider(BaseConservationProvider):
    """Integrazione reale con Aruba Conservazione. Stub."""

    def __init__(self):
        self.api_url = getattr(settings, "ARUBA_CONSERVATION_API_URL", "")
        self.api_key = getattr(settings, "ARUBA_CONSERVATION_API_KEY", "")

    def submit_for_conservation(self, document_path, metadata):
        raise NotImplementedError(
            "Implementare invio ad Aruba Conservazione. "
            "Documentazione: https://doc.aruba.it/conservazione/"
        )

    def check_conservation_status(self, provider_request_id):
        raise NotImplementedError("Implementare check stato Aruba Conservazione")
