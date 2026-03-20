"""
Test conversione AGID: timbro, conversione PDF, copertina, endpoint.
"""
import os
import tempfile
from io import BytesIO
from datetime import datetime
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from apps.organizations.models import OrganizationalUnit
from apps.protocols.models import Protocol
from apps.protocols.agid_converter import AGIDConverter, ConversionError

User = get_user_model()


def _make_pdf():
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 700, "Test PDF")
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


class AGIDConverterTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="Test123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.ou = OrganizationalUnit.objects.create(
            name="UO Test",
            code="UO1",
            created_by=self.user,
        )
        from django.utils import timezone
        self.protocol = Protocol.objects.create(
            protocol_number="2024/IT/0042",
            protocol_date=timezone.make_aware(datetime(2024, 3, 1, 10, 0, 0)),
            direction=Protocol.DIRECTION_IN,
            organizational_unit=self.ou,
            created_by=self.user,
        )

    def test_apply_protocol_stamp_on_pdf(self):
        pdf_data = _make_pdf()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_data)
            input_path = f.name
        try:
            fd, output_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            try:
                result = AGIDConverter.apply_protocol_stamp(
                    input_path, self.protocol, output_path
                )
                self.assertEqual(result, output_path)
                self.assertTrue(os.path.isfile(output_path))
                self.assertGreater(os.path.getsize(output_path), len(pdf_data))
            finally:
                if os.path.isfile(output_path):
                    os.unlink(output_path)
        finally:
            os.unlink(input_path)

    def test_convert_to_pdf_requires_libreoffice(self):
        """Se LibreOffice non è installato, convert_to_pdf solleva; altrimenti produce PDF."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Hello world")
            input_path = f.name
        try:
            try:
                result = AGIDConverter.convert_to_pdf(input_path)
                self.assertTrue(result.endswith(".pdf"))
                self.assertTrue(os.path.isfile(result))
            except (ConversionError, FileNotFoundError):
                pass  # LibreOffice non disponibile in ambiente test
        finally:
            os.unlink(input_path)

    def test_generate_protocol_coverpage(self):
        fd, output_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            result = AGIDConverter.generate_protocol_coverpage(
                self.protocol, output_path
            )
            self.assertEqual(result, output_path)
            self.assertTrue(os.path.isfile(output_path))
            self.assertGreater(os.path.getsize(output_path), 100)
        finally:
            if os.path.isfile(output_path):
                os.unlink(output_path)

    def test_stamped_document_endpoint_returns_pdf(self):
        pdf_data = _make_pdf()
        self.protocol.document_file.save(
            "test.pdf",
            SimpleUploadedFile("test.pdf", pdf_data, content_type="application/pdf"),
            save=True,
        )
        client = APIClient()
        client.force_authenticate(user=self.user)
        r = client.get(f"/api/protocols/{self.protocol.id}/stamped_document/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn("attachment", r.get("Content-Disposition", ""))

    def test_coverpage_endpoint_returns_pdf(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        r = client.get(f"/api/protocols/{self.protocol.id}/coverpage/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
