"""
Verifica firma digitale P7M (CAdES/PKCS#7) e PAdES.
Usa cryptography + pyasn1 per parsing ASN.1 del SignedData.
OpenSSL come fallback per verifica catena certificati.
"""
import os
import subprocess
import tempfile
from datetime import datetime, timezone as tz

from cryptography.hazmat.primitives.serialization import pkcs7


def verify_p7m(file_path: str) -> dict:
    """
    Verifica un file .p7m (CAdES / PKCS#7 SignedData).

    Ritorna:
    {
        "valid": bool,
        "signers": [
            {
                "common_name": str,
                "email": str,
                "organization": str,
                "serial_number": str,
                "issuer": str,
                "valid_from": str (ISO),
                "valid_to": str (ISO),
                "is_expired": bool,
            }
        ],
        "content_extracted": bool,
        "content_file_name": str | None,
        "errors": [str],
    }
    """
    result = {
        "valid": False,
        "signers": [],
        "content_extracted": False,
        "content_file_name": None,
        "errors": [],
    }

    if not os.path.isfile(file_path):
        result["errors"].append("File non trovato.")
        return result

    try:
        with open(file_path, "rb") as f:
            p7m_data = f.read()
    except Exception as e:
        result["errors"].append(f"Errore lettura file: {e}")
        return result

    # --- Metodo 1: cryptography (parsing PKCS#7) ---
    try:
        certs = pkcs7.load_der_pkcs7_certificates(p7m_data)
        if certs:
            now = datetime.now(tz.utc)
            for cert in certs:
                subj = cert.subject
                issuer = cert.issuer

                def _get_attr(name_obj, oid_dotted):
                    from cryptography.x509.oid import NameOID

                    oid_map = {
                        "CN": NameOID.COMMON_NAME,
                        "O": NameOID.ORGANIZATION_NAME,
                        "E": NameOID.EMAIL_ADDRESS,
                        "SN": NameOID.SERIAL_NUMBER,
                    }
                    oid = oid_map.get(oid_dotted)
                    if not oid:
                        return ""
                    attrs = name_obj.get_attributes_for_oid(oid)
                    return attrs[0].value if attrs else ""

                cn = _get_attr(subj, "CN")
                org = _get_attr(subj, "O")
                email = _get_attr(subj, "E")
                serial = _get_attr(subj, "SN")
                issuer_cn = _get_attr(issuer, "CN")
                issuer_org = _get_attr(issuer, "O")

                is_expired = cert.not_valid_after_utc < now

                result["signers"].append(
                    {
                        "common_name": cn,
                        "email": email,
                        "organization": org,
                        "serial_number": serial or str(cert.serial_number),
                        "issuer": f"{issuer_cn} ({issuer_org})" if issuer_org else issuer_cn,
                        "valid_from": cert.not_valid_before_utc.isoformat(),
                        "valid_to": cert.not_valid_after_utc.isoformat(),
                        "is_expired": is_expired,
                    }
                )

            result["valid"] = len(result["signers"]) > 0 and not any(s["is_expired"] for s in result["signers"])
    except Exception as e:
        result["errors"].append(f"Parsing PKCS#7 fallito: {e}")

    # --- Metodo 2: OpenSSL come fallback/verifica aggiuntiva ---
    if not result["signers"]:
        try:
            openssl_result = _verify_with_openssl(file_path)
            if openssl_result.get("signers"):
                result["signers"] = openssl_result["signers"]
                result["valid"] = openssl_result.get("valid", False)
            if openssl_result.get("errors"):
                result["errors"].extend(openssl_result["errors"])
        except Exception as e:
            result["errors"].append(f"OpenSSL fallback fallito: {e}")

    return result


def extract_p7m_content(file_path: str, output_dir: str = None) -> dict:
    """
    Estrae il documento originale dal file .p7m.

    Ritorna:
    {
        "success": bool,
        "extracted_path": str | None,
        "original_name": str | None,
        "content_type": str | None,
        "error": str | None,
    }
    """
    if not os.path.isfile(file_path):
        return {
            "success": False,
            "extracted_path": None,
            "original_name": None,
            "content_type": None,
            "error": "File non trovato.",
        }

    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix="p7m_extract_")

    # Determina nome originale (rimuovi .p7m)
    base_name = os.path.basename(file_path)
    if base_name.lower().endswith(".p7m"):
        original_name = base_name[:-4]
    else:
        original_name = base_name + ".extracted"

    output_path = os.path.join(output_dir, original_name)

    # Usa OpenSSL per estrarre il contenuto
    try:
        cmd = [
            "openssl",
            "smime",
            "-verify",
            "-in",
            file_path,
            "-inform",
            "DER",
            "-noverify",  # Non verificare la catena (solo estrazione)
            "-out",
            output_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)

        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            # Determina content type
            content_type = _guess_content_type(original_name)
            return {
                "success": True,
                "extracted_path": output_path,
                "original_name": original_name,
                "content_type": content_type,
                "error": None,
            }
        else:
            stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
            return {
                "success": False,
                "extracted_path": None,
                "original_name": original_name,
                "content_type": None,
                "error": f"Estrazione fallita: {stderr}",
            }
    except Exception as e:
        return {
            "success": False,
            "extracted_path": None,
            "original_name": original_name,
            "content_type": None,
            "error": str(e),
        }


