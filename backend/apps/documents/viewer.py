"""
Viewer documenti: tipi visualizzabili e utilità (FASE 19).
"""
import email
import os
import subprocess
import tempfile
from email import policy as email_policy

VIEWABLE_TYPES = {
    "pdf": ["application/pdf"],
    "office": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
    ],
    "image": [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    ],
    "video": ["video/mp4", "video/avi", "video/quicktime", "video/webm"],
    "audio": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4"],
    "text": [
        "text/plain",
        "text/csv",
        "text/xml",
        "application/json",
        "text/html",
    ],
    "email": ["message/rfc822"],
}


def get_viewer_type(mime_type: str) -> str:
    """Ritorna il tipo viewer (pdf, office, image, video, audio, text, email, generic)."""
    if not mime_type:
        return "generic"
    mime = (mime_type or "").strip().lower()
    for viewer, types in VIEWABLE_TYPES.items():
        if mime in types:
            return viewer
    return "generic"


def convert_office_to_pdf(input_path: str) -> str:
    """
    Converte file Office in PDF con LibreOffice headless.
    Ritorna path del PDF generato in directory temporanea.
    """
    out_dir = tempfile.mkdtemp()
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        out_dir,
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise Exception(
            f"LibreOffice conversion failed: {result.stderr.decode() if result.stderr else 'unknown'}"
        )
    base = os.path.splitext(os.path.basename(input_path))[0]
    pdf_path = os.path.join(out_dir, base + ".pdf")
    if not os.path.exists(pdf_path):
        raise Exception("PDF output not found after conversion")
    return pdf_path


def parse_eml(eml_path: str) -> dict:
    """
    Parsa file .eml, ritorna { from, to, subject, date, body_text, body_html, attachments }.
    """
    with open(eml_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=email_policy.default)
    result = {
        "from": str(msg.get("From", "")),
        "to": str(msg.get("To", "")),
        "subject": str(msg.get("Subject", "")),
        "date": str(msg.get("Date", "")),
        "body_text": "",
        "body_html": "",
        "attachments": [],
    }
    for part in msg.walk():
        ct = part.get_content_type()
        if ct == "text/plain" and not result["body_text"]:
            try:
                result["body_text"] = part.get_content() or ""
            except Exception:
                result["body_text"] = ""
        elif ct == "text/html" and not result["body_html"]:
            try:
                result["body_html"] = part.get_content() or ""
            except Exception:
                result["body_html"] = ""
        elif part.get_filename():
            raw = part.get_payload(decode=True) or b""
            result["attachments"].append({
                "filename": part.get_filename(),
                "content_type": ct,
                "size": len(raw),
            })
    return result
