# FASE 34B — Copertura righe residue dossiers/views.py (≥95%)
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.documents.models import Document, Folder
from apps.dossiers.models import Dossier, DossierPermission
from apps.dossiers.views import (
    DossierViewSet,
    _dossier_export_queryset,
    _user_can_access_dossier,
    _user_can_write_dossier,
)
from apps.metadata.models import MetadataField, MetadataStructure
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol, ProtocolCounter

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Rem OU", code="RMU", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="dosrem-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="D",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def approver_user(db, tenant, ou):
    u = User.objects.create_user(
        email="dosrem-ap@test.com",
        password="Appr123!",
        role="APPROVER",
        first_name="A",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="APPROVER")
    return u


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(
        email="dosrem-op@test.com",
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
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def approver_client(approver_user):
    c = APIClient()
    c.force_authenticate(user=approver_user)
    return c


@pytest.fixture
def operator_client(operator_user):
    c = APIClient()
    c.force_authenticate(user=operator_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="Rem F", tenant=tenant, created_by=admin_user)


@pytest.mark.django_db
class TestDossierViewsRemaining:
    # Copre righe: 49, 51, 53, 58, 63, 72, 76
    def test_export_queryset_filters_and_access_helpers(self, admin_user, approver_user, ou):
        d = Dossier.objects.create(
            title="Ex",
            identifier=f"ex-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        factory = APIRequestFactory()
        wsgi = factory.get(
            f"/api/dossiers/export_excel/?responsible_id={approver_user.id}&ou_id={ou.id}&status=open"
        )
        force_authenticate(wsgi, user=admin_user)
        request = Request(wsgi)
        view = DossierViewSet()
        view.request = request
        view.action = "list"
        qs = _dossier_export_queryset(view, request)
        assert d.id in qs.values_list("id", flat=True)
        assert _user_can_access_dossier(admin_user, d) is True
        assert _user_can_access_dossier(approver_user, d) is True
        d_cb = Dossier.objects.create(
            title="CB",
            identifier=f"cb-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        assert _user_can_access_dossier(approver_user, d_cb) is True
        other = User.objects.create_user(
            email=f"oth-{uuid.uuid4().hex[:6]}@x.com",
            password="Op123456!",
            role="OPERATOR",
        )
        other.tenant = ou.tenant
        other.save(update_fields=["tenant"])
        assert _user_can_access_dossier(other, d) is False
        DossierPermission.objects.create(dossier=d, user=other, can_read=True, can_write=False)
        assert _user_can_access_dossier(other, d) is True
        from apps.dossiers.models import DossierOUPermission

        ou2 = OrganizationalUnit.objects.create(name="O2", code="O2", tenant=ou.tenant)
        d2 = Dossier.objects.create(
            title="OU2",
            identifier=f"ou2-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou2,
            tenant=ou.tenant,
            status="open",
        )
        OrganizationalUnitMembership.objects.create(user=other, organizational_unit=ou, role="OPERATOR")
        DossierOUPermission.objects.create(dossier=d2, organizational_unit=ou, can_read=True)
        assert _user_can_access_dossier(other, d2) is True

    # Copre righe: 108 (utente non autenticato → queryset vuoto)
    def test_get_queryset_anonymous_empty(self, db):
        factory = APIRequestFactory()
        wsgi = factory.get("/api/dossiers/")
        wsgi.user = AnonymousUser()
        view = DossierViewSet()
        view.request = wsgi
        view.format_kwarg = None
        assert view.get_queryset().count() == 0

    # Copre righe: 221
    def test_retrieve_404_unknown_pk(self, admin_client):
        r = admin_client.get(f"/api/dossiers/{uuid.uuid4()}/")
        assert r.status_code == status.HTTP_404_NOT_FOUND

    # Copre righe: 276, 280 (create: allowed_users / allowed_ous)
    def test_create_populates_allowed_users_and_ous(self, approver_client, approver_user, operator_user, ou):
        ou2 = OrganizationalUnit.objects.create(name="OUx", code="OX", tenant=ou.tenant)
        r = approver_client.post(
            "/api/dossiers/",
            {
                "title": "Alw",
                "identifier": f"alw-{uuid.uuid4().hex[:6]}",
                "responsible": str(approver_user.id),
                "organizational_unit": str(ou.id),
                "allowed_users": [str(operator_user.id)],
                "allowed_ous": [str(ou2.id)],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    # Copre righe: 291, 297, 301-305, 307-322, 325-327, 331-333
    def test_update_metadata_string_parse_and_allowed_lists(self, approver_client, approver_user, ou):
        ms = MetadataStructure.objects.create(
            name=f"ds-{uuid.uuid4().hex[:6]}",
            tenant=ou.tenant,
            created_by=approver_user,
            applicable_to=["dossier"],
            is_active=True,
        )
        MetadataField.objects.create(
            structure=ms, name="code", label="C", field_type="text", is_required=False, order=0
        )
        r = approver_client.post(
            "/api/dossiers/",
            {
                "title": "Upd",
                "identifier": f"upd-{uuid.uuid4().hex[:6]}",
                "responsible": str(approver_user.id),
                "organizational_unit": str(ou.id),
                "allowed_users": [],
                "allowed_ous": [],
            },
            format="json",
        )
        did = r.json()["id"]
        r2 = approver_client.patch(
            f"/api/dossiers/{did}/",
            {
                "metadata_structure_id": str(ms.id),
                "metadata_values": '{"code": "x"}',
                "allowed_users": [str(approver_user.id)],
                "allowed_ous": [str(ou.id)],
            },
            format="json",
        )
        assert r2.status_code == status.HTTP_200_OK

    # Copre righe: 396 (archive senza permesso di scrittura)
    def test_archive_write_forbidden(self, admin_client, admin_user, approver_user, ou):
        d = Dossier.objects.create(
            title="Arc",
            identifier=f"arc-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        with patch("apps.dossiers.views._user_can_write_dossier", return_value=False):
            r = admin_client.post(f"/api/dossiers/{d.id}/archive/", {}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    # Copre righe: 417, 437, 447, 476, 546, 565, 594, 624
    def test_actions_write_forbidden_via_patch(self, admin_client, admin_user, approver_user, ou, folder):
        d = Dossier.objects.create(
            title="Wf",
            identifier=f"wf-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        doc = Document.objects.create(
            title="D",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        p = _make_protocol(ou, admin_user)
        with patch("apps.dossiers.views._user_can_write_dossier", return_value=False):
            assert admin_client.post(f"/api/dossiers/{d.id}/add_document/", {"document_id": str(doc.id)}).status_code == 403
            assert admin_client.delete(f"/api/dossiers/{d.id}/remove_document/{doc.id}/").status_code == 403
            assert admin_client.post(f"/api/dossiers/{d.id}/add_protocol/", {"protocol_id": str(p.id)}).status_code == 403
            assert admin_client.delete(f"/api/dossiers/{d.id}/remove_protocol/{p.id}/").status_code == 403
            assert admin_client.post(f"/api/dossiers/{d.id}/add_folder/", {"folder_id": str(folder.id)}).status_code == 403
            assert (
                admin_client.post(
                    f"/api/dossiers/{d.id}/add_email/",
                    {"subject": "s", "body": "b"},
                    format="json",
                ).status_code
                == 403
            )
            f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
            assert admin_client.post(f"/api/dossiers/{d.id}/upload_file/", {"file": f}, format="multipart").status_code == 403
            assert admin_client.post(f"/api/dossiers/{d.id}/close/", {}, format="json").status_code == 403

    # Copre righe: 486, 495, 506, 515, 638, 656
    def test_read_actions_access_forbidden(self, admin_client, admin_user, approver_user, ou):
        d = Dossier.objects.create(
            title="Rd",
            identifier=f"rd-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        with patch("apps.dossiers.views._user_can_access_dossier", return_value=False):
            assert admin_client.get(f"/api/dossiers/{d.id}/documents/").status_code == 403
            assert admin_client.post(f"/api/dossiers/{d.id}/chat/", {}, format="json").status_code == 403
            assert admin_client.get(f"/api/dossiers/{d.id}/protocols/").status_code == 403
            assert admin_client.get(f"/api/dossiers/{d.id}/detail_full/").status_code == 403
            assert admin_client.get(f"/api/dossiers/{d.id}/generate_index/").status_code == 403
            assert admin_client.get(f"/api/dossiers/{d.id}/agid_metadata/").status_code == 403

    # Copre righe: 557 (remove_folder → 404)
    def test_remove_folder_not_found(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="RF",
            identifier=f"rf-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        r = approver_client.post(
            f"/api/dossiers/{d.id}/remove_folder/",
            {"dossier_folder_id": str(uuid.uuid4())},
            format="json",
        )
        assert r.status_code == status.HTTP_404_NOT_FOUND

    # Copre righe: 567 (add_email fascicolo non aperto)
    def test_add_email_closed_dossier(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="EmC",
            identifier=f"emc-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="closed",
        )
        r = approver_client.post(
            f"/api/dossiers/{d.id}/add_email/",
            {"subject": "s", "body": "b"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    # Copre righe: 553-554 (remove_folder: TypeError → filter per folder_id)
    def test_remove_folder_typeref_fallback(self, approver_client, approver_user, ou, folder):
        d = Dossier.objects.create(
            title="RFF",
            identifier=f"rff-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        approver_client.post(f"/api/dossiers/{d.id}/add_folder/", {"folder_id": str(folder.id)}, format="json")
        # pk del DossierFolder ≠ UUID cartella: ValueError → ramo folder_id (righe 553-554)
        r = approver_client.post(
            f"/api/dossiers/{d.id}/remove_folder/",
            {"dossier_folder_id": str(folder.id)},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK


def _make_protocol(ou, user):
    y = timezone.now().year
    n = ProtocolCounter.get_next_number(ou, y)
    pid = f"{y}/{ou.code}/{n:04d}"
    now = timezone.now()
    return Protocol.objects.create(
        number=n,
        year=y,
        organizational_unit=ou,
        protocol_id=pid,
        direction="in",
        subject="S",
        sender_receiver="SR",
        registered_at=now,
        registered_by=user,
        status="active",
        protocol_number=pid,
        protocol_date=now,
        created_by=user,
    )
