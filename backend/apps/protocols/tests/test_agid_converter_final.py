# FASE 35E.1 — Copertura: protocols/agid_converter.py
import os
from unittest.mock import MagicMock, patch

import pytest

from apps.protocols.agid_converter import AGIDConverter, ConversionError


@pytest.mark.django_db
class TestAGIDConverterFinal:
    def test_convert_file_not_found(self, tmp_path):
        p = tmp_path / "missing.docx"
        with pytest.raises(ConversionError, match="non trovato"):
            AGIDConverter.convert_to_pdf(str(p))

    def test_libreoffice_failure_and_timeout(self, tmp_path):
        f = tmp_path / "a.docx"
        f.write_bytes(b"x")
        with patch("apps.protocols.agid_converter.subprocess.run") as run:
            run.return_value = MagicMock(returncode=1, stderr=b"fail")
            with pytest.raises(ConversionError, match="LibreOffice"):
                AGIDConverter.convert_to_pdf(str(f))
        with patch("apps.protocols.agid_converter.subprocess.run") as run:
            import subprocess as sp

            run.side_effect = sp.TimeoutExpired("libreoffice", 60)
            with pytest.raises(ConversionError, match="Timeout"):
                AGIDConverter.convert_to_pdf(str(f))

    def test_libreoffice_no_pdf_output(self, tmp_path):
        f = tmp_path / "b.docx"
        f.write_bytes(b"x")
        outdir = tmp_path / "out"
        outdir.mkdir()
        with patch("apps.protocols.agid_converter.subprocess.run") as run:
            run.return_value = MagicMock(returncode=0, stderr=b"")
            with patch("apps.protocols.agid_converter.tempfile.mkdtemp", return_value=str(outdir)):
                with pytest.raises(ConversionError, match="non ha generato"):
                    AGIDConverter.convert_to_pdf(str(f))

    def test_apply_stamp_non_pdf_triggers_convert(self, tmp_path, django_user_model):
        from apps.organizations.models import OrganizationalUnit
        from apps.protocols.models import Protocol, ProtocolCounter
        from django.utils import timezone

        u = django_user_model.objects.create_user(
            email="agf@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="O", code="O")
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="in",
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=u,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=u,
        )
        docx = tmp_path / "x.docx"
        docx.write_bytes(b"x")
        out_pdf = tmp_path / "out.pdf"
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4")
        with patch.object(AGIDConverter, "convert_to_pdf", return_value=str(fake_pdf)):
            with patch("apps.protocols.agid_converter.PdfReader") as mock_reader:
                mock_page = MagicMock()
                mock_reader.return_value.pages = [mock_page]
                with patch("apps.protocols.agid_converter.PdfWriter") as mock_writer:
                    AGIDConverter.apply_protocol_stamp(str(docx), p, str(out_pdf))
        assert mock_writer.return_value.write.called
