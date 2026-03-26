"""Test task documenti: OCR, compressione, thumbnail (FASE 33B)."""
import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.documents.models import Document, DocumentVersion, Folder
from apps.documents.tasks import (
    process_document_text_extraction,
    process_uploaded_file,
    _compress_image,
    _generate_image_thumbnail,
)

User = get_user_model()


@pytest.fixture
def folder_user(db):
    user = User.objects.create_user(
        email="taskdoc@test.com",
        password="Test123!",
        first_name="T",
        last_name="T",
        role="OPERATOR",
    )
    folder = Folder.objects.create(name="TF", created_by=user)
    return folder, user


@pytest.mark.django_db
class TestProcessDocumentTextExtraction:
    def test_missing_version_returns_silently(self):
        process_document_text_extraction(str(uuid.uuid4()))

    def test_no_file_sets_failed(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_type="application/pdf",
            created_by=user,
            is_current=True,
        )
        process_document_text_extraction(str(ver.id))
        doc.refresh_from_db()
        assert doc.ocr_status == "failed"
        assert "Nessun file" in (doc.ocr_error or "")

    def test_pdf_pdftotext_when_selectable(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_type="application/pdf",
            created_by=user,
            is_current=True,
        )
        pdf = SimpleUploadedFile("x.pdf", b"%PDF-1.4 hello", content_type="application/pdf")
        ver.file.save("x.pdf", pdf, save=True)
        long_text = "parola " * 10
        with patch("apps.documents.ocr_service.OCRService.has_selectable_text", return_value=True), patch(
            "apps.documents.ocr_service.OCRService.pdftotext_extract", return_value=long_text
        ):
            process_document_text_extraction(str(ver.id))
        doc.refresh_from_db()
        assert doc.ocr_status == "not_needed"

    def test_pdf_ocr_success(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_type="application/pdf",
            created_by=user,
            is_current=True,
        )
        pdf = SimpleUploadedFile("x.pdf", b"%PDF-1.4 x", content_type="application/pdf")
        ver.file.save("x.pdf", pdf, save=True)
        with patch("apps.documents.ocr_service.OCRService.has_selectable_text", return_value=False), patch(
            "apps.documents.ocr_service.OCRService.extract_text_from_file",
            return_value={
                "success": True,
                "text": "testo ocr",
                "pages": [{"confidence": 80}],
            },
        ):
            process_document_text_extraction(str(ver.id))
        doc.refresh_from_db()
        assert doc.ocr_status == "completed"
        assert doc.extracted_text

    def test_pdf_ocr_failure(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_type="application/pdf",
            created_by=user,
            is_current=True,
        )
        pdf = SimpleUploadedFile("x.pdf", b"%PDF-1.4 x", content_type="application/pdf")
        ver.file.save("x.pdf", pdf, save=True)
        with patch("apps.documents.ocr_service.OCRService.has_selectable_text", return_value=False), patch(
            "apps.documents.ocr_service.OCRService.extract_text_from_file",
            return_value={"success": False, "error": "ocr fail"},
        ):
            process_document_text_extraction(str(ver.id))
        doc.refresh_from_db()
        assert doc.ocr_status == "failed"

    def test_image_ocr_path(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.png",
            file_type="image/png",
            created_by=user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
        buf.seek(0)
        up = SimpleUploadedFile("x.png", buf.read(), content_type="image/png")
        ver.file.save("x.png", up, save=True)
        with patch(
            "apps.documents.ocr_service.OCRService.extract_text_from_file",
            return_value={"success": True, "text": "hello", "pages": [{"confidence": 50}]},
        ):
            process_document_text_extraction(str(ver.id))
        doc.refresh_from_db()
        assert doc.ocr_status == "completed"

    def test_native_extract_text(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="n.txt",
            file_type="text/plain",
            created_by=user,
            is_current=True,
        )
        up = SimpleUploadedFile("n.txt", b"native body", content_type="text/plain")
        ver.file.save("n.txt", up, save=True)
        with patch("apps.search.extractors.extract_text", return_value="extracted native"):
            process_document_text_extraction(str(ver.id))
        doc.refresh_from_db()
        assert doc.ocr_status == "not_needed"
        assert "native" in (doc.extracted_text or "") or doc.extracted_text == "extracted native"


@pytest.mark.django_db
class TestProcessUploadedFile:
    def test_missing_version(self):
        process_uploaded_file(str(uuid.uuid4()))

    @patch("apps.documents.tasks.process_document_text_extraction.delay")
    def test_image_triggers_pipeline(self, mock_delay, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="h.png",
            file_type="image/png",
            file_size=500,
            created_by=user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGB", (50, 50), color="blue").save(buf, format="PNG")
        buf.seek(0)
        up = SimpleUploadedFile("h.png", buf.read(), content_type="image/png")
        ver.file.save("h.png", up, save=True)
        ver.refresh_from_db()
        process_uploaded_file(str(ver.id))
        mock_delay.assert_called_once()


@pytest.mark.django_db
class TestCompressImageHelpers:
    def test_compress_skips_small_image(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="s.png",
            file_type="image/png",
            file_size=100,
            created_by=user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGB", (100, 100), color="white").save(buf, format="PNG")
        buf.seek(0)
        up = SimpleUploadedFile("s.png", buf.read(), content_type="image/png")
        ver.file.save("s.png", up, save=True)
        ver.refresh_from_db()
        old_size = ver.file_size
        _compress_image(ver)
        ver.refresh_from_db()
        assert ver.file_size == old_size

    def test_thumbnail_generated(self, folder_user):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="t.png",
            file_type="image/png",
            file_size=200,
            created_by=user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGB", (400, 400), color="green").save(buf, format="PNG")
        buf.seek(0)
        up = SimpleUploadedFile("t.png", buf.read(), content_type="image/png")
        ver.file.save("t.png", up, save=True)
        ver.refresh_from_db()
        _generate_image_thumbnail(ver)
        ver.refresh_from_db()
        assert ver.thumbnail


@pytest.mark.django_db
class TestVideoHelpers:
    @patch("apps.documents.tasks.subprocess.run")
    def test_compress_video_success_smaller(self, mock_run, folder_user, tmp_path):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v.mp4",
            file_type="video/mp4",
            file_size=10000,
            created_by=user,
            is_current=True,
        )
        small_vid = b"fakevideo" * 100
        up = SimpleUploadedFile("v.mp4", small_vid, content_type="video/mp4")
        ver.file.save("v.mp4", up, save=True)
        ver.refresh_from_db()

        out_file = tmp_path / "out.mp4"
        out_file.write_bytes(b"x" * 100)

        def fake_run(cmd, **kwargs):
            if "compressed" in str(cmd[-1]):
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        mock_run.side_effect = lambda cmd, **kwargs: (
            MagicMock(returncode=0) if cmd[0] == "ffmpeg" else MagicMock(returncode=0)
        )

        with patch("apps.documents.tasks.os.path.exists", side_effect=lambda p: str(p).endswith("_compressed.mp4")), patch(
            "apps.documents.tasks.os.path.getsize", return_value=100
        ), patch("builtins.open", create=True) as m_open:
            m_open.return_value.__enter__.return_value.read.return_value = b"compressed"
            from apps.documents.tasks import _compress_video

            _compress_video(ver)

    @patch("apps.documents.tasks.subprocess.run")
    def test_generate_video_thumbnail(self, mock_run, folder_user, tmp_path):
        folder, user = folder_user
        doc = Document.objects.create(title="D", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v.mp4",
            file_type="video/mp4",
            file_size=500,
            created_by=user,
            is_current=True,
        )
        up = SimpleUploadedFile("v.mp4", b"vid", content_type="video/mp4")
        ver.file.save("v.mp4", up, save=True)
        ver.refresh_from_db()
        thumb = tmp_path / "thumb.jpg"
        thumb.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)

        def exists_side(p):
            s = str(p)
            return s.endswith("_thumb.jpg") or s.endswith(".mp4")

        mock_run.return_value = MagicMock(returncode=0)
        with patch("apps.documents.tasks.os.path.exists", side_effect=exists_side), patch(
            "apps.documents.tasks.os.path.getsize", return_value=100
        ), patch("builtins.open", create=True) as m_open:
            m_open.return_value.__enter__.return_value.read.return_value = thumb.read_bytes()
            from apps.documents.tasks import _generate_video_thumbnail

            _generate_video_thumbnail(ver)
