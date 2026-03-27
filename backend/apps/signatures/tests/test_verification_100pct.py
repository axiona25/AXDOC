"""Copertura mirata apps.signatures.verification (mock pkcs7, subprocess, FS)."""
import os
from datetime import datetime, timedelta, timezone as dt_tz
from unittest.mock import MagicMock, patch

from apps.signatures import verification as ver


def test_verify_p7m_file_not_found():
    r = ver.verify_p7m("/nonexistent/path/file.p7m")
    assert r["valid"] is False
    assert "non trovato" in r["errors"][0].lower()


def test_verify_p7m_read_error(tmp_path):
    p = tmp_path / "x.p7m"
    p.write_bytes(b"x")
    with patch("builtins.open", side_effect=OSError("boom")):
        r = ver.verify_p7m(str(p))
    assert any("lettura" in e.lower() for e in r["errors"])


def test_verify_p7m_pkcs7_success_with_mock_cert(tmp_path):
    p = tmp_path / "sig.p7m"
    p.write_bytes(b"DERDATA")

    now = datetime.now(dt_tz.utc)
    cert = MagicMock()
    cert.serial_number = 42
    cert.not_valid_before_utc = now - timedelta(days=1)
    cert.not_valid_after_utc = now + timedelta(days=30)

    subj = MagicMock()
    iss = MagicMock()

    def attrs(oid):
        from cryptography.x509.oid import NameOID

        if oid == NameOID.COMMON_NAME:
            return [MagicMock(value="Mario Rossi")]
        if oid == NameOID.ORGANIZATION_NAME:
            return [MagicMock(value="ACME")]
        if oid == NameOID.EMAIL_ADDRESS:
            return [MagicMock(value="m@acme.it")]
        return []

    subj.get_attributes_for_oid = attrs
    iss.get_attributes_for_oid = attrs
    cert.subject = subj
    cert.issuer = iss

    with patch("apps.signatures.verification.pkcs7.load_der_pkcs7_certificates", return_value=[cert]):
        r = ver.verify_p7m(str(p))
    assert r["valid"] is True
    assert r["signers"][0]["common_name"] == "Mario Rossi"


def test_verify_p7m_expired_cert_invalid(tmp_path):
    p = tmp_path / "exp.p7m"
    p.write_bytes(b"x")
    past = datetime.now(dt_tz.utc) - timedelta(days=10)
    cert = MagicMock()
    cert.serial_number = 1
    cert.not_valid_before_utc = past - timedelta(days=365)
    cert.not_valid_after_utc = past
    cert.subject = MagicMock(get_attributes_for_oid=lambda oid: [])
    cert.issuer = MagicMock(get_attributes_for_oid=lambda oid: [])
    with patch("apps.signatures.verification.pkcs7.load_der_pkcs7_certificates", return_value=[cert]):
        r = ver.verify_p7m(str(p))
    assert r["valid"] is False
    assert r["signers"][0]["is_expired"] is True


