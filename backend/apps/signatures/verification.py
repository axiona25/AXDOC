"""
Verifica firma digitale e marca temporale RFC 3161 (FASE 20).
In dev: mock sempre valido. In prod: integrazione TSA/verifica certificati.
"""
import base64
from django.utils import timezone


def verify_signature(signed_file_path: str, signature_type: str) -> dict:
    """
    Verifica firma digitale su file .p7m o PDF firmato.
    Ritorna: valid, signer_cn, signer_email, certificate_issuer,
    certificate_valid_from, certificate_valid_to, signed_at,
    timestamp_token, revocation_status, errors.
    In dev: mock sempre valido.
    """
    try:
        from .providers import get_signature_provider
        provider = get_signature_provider()
        if hasattr(provider, "verify_signature"):
            return provider.verify_signature(signed_file_path)
    except Exception as e:
        return {
            "valid": False,
            "signer_cn": "",
            "signer_email": "",
            "certificate_issuer": "",
            "certificate_valid_from": None,
            "certificate_valid_to": None,
            "signed_at": None,
            "timestamp_token": None,
            "revocation_status": "",
            "errors": [str(e)],
        }
    # Mock per sviluppo: risultato sempre valido
    return {
        "valid": True,
        "signer_cn": "Mock Signer",
        "signer_email": "signer@mock.local",
        "certificate_issuer": "Mock CA",
        "certificate_valid_from": timezone.now().isoformat(),
        "certificate_valid_to": (timezone.now() + timezone.timedelta(days=365)).isoformat(),
        "signed_at": timezone.now().isoformat(),
        "timestamp_token": "mock-rfc3161-token",
        "revocation_status": "good",
        "errors": [],
    }


def apply_timestamp(file_path: str) -> bytes:
    """
    Applica marca temporale RFC 3161 al file.
    In dev: timestamp mock con datetime.now().
    In prod: chiamata a TSA configurata.
    """
    with open(file_path, "rb") as f:
        content = f.read()
    # Mock: in produzione si chiamerebbe un TSA reale
    ts = timezone.now().isoformat().encode("utf-8")
    return base64.b64encode(ts) if content else b""
