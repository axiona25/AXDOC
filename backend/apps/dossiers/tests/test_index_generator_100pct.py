"""Copertura mirata apps.dossiers.index_generator (mock reportlab Canvas)."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone as dj_tz

from apps.documents.models import Document, Folder
from apps.dossiers.index_generator import _draw_text, generate_dossier_index_pdf
from apps.dossiers.models import Dossier, DossierDocument, DossierEmail, DossierFolder
from apps.organizations.models import OrganizationalUnit, Tenant

User = get_user_model()


def _default_tenant():
    return Tenant.objects.get_or_create(slug="default", defaults={"name": "Default Org"})[0]


@pytest.mark.django_db
class TestIndexGenerator:
    def test_draw_text_coerces_empty(self):
        c = MagicMock()
        _draw_text(c, 1, 2, None)
        c.drawString.assert_called()
        args = c.drawString.call_args[0]
        assert args[2] == ""

    def test_generate_empty_dossier_mock_canvas(self):
        tenant = _default_tenant()
        d = Dossier.objects.create(
            tenant=tenant,
            title="",
            identifier=f"IDX-{uuid.uuid4().hex[:10]}",
        )
        mock_c = MagicMock()
        with patch("apps.dossiers.index_generator.canvas.Canvas", return_value=mock_c):
            out = generate_dossier_index_pdf(d)
        assert isinstance(out, bytes)
        mock_c.save.assert_called_once()
        mock_c.showPage.assert_not_called()

    def test_generate_with_relations_and_agid_meta(self):
        tenant = _default_tenant()
        u = User.objects.create_user(email="idx_rel@test.com", password="x", role="OPERATOR")
        code = f"OU{uuid.uuid4().hex[:6]}"
        ou = OrganizationalUnit.objects.create(tenant=tenant, name="Office", code=code)
        closed = dj_tz.now()
        d = Dossier.objects.create(
            tenant=tenant,
            title="Oggetto fascicolo",
            identifier=f"IDX-{uuid.uuid4().hex[:10]}",
            responsible=u,
            organizational_unit=ou,
            classification_code="A",
            classification_label="Segreto",
            closed_at=closed,
        )
        doc = Document.objects.create(tenant=tenant, title="", folder=None)
        DossierDocument.objects.create(dossier=d, document=doc)
        folder = Folder.objects.create(tenant=tenant, name="F1")
        DossierFolder.objects.create(dossier=d, folder=folder)
        DossierEmail.objects.create(
            dossier=d,
            email_type="pec",
            from_address="a@pec.it",
            subject="Oggetto mail lungo " * 3,
            received_at=dj_tz.now(),
        )
        meta = {f"k{i}": f"v{i}" for i in range(45)}
        mock_c = MagicMock()
        with patch("apps.dossiers.index_generator.canvas.Canvas", return_value=mock_c), patch(
            "apps.metadata.agid_metadata.get_agid_metadata_for_dossier", return_value=meta
        ):
            generate_dossier_index_pdf(d)
        assert mock_c.showPage.call_count >= 1

    def test_generate_agid_metadata_exception_branch(self):
        tenant = _default_tenant()
        d = Dossier.objects.create(
            tenant=tenant,
            title="T",
            identifier=f"IDX-{uuid.uuid4().hex[:10]}",
        )
        mock_c = MagicMock()
        with patch("apps.dossiers.index_generator.canvas.Canvas", return_value=mock_c), patch(
            "apps.metadata.agid_metadata.get_agid_metadata_for_dossier",
            side_effect=RuntimeError("meta"),
        ):
            generate_dossier_index_pdf(d)
        joined = str(mock_c.drawString.call_args_list)
        assert "Metadati non disponibili" in joined

    def test_generate_many_documents_triggers_show_page(self):
        tenant = _default_tenant()
        d = Dossier.objects.create(
            tenant=tenant,
            title="Bulk",
            identifier=f"IDX-{uuid.uuid4().hex[:10]}",
        )
        docs = [
            Document(tenant=tenant, title=f"Documento numero {i}", folder=None) for i in range(55)
        ]
        Document.objects.bulk_create(docs)
        links = [DossierDocument(dossier=d, document=doc) for doc in docs]
        DossierDocument.objects.bulk_create(links)
        mock_c = MagicMock()
        with patch("apps.dossiers.index_generator.canvas.Canvas", return_value=mock_c), patch(
            "apps.metadata.agid_metadata.get_agid_metadata_for_dossier", return_value={}
        ):
            generate_dossier_index_pdf(d)
        assert mock_c.showPage.call_count >= 1

    def test_generate_many_folders_and_emails_paginate(self):
        tenant = _default_tenant()
        d = Dossier.objects.create(
            tenant=tenant,
            title="Pag",
            identifier=f"IDX-{uuid.uuid4().hex[:10]}",
        )
        folders = [Folder(tenant=tenant, name=f"Cartella numero {i}") for i in range(50)]
        Folder.objects.bulk_create(folders)
        DossierFolder.objects.bulk_create(
            [DossierFolder(dossier=d, folder=f) for f in folders]
        )
        emails = [
            DossierEmail(
                dossier=d,
                email_type="email",
                from_address="mail@test.it",
                subject=f"Oggetto {i}",
                received_at=dj_tz.now(),
            )
            for i in range(50)
        ]
        DossierEmail.objects.bulk_create(emails)
        mock_c = MagicMock()
        with patch("apps.dossiers.index_generator.canvas.Canvas", return_value=mock_c), patch(
            "apps.metadata.agid_metadata.get_agid_metadata_for_dossier", return_value={}
        ):
            generate_dossier_index_pdf(d)
        assert mock_c.showPage.call_count >= 2