def test_verify_p7m_pkcs7_parse_fails_opens_openssl(tmp_path):
    p = tmp_path / "bad.p7m"
    p.write_bytes(b"bad")
    openssl_out = """
Subject: CN = Test, O = Org, emailAddress = t@test.it
Issuer: CN = CA, O = Root
Not Before: Jan  1 00:00:00 2025 GMT
Not After : Jan  1 00:00:00 2030 GMT
"""
    with patch(
        "apps.signatures.verification.pkcs7.load_der_pkcs7_certificates",
        side_effect=ValueError("bad der"),
    ), patch("apps.signatures.verification.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0, stdout=openssl_out.encode(), stderr=b"")
        r = ver.verify_p7m(str(p))
    assert r["signers"]
    assert any("parsing" in e.lower() for e in r["errors"])


def test_verify_p7m_openssl_fallback_exception(tmp_path):
    p = tmp_path / "e.p7m"
    p.write_bytes(b"x")
    with patch(
        "apps.signatures.verification.pkcs7.load_der_pkcs7_certificates",
        return_value=[],
    ), patch(
        "apps.signatures.verification._verify_with_openssl",
        side_effect=RuntimeError("openssl down"),
    ):
        r = ver.verify_p7m(str(p))
    assert any("openssl fallback" in e.lower() for e in r["errors"])


def test_verify_p7m_empty_certs_opens_openssl(tmp_path):
    p = tmp_path / "empty.p7m"
    p.write_bytes(b"x")
    out = b"Subject: CN = Solo\nIssuer: CN = I\nNot Before: Jan  1 00:00:00 2025 GMT\nNot After : Jan  1 00:00:00 2030 GMT\n"
    with patch("apps.signatures.verification.pkcs7.load_der_pkcs7_certificates", return_value=[]), patch(
        "apps.signatures.verification.subprocess.run"
    ) as run:
        run.return_value = MagicMock(returncode=0, stdout=out, stderr=b"")
        r = ver.verify_p7m(str(p))
    assert r["signers"]


def test_extract_p7m_not_found():
    r = ver.extract_p7m_content("/no/file.p7m")
    assert r["success"] is False
    assert r["error"]


def test_extract_p7m_success_mock_subprocess(tmp_path):
    src = tmp_path / "doc.p7m"
    src.write_bytes(b"p7")
    outdir = tmp_path / "out"
    outdir.mkdir()
    dest = outdir / "doc"
    dest.write_bytes(b"payload")

    def isfile_side(path):
        ps = os.path.normpath(str(path))
        return ps == os.path.normpath(str(src)) or ps == os.path.normpath(str(dest))

    with patch("apps.signatures.verification.subprocess.run") as run, patch(
        "apps.signatures.verification.os.path.isfile",
        side_effect=isfile_side,
    ), patch("apps.signatures.verification.os.path.getsize", return_value=10):
        run.return_value = MagicMock(returncode=0, stderr=b"")
        r = ver.extract_p7m_content(str(src), output_dir=str(outdir))
    assert r["success"] is True
    assert r["original_name"] == "doc"
    assert r["content_type"] == "application/octet-stream"


def test_extract_p7m_non_p7m_extension(tmp_path):
    src = tmp_path / "blob.bin"
    src.write_bytes(b"x")
    def isfile_side(path):
        ps = os.path.normpath(str(path))
        return ps == os.path.normpath(str(src))

    with patch("apps.signatures.verification.subprocess.run") as run, patch(
        "apps.signatures.verification.os.path.isfile",
        side_effect=isfile_side,
    ):
        run.return_value = MagicMock(returncode=0, stderr=b"errmsg")
        r = ver.extract_p7m_content(str(src))
    assert r["success"] is False
    assert r["original_name"] == "blob.bin.extracted"
    assert "estrazione" in (r["error"] or "").lower()


def test_extract_p7m_subprocess_exception(tmp_path):
    src = tmp_path / "x.p7m"
    src.write_bytes(b"x")
    with patch("apps.signatures.verification.subprocess.run", side_effect=OSError("nope")):
        r = ver.extract_p7m_content(str(src), output_dir=str(tmp_path))
    assert r["success"] is False


def test_verify_signature_cades_mapping(tmp_path):
    p = tmp_path / "a.p7m"
    p.write_bytes(b"d")
    fake = {
        "valid": True,
        "signers": [
            {
                "common_name": "CN",
                "email": "e@e.it",
                "issuer": "I",
                "valid_from": "2025-01-01",
                "valid_to": "2030-01-01",
                "is_expired": False,
            }
        ],
        "errors": [],
    }
    with patch("apps.signatures.verification.verify_p7m", return_value=fake):
        r = ver.verify_signature(str(p), "cades")
    assert r["valid"] is True
    assert r["signer_cn"] == "CN"
    assert r["revocation_status"] == "good"


def test_verify_signature_pades_fallback():
    r = ver.verify_signature("/tmp/x.pdf", "pades")
    assert r["valid"] is True
    assert "PAdES" in r["signer_cn"]
    assert r["errors"]


def test_verify_signature_p7m_extension_forces_cades(tmp_path):
    p = tmp_path / "z.p7m"
    p.write_bytes(b"x")
    with patch("apps.signatures.verification.verify_p7m", return_value={"valid": False, "signers": [], "errors": []}):
        r = ver.verify_signature(str(p), "pades")
    assert r["signers"] == []


def test_apply_timestamp_returns_base64():
    b = ver.apply_timestamp("/any")
    assert isinstance(b, bytes)
    assert len(b) > 0


def test_verify_openssl_returncode_error():
    with patch("apps.signatures.verification.subprocess.run") as run:
        run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"bad cert")
        r = ver._verify_with_openssl("/x")
    assert r["errors"]


