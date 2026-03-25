"""
Viewer documenti: tipi visualizzabili e utilità (FASE 19).
"""
import email
import mimetypes
import os
import shutil
import subprocess
import tempfile
from email import policy as email_policy

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

# Estensioni extra non sempre presenti nel registro mimetypes di Python
EXTRA_MIME_MAP = {
    ".p7m": "application/pkcs7-mime",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".wmv": "video/x-ms-wmv",
    ".mpg": "video/mpeg",
    ".mpeg": "video/mpeg",
    ".3gp": "video/3gpp",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".eml": "message/rfc822",
    ".md": "text/markdown",
}


def detect_mime_type(file_name: str, fallback: str = "") -> str:
    """
    Determina il MIME type dal nome file.
    Usa il registro di Python + estensioni extra.
    Se fallback è un MIME valido (non octet-stream), lo usa.
    """
    if fallback and fallback != "application/octet-stream":
        return fallback

    if not file_name:
        return fallback or "application/octet-stream"

    ext = os.path.splitext(file_name)[1].lower()

    if ext in EXTRA_MIME_MAP:
        return EXTRA_MIME_MAP[ext]

    guess, _ = mimetypes.guess_type(file_name)
    if guess:
        return guess

    return fallback or "application/octet-stream"


VIEWABLE_TYPES = {
    "pdf": ["application/pdf"],
    "office": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/vnd.oasis.opendocument.text",
        "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.presentation",
    ],
    "image": [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        "image/bmp",
        "image/tiff",
        "image/heic",
        "image/heif",
    ],
    "video": [
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-msvideo",
        "video/avi",
        "video/mpeg",
        "video/x-matroska",
        "video/x-ms-wmv",
        "video/3gpp",
        "video/ogg",
    ],
    "audio": [
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
        "audio/mp4",
        "audio/x-wav",
        "audio/webm",
        "audio/aac",
        "audio/flac",
    ],
    "text": [
        "text/plain",
        "text/csv",
        "text/xml",
        "application/json",
        "text/html",
        "text/markdown",
        "application/xml",
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


def convert_image_to_web(input_path: str) -> tuple[str, str]:
    """
    Converte immagini non-web (TIFF, BMP, HEIC) in JPEG usando Pillow.
    Ritorna (output_path, mime_type).
    """
    from PIL import Image

    out_dir = tempfile.mkdtemp()
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, base + ".jpg")

    try:
        img = Image.open(input_path)
        if img.mode in ("RGBA", "P", "LA"):
            output_path = os.path.join(out_dir, base + ".png")
            img.save(output_path, "PNG")
            return output_path, "image/png"
        if img.mode == "CMYK":
            img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=90)
        return output_path, "image/jpeg"
    except Exception as e:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise Exception(f"Image conversion failed: {e}") from e


def convert_video_to_mp4(input_path: str) -> str:
    """
    Converte video non-web (MOV, AVI, MPEG, MKV, WMV) in MP4 H.264 usando FFmpeg.
    Ritorna path del MP4 generato.
    """
    out_dir = tempfile.mkdtemp()
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(out_dir, base + ".mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vcodec",
        "libx264",
        "-crf",
        "23",
        "-preset",
        "fast",
        "-acodec",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-vf",
        "scale='min(1920,iw)':-2",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[:500]
            raise Exception(f"FFmpeg conversion failed: {stderr}")
        if not os.path.exists(output_path):
            raise Exception("MP4 output not found after conversion")
        return output_path
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise


# MIME types che richiedono conversione prima della visualizzazione
NEEDS_IMAGE_CONVERSION = {"image/tiff", "image/bmp", "image/heic", "image/heif"}
NEEDS_VIDEO_CONVERSION = {
    "video/quicktime",
    "video/x-msvideo",
    "video/avi",
    "video/mpeg",
    "video/x-matroska",
    "video/x-ms-wmv",
    "video/3gpp",
    "video/ogg",
}
# Formati video nativi del browser (NON richiedono conversione)
BROWSER_NATIVE_VIDEO = {"video/mp4", "video/webm"}
