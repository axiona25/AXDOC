"""
Task Celery per compressione immagini/video, thumbnail e estrazione testo/OCR (FASE 30).
"""
import logging
import os
import subprocess
import tempfile

from io import BytesIO

from celery import shared_task
from django.core.files.base import ContentFile
from PIL import Image


# ─── Configurazione ────────────────────────────────
MAX_IMAGE_DIMENSION = 2048
JPEG_QUALITY = 82
THUMBNAIL_SIZE = (300, 300)
VIDEO_CRF = 28  # Qualità video (più alto = più compresso, 23=default, 28=buono per web)
VIDEO_MAX_WIDTH = 1280

logger = logging.getLogger(__name__)


@shared_task(name="apps.documents.tasks.process_document_text_extraction")
def process_document_text_extraction(version_id: str):
    """
    OCR / pdftotext / estrazione nativa → Document.extracted_text + DocumentIndex.
    """
    from django.utils import timezone

    from apps.documents.models import Document, DocumentVersion
    from apps.documents.ocr_service import OCRService
    from apps.search.extractors import extract_text
    from apps.search.models import DocumentIndex

    try:
        version = DocumentVersion.objects.select_related("document").get(pk=version_id)
    except DocumentVersion.DoesNotExist:
        return

    doc = version.document
    if not version.file:
        Document.objects.filter(pk=doc.pk).update(
            ocr_status="failed",
            ocr_error="Nessun file allegato",
        )
        return

    path = getattr(version.file, "path", None)
    if not path or not os.path.isfile(path):
        Document.objects.filter(pk=doc.pk).update(
            ocr_status="failed",
            ocr_error="File non disponibile su disco",
        )
        return

    ext = os.path.splitext(path)[1].lower()
    mime = (version.file_type or "").lower()

    Document.objects.filter(pk=doc.pk).update(ocr_status="processing", ocr_error="")

    text = ""
    method = ""
    error_msg = ""
    ocr_confidence = None
    ocr_status = "completed"

    try:
        if ext == ".pdf":
            if OCRService.has_selectable_text(path):
                text = OCRService.pdftotext_extract(path)
                method = "pdftotext"
                ocr_status = "not_needed" if len(text.strip()) > 20 else "completed"
            else:
                ocr_result = OCRService.extract_text_from_file(path)
                if ocr_result["success"] and (ocr_result.get("text") or "").strip():
                    text = ocr_result["text"]
                    method = "ocr"
                    pages = ocr_result.get("pages") or []
                    confs = [p.get("confidence") or 0 for p in pages if p.get("confidence")]
                    ocr_confidence = sum(confs) / len(confs) if confs else None
                    ocr_status = "completed"
                else:
                    ocr_status = "failed"
                    error_msg = (ocr_result.get("error") or "OCR non ha prodotto testo")[:2000]
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
            ocr_result = OCRService.extract_text_from_file(path)
            if ocr_result["success"] and (ocr_result.get("text") or "").strip():
                text = ocr_result["text"]
                method = "ocr"
                p0 = (ocr_result.get("pages") or [{}])[0]
                ocr_confidence = p0.get("confidence")
                ocr_status = "completed"
            else:
                ocr_status = "failed"
                error_msg = (ocr_result.get("error") or "OCR non ha prodotto testo")[:2000]
        else:
            text = extract_text(path, mime)
            method = "native"
            ocr_status = "not_needed"
    except Exception as e:
        logger.exception("Text extraction failed for version %s", version_id)
        ocr_status = "failed"
        error_msg = str(e)[:2000]

    text_store = (text or "")[:50000]
    DocumentIndex.objects.update_or_create(
        document=doc,
        defaults={
            "document_version": version,
            "content": text_store,
            "extraction_method": method or ("failed" if error_msg else "none"),
            "error_message": (error_msg or "")[:500],
            "indexed_at": timezone.now(),
        },
    )

    Document.objects.filter(pk=doc.pk).update(
        extracted_text=text_store,
        ocr_status=ocr_status,
        ocr_confidence=ocr_confidence,
        ocr_error=error_msg[:2000] if error_msg else "",
    )


@shared_task(name="apps.documents.tasks.process_uploaded_file")
def process_uploaded_file(version_id: str):
    """
    Processa un file appena caricato:
    - Se immagine: comprimi + genera thumbnail
    - Se video: comprimi con ffmpeg + genera thumbnail dal primo frame
    """
    from apps.documents.models import DocumentVersion

    try:
        version = DocumentVersion.objects.get(pk=version_id)
    except DocumentVersion.DoesNotExist:
        return

    mime = (version.file_type or "").lower()

    if mime.startswith("image/") and mime not in ("image/gif", "image/svg+xml"):
        _compress_image(version)
        _generate_image_thumbnail(version)
    elif mime.startswith("video/"):
        _compress_video(version)
        _generate_video_thumbnail(version)

    process_document_text_extraction.delay(str(version_id))


