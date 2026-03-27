# FASE 34 — Copertura mirata protocols/views.py (>=95%)
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.documents.models import Document, DocumentVersion, Folder
from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.agid_converter import ConversionError
from apps.protocols.models import Protocol, ProtocolCounter
from apps.protocols.views import (
    ProtocolViewSet,
    _normalize_protocol_direction_param,
    _protocol_export_queryset,
    _user_ou_ids,
)

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default Org", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Prot OU", code="POU", tenant=tenant)


@pytest.fixture
def ou2(db, tenant):
    return OrganizationalUnit.objects.create(name="Prot OU2", code="P2", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="prot100-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(
        email="prot100-op@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="O",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def operator_no_ou(db, tenant):
    u = User.objects.create_user(
        email="prot100-nou@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="N",
        last_name="O",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def operator_client(operator_user):
    c = APIClient()
    c.force_authenticate(user=operator_user)
    return c


@pytest.fixture
def no_ou_client(operator_no_ou):
    c = APIClient()
    c.force_authenticate(user=operator_no_ou)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="Prot F", tenant=tenant, created_by=admin_user)


@pytest.fixture
def document(db, tenant, admin_user, folder):
    return Document.objects.create(
        title="Prot Doc",
        tenant=tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
        status=Document.STATUS_DRAFT,
    )


def _make_protocol(ou, admin_user, **kwargs):
    year = timezone.now().year
    n = ProtocolCounter.get_next_number(ou, year)
    pid = f"{year}/{ou.code}/{n:04d}"
    defaults = dict(
        number=n,
        year=year,
        organizational_unit=ou,
        protocol_id=pid,
        direction="in",
        subject="Soggetto test",
        sender_receiver="X",
        registered_at=timezone.now(),
        registered_by=admin_user,
        status="active",
        protocol_number=pid,
        protocol_date=timezone.now(),
        created_by=admin_user,
    )
    defaults.update(kwargs)
    return Protocol.objects.create(**defaults)


@pytest.mark.django_db
class TestProtocolHelpers:
    def test_normalize_direction_variants(self):
        assert _normalize_protocol_direction_param("IN") == "in"
        assert _normalize_protocol_direction_param("OUT") == "out"
        assert _normalize_protocol_direction_param("  in ") == "in"
        assert _normalize_protocol_direction_param("") is None
        assert _normalize_protocol_direction_param("bogus") is None
        assert _normalize_protocol_direction_param("inbound") is None

    def test_user_ou_ids(self, operator_user, ou):
        assert ou.id in _user_ou_ids(operator_user)


@pytest.mark.django_db
class TestProtocolListAndExport:
    def test_list_mine_empty_ou(self, no_ou_client):
        r = no_ou_client.get("/api/protocols/", {"filter": "mine"})
        assert r.status_code == 200
        assert r.json().get("count", 0) == 0 or len(r.json().get("results", [])) == 0

    def test_list_direction_year_search_dates(self, admin_client, admin_user, ou):
        _make_protocol(ou, admin_user, direction="out", subject="Alpha unique")
        r = admin_client.get(
            "/api/protocols/",
            {
                "direction": "OUT",
                "year": str(timezone.now().year),
                "search": "Alpha",
                "date_from": (timezone.now().date() - timedelta(days=1)).isoformat(),
                "date_to": (timezone.now().date() + timedelta(days=1)).isoformat(),
            },
        )
        assert r.status_code == 200

    def test_list_invalid_year_ignored(self, admin_client):
        r = admin_client.get("/api/protocols/", {"year": "notint"})
        assert r.status_code == 200

    def test_export_queryset_branches(self, admin_user, ou):
        _make_protocol(ou, admin_user)
        factory = APIRequestFactory()
        wsgi = factory.get(
            "/api/protocols/export_excel/?filter=mine&direction=IN&status=active&search=x&date_from=2020-01-01&date_to=2030-01-01"
        )
        force_authenticate(wsgi, user=admin_user)
        request = Request(wsgi)
        view = ProtocolViewSet()
        view.request = request
        view.action = "list"
        qs = _protocol_export_queryset(view, request)
        assert qs.model is Protocol

    def test_export_queryset_ou_id_and_bad_year(self, admin_user, ou):
        _make_protocol(ou, admin_user)
        factory = APIRequestFactory()
        wsgi = factory.get(f"/api/protocols/export_excel/?ou_id={ou.id}&year=not-a-number")
        force_authenticate(wsgi, user=admin_user)
        request = Request(wsgi)
        view = ProtocolViewSet()
        view.request = request
        view.action = "list"
        qs = _protocol_export_queryset(view, request)
        assert qs.model is Protocol

    def test_list_non_paginated(self, admin_client, admin_user, ou):
        _make_protocol(ou, admin_user)
        with patch.object(ProtocolViewSet, "paginate_queryset", return_value=None):
            r = admin_client.get("/api/protocols/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_export_excel_and_pdf(self, admin_client, admin_user, ou):
        _make_protocol(ou, admin_user)
        r1 = admin_client.get("/api/protocols/export_excel/")
        assert r1.status_code == 200
        r2 = admin_client.get("/api/protocols/export_pdf/", {"direction": "in"})
        assert r2.status_code == 200


@pytest.mark.django_db
class TestDailyRegister:
    def test_daily_register_missing_date(self, admin_client):
        r = admin_client.get("/api/protocols/daily_register/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_daily_register_bad_date(self, admin_client):
        r = admin_client.get("/api/protocols/daily_register/", {"date": "not-a-date"})
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_daily_register_ok(self, admin_client, admin_user, ou):
        day = timezone.now().date().isoformat()
        p = _make_protocol(ou, admin_user)
        p.registered_at = timezone.now()
        p.save(update_fields=["registered_at"])
        r = admin_client.get("/api/protocols/daily_register/", {"date": day, "ou_id": str(ou.id)})
        assert r.status_code == 200
        assert "protocols" in r.json()


@pytest.mark.django_db
class TestProtocolCreateUpdateDestroy:
    def test_create_forbidden_wrong_ou(self, operator_client, ou2):
        r = operator_client.post(
            "/api/protocols/",
            {
                "direction": "in",
                "organizational_unit": str(ou2.id),
                "subject": "X",
                "sender_receiver": "Y",
            },
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_create_with_attachments_and_dossier(self, operator_client, operator_user, ou, document, folder):
        d2 = Document.objects.create(
            title="Att",
            tenant=document.tenant,
            folder=folder,
            created_by=operator_user,
            owner=operator_user,
            status=Document.STATUS_DRAFT,
        )
        dos = Dossier.objects.create(
            title="Doss",
            identifier=f"id-{uuid.uuid4().hex[:8]}",
            responsible=operator_user,
            created_by=operator_user,
            organizational_unit=ou,
            status="open",
        )
        r = operator_client.post(
            "/api/protocols/",
            {
                "direction": "in",
                "organizational_unit": str(ou.id),
                "subject": "With att",
                "sender_receiver": "Z",
                "attachment_ids": [str(d2.id)],
                "dossier_ids": [str(dos.id)],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_create_skips_main_doc_in_attachment_ids(self, operator_client, operator_user, ou, document, folder):
        d2 = Document.objects.create(
            title="Att2",
            tenant=document.tenant,
            folder=folder,
            created_by=operator_user,
            owner=operator_user,
            status=Document.STATUS_DRAFT,
        )
        r = operator_client.post(
            "/api/protocols/",
            {
                "direction": "in",
                "organizational_unit": str(ou.id),
                "subject": "Main + att",
                "sender_receiver": "Z",
                "document": str(document.id),
                "attachment_ids": [str(document.id), str(d2.id)],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_create_document_already_protocolled(self, admin_client, admin_user, ou, document):
        Document.objects.filter(pk=document.pk).update(is_protocolled=True)
        r = admin_client.post(
            "/api/protocols/",
            {
                "direction": "in",
                "organizational_unit": str(ou.id),
                "subject": "Dup",
                "sender_receiver": "A",
                "document": str(document.id),
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_file_upload(self, admin_client, admin_user, ou):
        f = SimpleUploadedFile("up.pdf", b"%PDF-1.4 x", content_type="application/pdf")
        r = admin_client.post(
            "/api/protocols/",
            {
                "direction": "in",
                "organizational_unit": str(ou.id),
                "subject": "File up",
                "sender_receiver": "B",
                "file_upload": f,
            },
            format="multipart",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_update_partial(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)
        r = admin_client.patch(
            f"/api/protocols/{p.id}/",
            {"subject": "Nuovo", "sender_receiver": "SR", "notes": "n"},
            format="json",
        )
        assert r.status_code == 200

    def test_destroy_not_allowed(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)
        r = admin_client.delete(f"/api/protocols/{p.id}/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestProtocolActions:
    def test_archive(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)
        r = admin_client.post(f"/api/protocols/{p.id}/archive/")
        assert r.status_code == 200
        p.refresh_from_db()
        assert p.status == "archived"

    def test_download_open_fails_404(self, admin_client, admin_user, ou, folder, monkeypatch):
        from django.db.models.fields.files import FieldFile

        doc = Document.objects.create(
            title="DL",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="openfail.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("openfail.pdf", SimpleUploadedFile("openfail.pdf", b"%PDF-1.4", content_type="application/pdf"), save=True)
        p = _make_protocol(ou, admin_user, document=doc)
        real_open = FieldFile.open

        def _open(self, mode="rb"):
            if "openfail" in (getattr(self, "name", "") or ""):
                raise OSError("x")
            return real_open(self, mode)

        monkeypatch.setattr(FieldFile, "open", _open)
        r = admin_client.get(f"/api/protocols/{p.id}/download/")
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_download_with_file(self, admin_client, admin_user, ou, folder):
        doc = Document.objects.create(
            title="DL",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF-1.4", content_type="application/pdf"), save=True)
        p = _make_protocol(ou, admin_user, document=doc)
        r = admin_client.get(f"/api/protocols/{p.id}/download/")
        assert r.status_code == 200

    def test_download_404(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user, document=None)
        r = admin_client.get(f"/api/protocols/{p.id}/download/")
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_add_attachment_missing_id(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)
        r = admin_client.post(f"/api/protocols/{p.id}/add_attachment/", {}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_attachment_doc_not_found(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)
        r = admin_client.post(
            f"/api/protocols/{p.id}/add_attachment/",
            {"document_id": str(uuid.uuid4())},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_attachment_flow(self, admin_client, admin_user, ou, folder):
        p = _make_protocol(ou, admin_user)
        doc = Document.objects.create(
            title="Att2",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        r = admin_client.post(f"/api/protocols/{p.id}/add_attachment/", {"document_id": str(doc.id)}, format="json")
        assert r.status_code == 200
        r2 = admin_client.post(f"/api/protocols/{p.id}/add_attachment/", {"document_id": str(doc.id)}, format="json")
        assert r2.status_code == status.HTTP_400_BAD_REQUEST

    def test_share_internal_bad_user(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)
        r = admin_client.post(
            f"/api/protocols/{p.id}/share/",
            {"recipient_type": "internal", "recipient_user_id": str(uuid.uuid4())},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_shares_list(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)
        r = admin_client.get(f"/api/protocols/{p.id}/shares/")
        assert r.status_code == 200

    @patch("apps.protocols.views.AGIDConverter.generate_protocol_coverpage")
    @patch("apps.protocols.views.os.path.isfile", return_value=False)
    def test_stamped_document_no_valid_disk_path(self, mock_isfile, mock_cov, admin_client, admin_user, ou, folder):
        doc = Document.objects.create(
            title="St0",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("x.pdf", SimpleUploadedFile("x.pdf", b"%PDF-1.4", content_type="application/pdf"), save=True)
        p = _make_protocol(ou, admin_user, document=doc)

        def _gen(prot, outp):
            with open(outp, "wb") as f:
                f.write(b"%PDF")

        mock_cov.side_effect = _gen
        r = admin_client.get(f"/api/protocols/{p.id}/stamped_document/")
        assert r.status_code == 200

    @patch("apps.protocols.views.os.path.isfile", return_value=True)
    @patch("apps.protocols.views.AGIDConverter.apply_protocol_stamp")
    def test_stamped_document_with_input(self, mock_stamp, mock_isfile, admin_client, admin_user, ou, folder):
        doc = Document.objects.create(
            title="St",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("x.pdf", SimpleUploadedFile("x.pdf", b"%PDF-1.4", content_type="application/pdf"), save=True)
        p = _make_protocol(ou, admin_user, document=doc)

        def _apply(inp, prot, outp):
            with open(outp, "wb") as f:
                f.write(b"%PDF")

        mock_stamp.side_effect = _apply
        r = admin_client.get(f"/api/protocols/{p.id}/stamped_document/")
        assert r.status_code == 200

    def test_stamped_document_cover_only(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user, document=None)

        def _gen(prot, outp):
            with open(outp, "wb") as f:
                f.write(b"%PDF")

        with patch("apps.protocols.views.AGIDConverter.generate_protocol_coverpage", side_effect=_gen):
            r = admin_client.get(f"/api/protocols/{p.id}/stamped_document/")
        assert r.status_code == 200

    @patch("apps.protocols.views.os.path.isfile", return_value=True)
    @patch("apps.protocols.views.AGIDConverter.apply_protocol_stamp", side_effect=ConversionError("bad"))
    def test_stamped_document_conversion_error(self, mock_isfile, mock_apply, admin_client, admin_user, ou, folder):
        doc = Document.objects.create(
            title="E1",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("x.pdf", SimpleUploadedFile("x.pdf", b"%PDF-1.4", content_type="application/pdf"), save=True)
        p = _make_protocol(ou, admin_user, document=doc)
        r = admin_client.get(f"/api/protocols/{p.id}/stamped_document/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_coverpage(self, admin_client, admin_user, ou):
        p = _make_protocol(ou, admin_user)

        def _gen(prot, outp):
            with open(outp, "wb") as f:
                f.write(b"%PDF")

        with patch("apps.protocols.views.AGIDConverter.generate_protocol_coverpage", side_effect=_gen):
            r = admin_client.get(f"/api/protocols/{p.id}/coverpage/")
        assert r.status_code == 200