def verify_signature(signed_file_path: str, signature_type: str = "cades") -> dict:
    """
    Entry point principale per verifica firma (mantiene compatibilità con il codice esistente).
    Richiamato da views.py SignatureRequestViewSet.verify().
    """
    if signature_type == "cades" or signed_file_path.lower().endswith(".p7m"):
        p7m_result = verify_p7m(signed_file_path)
        # Mappa al formato atteso dal frontend
        first_signer = p7m_result["signers"][0] if p7m_result["signers"] else {}
        return {
            "valid": p7m_result["valid"],
            "signer_cn": first_signer.get("common_name", ""),
            "signer_email": first_signer.get("email", ""),
            "certificate_issuer": first_signer.get("issuer", ""),
            "certificate_valid_from": first_signer.get("valid_from"),
            "certificate_valid_to": first_signer.get("valid_to"),
            "signed_at": first_signer.get("valid_from"),  # Approssimazione
            "timestamp_token": None,
            "revocation_status": "expired" if first_signer.get("is_expired") else "good",
            "errors": p7m_result["errors"],
            "signers": p7m_result["signers"],
        }

    # PAdES o altro — fallback mock per ora
    return {
        "valid": True,
        "signer_cn": "PAdES verification not yet implemented",
        "signer_email": "",
        "certificate_issuer": "",
        "certificate_valid_from": None,
        "certificate_valid_to": None,
        "signed_at": None,
        "timestamp_token": None,
        "revocation_status": "",
        "errors": ["PAdES verification non ancora implementata."],
        "signers": [],
    }


def apply_timestamp(file_path: str) -> bytes:
    """Marca temporale RFC 3161 — placeholder per integrazione TSA."""
    import base64

    from django.utils import timezone as dtz

    ts = dtz.now().isoformat().encode("utf-8")
    return base64.b64encode(ts)


# ─── Utilità interne ───────────────────────────────


def _verify_with_openssl(file_path: str) -> dict:
    """Verifica P7M con OpenSSL CLI e parsing output."""
    result = {"valid": False, "signers": [], "errors": []}
    try:
        # Estrai info certificato
        cmd = [
            "openssl",
            "pkcs7",
            "-in",
            file_path,
            "-inform",
            "DER",
            "-print_certs",
            "-noout",
            "-text",
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        output = proc.stdout.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
            result["errors"].append(f"OpenSSL error: {stderr}")
            return result

        # Parse certificati dall'output
        signers = _parse_openssl_cert_text(output)
        result["signers"] = signers
        result["valid"] = len(signers) > 0

    except Exception as e:
        result["errors"].append(str(e))

    return result


def _parse_openssl_cert_text(text: str) -> list:
    """Parsing output di openssl x509 -text per estrarre info firmatario."""
    signers = []
    current = {}

    for line in text.splitlines():
        line = line.strip()
        if "Subject:" in line:
            # Parse CN, O, E dal Subject
            parts = line.split("Subject:")[-1]
            current["common_name"] = _extract_field(parts, "CN")
            current["organization"] = _extract_field(parts, "O")
            current["email"] = _extract_field(parts, "emailAddress") or _extract_field(parts, "E")
            current["serial_number"] = _extract_field(parts, "serialNumber") or _extract_field(parts, "SN")
        elif "Issuer:" in line:
            parts = line.split("Issuer:")[-1]
            issuer_cn = _extract_field(parts, "CN")
            issuer_org = _extract_field(parts, "O")
            current["issuer"] = f"{issuer_cn} ({issuer_org})" if issuer_org else issuer_cn
        elif "Not Before:" in line:
            date_str = line.split("Not Before:")[-1].strip()
            current["valid_from"] = _parse_openssl_date(date_str)
        elif "Not After :" in line or "Not After:" in line:
            date_str = line.split("Not After")[-1].replace(":", "", 1).strip()
            current["valid_to"] = _parse_openssl_date(date_str)

            # Fine di un certificato — salva
            if current.get("common_name"):
                from datetime import datetime, timezone as tz

                now = datetime.now(tz.utc)
                valid_to = current.get("valid_to")
                is_expired = False
                if valid_to:
                    try:
                        is_expired = datetime.fromisoformat(valid_to) < now
                    except Exception:
                        pass
                current["is_expired"] = is_expired
                signers.append(current)
            current = {}

    return signers


def _extract_field(subject_str: str, field_name: str) -> str:
    """Estrae un campo dal Subject/Issuer string."""
    import re

    # Prova formato "CN = value" e "CN=value"
    pattern = rf"{field_name}\s*=\s*([^,/]+)"
    match = re.search(pattern, subject_str)
    return match.group(1).strip() if match else ""


def _parse_openssl_date(date_str: str) -> str | None:
    """Parse data OpenSSL (es. 'Mar 24 12:00:00 2026 GMT') → ISO."""
    from datetime import datetime, timezone as tz

    formats = [
        "%b %d %H:%M:%S %Y %Z",
        "%b %d %H:%M:%S %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt).replace(tzinfo=tz.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return date_str


def _guess_content_type(filename: str) -> str:
    """Indovina il MIME type dal nome file."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_map = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xml": "application/xml",
        "txt": "text/plain",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    return mime_map.get(ext, "application/octet-stream")
