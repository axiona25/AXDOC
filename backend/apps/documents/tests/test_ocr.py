"""Servizio OCR (FASE 30)."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from pypdf import PdfWriter

from apps.documents.ocr_service import OCRService


def _tesseract_available():
    return shutil.which("tesseract") is not None


@pytest.mark.skipif(not _tesseract_available(), reason="Tesseract non installato")
def test_extract_text_from_image():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name
    try:
        img = Image.new("RGB", (400, 120), color="white")
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "Hello OCR", fill="black")
        img.save(path)
        result = OCRService.extract_text_from_file(path, lang="eng")
        assert result["success"] is True
        assert "Hello" in result["text"] or "OCR" in result["text"]
    finally:
        Path(path).unlink(missing_ok=True)


def test_has_selectable_text_returns_false_for_blank_pdf():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    try:
        w = PdfWriter()
        w.add_blank_page(width=200, height=200)
        with open(path, "wb") as f:
            w.write(f)
        assert OCRService.has_selectable_text(path, min_chars=50) is False
    finally:
        Path(path).unlink(missing_ok=True)


def test_unsupported_format_returns_error():
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp:
        path = tmp.name
    try:
        Path(path).write_text("x")
        r = OCRService.extract_text_from_file(path)
        assert r["success"] is False
        assert r["method"] == "unsupported"
    finally:
        Path(path).unlink(missing_ok=True)


def test_extract_handles_exception_gracefully():
    with patch.object(OCRService, "_extract_from_image", side_effect=RuntimeError("boom")):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name
        try:
            Image.new("RGB", (10, 10)).save(path)
            r = OCRService.extract_text_from_file(path)
            assert r["success"] is False
            assert "boom" in (r.get("error") or "")
        finally:
            Path(path).unlink(missing_ok=True)