def _compress_image(version):
    """Comprimi immagine con Pillow se necessario."""
    try:
        version.file.seek(0)
        img = Image.open(version.file)

        # Skip se già piccola
        width, height = img.size
        file_size = version.file_size
        if width <= MAX_IMAGE_DIMENSION and height <= MAX_IMAGE_DIMENSION and file_size <= 2 * 1024 * 1024:
            return

        # Ridimensiona
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

        # Converti RGBA → RGB per JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Salva compresso
        buffer = BytesIO()
        output_format = "JPEG"
        if version.file_type == "image/webp":
            output_format = "WEBP"
        img.save(buffer, format=output_format, quality=JPEG_QUALITY, optimize=True)
        new_size = len(buffer.getvalue())
        buffer.seek(0)

        old_size = version.file_size
        if new_size < old_size:
            # Aggiorna estensione se necessario
            name = version.file_name
            if output_format == "JPEG" and name.lower().endswith(".png"):
                name = name.rsplit(".", 1)[0] + ".jpg"
                version.file_name = name
                version.file_type = "image/jpeg"

            version.file.save(name, ContentFile(buffer.read()), save=False)
            version.file_size = new_size
            version.save(update_fields=["file", "file_name", "file_size", "file_type"])
            print(f"[COMPRESS] {version.file_name}: {old_size}B → {new_size}B")
    except Exception as e:
        print(f"[COMPRESS] Errore immagine {version.pk}: {e}")


def _generate_image_thumbnail(version):
    """Genera thumbnail per immagine."""
    try:
        version.file.seek(0)
        img = Image.open(version.file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        buffer.seek(0)

        thumb_name = f"thumb_{version.pk}.jpg"
        version.thumbnail.save(thumb_name, ContentFile(buffer.read()), save=True)
        print(f"[THUMBNAIL] Immagine {version.file_name}: generato")
    except Exception as e:
        print(f"[THUMBNAIL] Errore immagine {version.pk}: {e}")


def _compress_video(version):
    """Comprimi video con FFmpeg."""
    try:
        # Scarica il file in un temp
        version.file.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
            for chunk in version.file.chunks():
                tmp_in.write(chunk)
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path + "_compressed.mp4"

        # FFmpeg: comprimi con H.264, limita risoluzione, audio AAC
        cmd = [
            "ffmpeg", "-y", "-i", tmp_in_path,
            "-vcodec", "libx264", "-crf", str(VIDEO_CRF),
            "-preset", "fast",
            "-vf", f"scale='min({VIDEO_MAX_WIDTH},iw)':-2",
            "-acodec", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            tmp_out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)

        if result.returncode == 0 and os.path.exists(tmp_out_path):
            new_size = os.path.getsize(tmp_out_path)
            old_size = version.file_size
            if new_size < old_size:
                with open(tmp_out_path, "rb") as f:
                    version.file.save(version.file_name, ContentFile(f.read()), save=False)
                version.file_size = new_size
                version.save(update_fields=["file", "file_size"])
                print(f"[COMPRESS] Video {version.file_name}: {old_size}B → {new_size}B")
            else:
                print(f"[COMPRESS] Video {version.file_name}: compresso non più piccolo, skip")
        else:
            stderr = result.stderr.decode("utf-8", errors="replace")[:500]
            print(f"[COMPRESS] FFmpeg errore: {stderr}")

        # Cleanup
        for p in [tmp_in_path, tmp_out_path]:
            if os.path.exists(p):
                os.unlink(p)

    except Exception as e:
        print(f"[COMPRESS] Errore video {version.pk}: {e}")


def _generate_video_thumbnail(version):
    """Genera thumbnail dal primo frame del video con FFmpeg."""
    try:
        version.file.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
            for chunk in version.file.chunks():
                tmp_in.write(chunk)
            tmp_in_path = tmp_in.name

        tmp_thumb_path = tmp_in_path + "_thumb.jpg"

        cmd = [
            "ffmpeg", "-y", "-i", tmp_in_path,
            "-vframes", "1", "-ss", "1",
            "-vf", f"scale={THUMBNAIL_SIZE[0]}:-1",
            tmp_thumb_path,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0 and os.path.exists(tmp_thumb_path):
            with open(tmp_thumb_path, "rb") as f:
                thumb_name = f"thumb_{version.pk}.jpg"
                version.thumbnail.save(thumb_name, ContentFile(f.read()), save=True)
            print(f"[THUMBNAIL] Video {version.file_name}: generato")

        # Cleanup
        for p in [tmp_in_path, tmp_thumb_path]:
            if os.path.exists(p):
                os.unlink(p)

    except Exception as e:
        print(f"[THUMBNAIL] Errore video {version.pk}: {e}")
