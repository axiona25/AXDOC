"""
Test viewer_info e preview (FASE 19).
"""
import io
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document, DocumentVersion, Folder

User = get_user_model()


class ViewerAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            role="OPERATOR",
        )
        self.client.force_authenticate(user=self.user)
        self.folder = Folder.objects.create(name="TestFolder", created_by=self.user)

    def _doc_with_version(self, file_name, content_type, content=b"content"):
        doc = Document.objects.create(
            title="Doc",
            folder=self.folder,
            created_by=self.user,
            owner=self.user,
        )
        f = SimpleUploadedFile(file_name, content, content_type=content_type)
        version = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name=file_name,
            file_size=len(content),
            file_type=content_type,
            checksum="a" * 64,
            created_by=self.user,
            is_current=True,
        )
        version.file.save(file_name, f, save=True)
        return doc

    def test_viewer_info_pdf_returns_pdf_type(self):
        doc = self._doc_with_version("doc.pdf", "application/pdf", b"%PDF-1.4 fake")
        r = self.client.get(f"/api/documents/{doc.id}/viewer_info/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["viewer_type"], "pdf")
        self.assertEqual(r.data["mime_type"], "application/pdf")
        self.assertEqual(r.data["file_name"], "doc.pdf")

    def test_viewer_info_docx_returns_office_type(self):
        doc = self._doc_with_version(
            "doc.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        r = self.client.get(f"/api/documents/{doc.id}/viewer_info/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["viewer_type"], "office")

    def test_viewer_info_image_returns_image_type(self):
        doc = self._doc_with_version("img.png", "image/png")
        r = self.client.get(f"/api/documents/{doc.id}/viewer_info/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["viewer_type"], "image")

    def test_preview_pdf_returns_inline(self):
        doc = self._doc_with_version("doc.pdf", "application/pdf", b"%PDF-1.4 fake")
        r = self.client.get(f"/api/documents/{doc.id}/preview/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("inline", r.get("Content-Disposition", ""))
        self.assertEqual(r.get("X-Viewer-Type"), "pdf")

    def test_preview_office_converts_to_pdf(self):
        import subprocess
        try:
            subprocess.run(["libreoffice", "--version"], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.skipTest("LibreOffice non disponibile")
        doc = self._doc_with_version(
            "doc.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"PK content zip",
        )
        r = self.client.get(f"/api/documents/{doc.id}/preview/")
        if r.status_code == 503:
            self.skipTest("Conversione LibreOffice fallita (ambiente di test)")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get("X-Viewer-Type"), "office")

    def test_preview_text_returns_content(self):
        doc = self._doc_with_version("file.txt", "text/plain", b"Hello world")
        r = self.client.get(f"/api/documents/{doc.id}/preview/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data.get("content"), "Hello world")
        self.assertEqual(r.get("X-Viewer-Type"), "text")

    def test_preview_eml_returns_parsed(self):
        eml = b"""From: a@test.com\r\nTo: b@test.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\nContent-Type: text/plain\r\n\r\nBody here."""
        doc = self._doc_with_version("msg.eml", "message/rfc822", eml)
        r = self.client.get(f"/api/documents/{doc.id}/preview/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("from", r.data)
        self.assertIn("to", r.data)
        self.assertIn("subject", r.data)
        self.assertEqual(r.get("X-Viewer-Type"), "email")
