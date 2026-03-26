"""Edge case OCR (FASE 33)."""
import pytest
from pathlib import Path

from PIL import Image

from apps.documents.ocr_service import OCRService


@pytest.mark.django_db
class TestOCREdgeCases:
    def test_unsupported_extension(self, tmp_path):
        p = tmp_path / "file.xyz"
        p.write_text("x", encoding="utf-8")
        result = OCRService.extract_text_from_file(str(p))
        assert result["success"] is False
        assert result.get("method") == "unsupported"

    def test_corrupted_pdf_returns_error(self, tmp_path):
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"not a pdf")
        result = OCRService.extract_text_from_file(str(bad_pdf))
        assert result["success"] is False

    def test_empty_image_returns_ocr_result(self, tmp_path):
        img = Image.new("RGB", (100, 100), "white")
        img_path = tmp_path / "blank.png"
        img.save(str(img_path))
        result = OCRService.extract_text_from_file(str(img_path))
        assert result["success"] is True
        assert isinstance(result.get("text", ""), str)
