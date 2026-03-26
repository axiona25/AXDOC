"""Test estesi su verification.py (FASE 33B)."""
import base64
import os
from unittest.mock import MagicMock, patch

import pytest

from apps.signatures import verification as ver


class TestVerifyP7mExtended:
    def test_missing_file(self, tmp_path):
        p = tmp_path / "missing.p7m"
        r = ver.verify_p7m(str(p))
        assert r["valid"] is False
        assert any("non trovato" in e.lower() for e in r["errors"]) or r["errors"]

    def test_openssl_fallback_populates_signers(self, tmp_path):
        fake_p7m = tmp_path / "x.p7m"
        fake_p7m.write_bytes(b"not real der but bytes")
        openssl_out = """
Subject: CN = Mario Rossi, emailAddress = mario@test.it, O = Org
Issuer: CN = Test CA, O = CA Org
Not Before: Jan  1 00:00:00 2025 GMT
Not After : Jan  1 00:00:00 2030 GMT
"""
        with patch("apps.signatures.verification.pkcs7.load_der_pkcs7_certificates", side_effect=ValueError("bad")), patch(
            "apps.signatures.verification.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=openssl_out.encode(), stderr=b""),
        ):
            r = ver.verify_p7m(str(fake_p7m))
        assert r["signers"]
        assert r["signers"][0].get("common_name") == "Mario Rossi"


class TestExtractP7mContentExtended:
    def test_file_not_found(self, tmp_path):
        r = ver.extract_p7m_content(str(tmp_path / "nope.p7m"))
        assert r["success"] is False
        assert "non trovato" in (r.get("error") or "").lower()

    def test_openssl_extract_success(self, tmp_path):
        src = tmp_path / "doc.p7m"
        src.write_bytes(b"x")

        def fake_run(cmd, **kwargs):
            if "-out" in cmd:
                out_idx = cmd.index("-out") + 1
                path = cmd[out_idx]
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(b"extracted pdf content")
            return MagicMock(returncode=0, stderr=b"")

        with patch("apps.signatures.verification.subprocess.run", side_effect=fake_run):
            r = ver.extract_p7m_content(str(src), output_dir=str(tmp_path))
        assert r["success"] is True
        assert r["extracted_path"]


class TestVerifySignatureAndTimestamp:
    def test_verify_signature_pades_path(self):
        r = ver.verify_signature("/tmp/file.pdf", signature_type="pades_invisible")
        assert r["valid"] is True
        assert r["signers"] == []

    def test_apply_timestamp_returns_base64(self, tmp_path):
        p = tmp_path / "a.pdf"
        p.write_bytes(b"%PDF-1.4")
        out = ver.apply_timestamp(str(p))
        assert isinstance(out, bytes)
        base64.b64decode(out, validate=True)


class TestParseHelpers:
    def test_parse_openssl_cert_text(self):
        text = """
Subject: CN = Test User, emailAddress = u@x.it, O = Co
Issuer: CN = Root, O = R
Not Before: Mar 24 12:00:00 2026 GMT
Not After : Mar 24 12:00:00 2030 GMT
"""
        signers = ver._parse_openssl_cert_text(text)
        assert signers
        assert signers[0]["common_name"] == "Test User"

    def test_guess_content_type(self):
        assert ver._guess_content_type("a.pdf") == "application/pdf"
        assert ver._guess_content_type("z.unknown") == "application/octet-stream"
