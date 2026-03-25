"""Test unitari verifica firma (FASE 31)."""
from unittest.mock import patch

import pytest

from apps.signatures.verification import verify_p7m, verify_signature


def test_verify_signature_cades_with_mock(tmp_path):
    p7m_file = tmp_path / "test.p7m"
    p7m_file.write_bytes(b"fake p7m content")

    with patch("apps.signatures.verification.verify_p7m") as mock_verify:
        mock_verify.return_value = {
            "valid": True,
            "signers": [
                {
                    "common_name": "Mario Rossi",
                    "email": "mario@test.it",
                    "issuer": "CA Test",
                    "valid_from": "2025-01-01",
                    "valid_to": "2026-01-01",
                    "is_expired": False,
                }
            ],
            "errors": [],
        }
        result = verify_signature(str(p7m_file), "cades")
        assert result["valid"] is True
        assert result["signer_cn"] == "Mario Rossi"


def test_verify_signature_pades_returns_placeholder(tmp_path):
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")
    result = verify_signature(str(pdf_file), "pades")
    assert result["valid"] is True
    assert "PAdES" in (result.get("signer_cn") or "")


def test_verify_p7m_with_invalid_file(tmp_path):
    bad_file = tmp_path / "bad.p7m"
    bad_file.write_bytes(b"not a real p7m")
    result = verify_p7m(str(bad_file))
    assert result["valid"] is False or len(result.get("errors", [])) > 0