def test_verify_openssl_subprocess_raises():
    with patch("apps.signatures.verification.subprocess.run", side_effect=RuntimeError("spawn failed")):
        r = ver._verify_with_openssl("/x.p7m")
    assert any("spawn failed" in e for e in r["errors"])


def test_verify_openssl_success_parse():
    out = b"""
Subject: CN = Alice, O = Org, emailAddress = a@b.c
Issuer: CN = RootCA, O = CA
Not Before: Mar  1 10:00:00 2025 GMT
Not After : Mar  1 10:00:00 2030 GMT
"""
    with patch("apps.signatures.verification.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0, stdout=out, stderr=b"")
        r = ver._verify_with_openssl("/f.p7m")
    assert r["signers"]
    assert r["valid"]


def test_parse_openssl_cert_text_minimal():
    text = """
Subject: CN = OnlyCN
Issuer: CN = IssuerOnly
Not Before: Jan  2 00:00:00 2024 GMT
Not After : Jan  2 00:00:00 2026 GMT
"""
    signers = ver._parse_openssl_cert_text(text)
    assert signers and signers[0]["common_name"] == "OnlyCN"


def test_verify_p7m_openssl_errors_appended_with_signers(tmp_path):
    p = tmp_path / "both.p7m"
    p.write_bytes(b"x")
    with patch("apps.signatures.verification.pkcs7.load_der_pkcs7_certificates", return_value=[]), patch(
        "apps.signatures.verification._verify_with_openssl",
        return_value={
            "signers": [{"common_name": "A", "issuer": "I", "is_expired": False}],
            "valid": True,
            "errors": ["warning line"],
        },
    ):
        r = ver.verify_p7m(str(p))
    assert r["signers"]
    assert "warning line" in r["errors"]


def test_parse_openssl_cert_expired_flag_skips_bad_iso():
    text = """Subject: CN = Zed
Issuer: CN = Way
Not Before: Jan  2 00:00:00 2024 GMT
Not After : Jan  2 00:00:00 2026 GMT
"""
    with patch.object(ver, "_parse_openssl_date", return_value="not-an-iso-string"):
        signers = ver._parse_openssl_cert_text(text)
    assert signers[0]["common_name"] == "Zed"
    assert signers[0]["is_expired"] is False


def test_parse_openssl_cert_not_after_colon_variant():
    text = """
Subject: CN = X
Issuer: CN = Y
Not Before: Jan  2 00:00:00 2024 GMT
Not After: Jan  2 00:00:00 2026 GMT
"""
    signers = ver._parse_openssl_cert_text(text)
    assert signers


def test_extract_field_and_parse_date():
    assert ver._extract_field("CN = Foo, O = Bar", "CN") == "Foo"
    assert ver._parse_openssl_date("not a date") == "not a date"


def test_parse_openssl_date_iso_branch():
    iso_like = ver._parse_openssl_date("Mar 15 12:00:00 2030 GMT")
    assert "2030" in iso_like


def test_guess_content_type_edges():
    assert ver._guess_content_type("a.pdf") == "application/pdf"
    assert ver._guess_content_type("x.docx") == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert ver._guess_content_type("x.unknown") == "application/octet-stream"
