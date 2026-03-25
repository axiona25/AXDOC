"""
OCR con Tesseract (FASE 30): PDF immagine e immagini.
"""
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

import pytesseract
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)


class OCRService:
    """Estrazione testo via Tesseract."""

    DEFAULT_LANG = "ita+eng"
    DEFAULT_DPI = 300

    @classmethod
    def get_lang(cls) -> str:
        return getattr(settings, "OCR_TESSERACT_LANG", cls.DEFAULT_LANG)

    @classmethod
    def max_pdf_pages(cls) -> int:
        return int(getattr(settings, "OCR_MAX_PDF_PAGES", 30))

    @classmethod
    def extract_text_from_file(cls, file_path: str, lang: Optional[str] = None) -> dict[str, Any]:
        lang = lang or cls.get_lang()
        ext = Path(file_path).suffix.lower()

        try:
            if ext == ".pdf":
                return cls._extract_from_pdf(file_path, lang)
            if ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
                return cls._extract_from_image(file_path, lang)
            return {
                "text": "",
                "pages": [],
                "language": lang,
                "method": "unsupported",
                "success": False,
                "error": f"Formato non supportato per OCR: {ext}",
            }
        except Exception as e:
            logger.exception("OCR failed for %s", file_path)
            return {
                "text": "",
                "pages": [],
                "language": lang,
                "method": "ocr",
                "success": False,
                "error": str(e),
            }

    @classmethod
    def _extract_from_pdf(cls, file_path: str, lang: str) -> dict[str, Any]:
        from pdf2image import convert_from_path

        max_pages = cls.max_pdf_pages()
        images = convert_from_path(file_path, dpi=cls.DEFAULT_DPI, last_page=max_pages)
        pages = []
        full_text = []

        for i, image in enumerate(images, 1):
            data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
            confidences = [c for c in data["conf"] if c != -1 and c > 0]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            page_text = pytesseract.image_to_string(image, lang=lang).strip()
            full_text.append(page_text)
            pages.append({"page": i, "text": page_text, "confidence": round(avg_conf, 1)})

        return {
            "text": "\n\n".join(full_text),
            "pages": pages,
            "language": lang,
            "method": "ocr",
            "success": True,
            "error": None,
        }

    @classmethod
    def _extract_from_image(cls, file_path: str, lang: str) -> dict[str, Any]:
        image = Image.open(file_path)
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        confidences = [c for c in data["conf"] if c != -1 and c > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        text = pytesseract.image_to_string(image, lang=lang).strip()

        return {
            "text": text,
            "pages": [{"page": 1, "text": text, "confidence": round(avg_conf, 1)}],
            "language": lang,
            "method": "ocr",
            "success": True,
            "error": None,
        }

    @classmethod
    def has_selectable_text(cls, file_path: str, min_chars: int = 50) -> bool:
        ext = Path(file_path).suffix.lower()
        if ext != ".pdf":
            return False
        try:
            result = subprocess.run(
                ["pdftotext", file_path, "-"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            text = (result.stdout or "").strip()
            return len(text) > min_chars
        except Exception:
            return False

    @classmethod
    def pdftotext_extract(cls, file_path: str) -> str:
        try:
            result = subprocess.run(
                ["pdftotext", file_path, "-"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return (result.stdout or "").strip()
        except Exception as e:
            logger.warning("pdftotext failed: %s", e)
            return ""
