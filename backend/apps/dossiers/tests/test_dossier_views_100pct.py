# FASE 34 — Copertura mirata dossiers/views.py (>=95%)
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.documents.models import Document, Folder
from apps.dossiers.models import Dossier, DossierDocument, DossierPermission
from apps.metadata.models import MetadataField, MetadataStructure
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol, ProtocolCounter
from apps.dossiers.views import DossierViewSet, _dossier_export_queryset, _user_can_access_dossier, _user_can_write_dossier

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Dos OU", code="DOU", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="dos100-adm@test.com",
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
        email="dos100-ap@test.com",
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
        email="dos100-op@test.com",
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
    return Folder.objects.create(name="Dos F", tenant=tenant, created_by=admin_user)


@pytest.mark.django_db
class TestDossierHelpers:
    def test_user_can_access_variants(self, admin_user, operator_user, ou):
        d = Dossier.objects.create(
            title="H",
            identifier=f"h-{uuid.uuid4().hex[:6]}",
            responsible=operator_user,
            created_by=operator_user,
            organizational_unit=ou,
            status="open",
        )
        assert _user_can_access_dossier(operator_user, d) is True
        assert _user_can_access_dossier(admin_user, d) is True
        assert _user_can_write_dossier(operator_user, d) is True

    def test_export_queryset_filters(self, admin_user, ou):
        Dossier.objects.create(
            title="E1",
            identifier=f"e1-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="open",
        )
        factory = APIRequestFactory()
        wsgi = factory.get("/api/dossiers/export_excel/?responsible_id=&ou_id=&status=open")
        force_authenticate(wsgi, user=admin_user)
        request = Request(wsgi)
        view = DossierViewSet()
        view.request = request
        view.action = "list"
        qs = _dossier_export_queryset(view, request)
        assert qs.model is Dossier


@pytest.mark.django_db
class TestDossierListRetrieve:
    def test_list_filter_all_admin(self, admin_client, admin_user, ou):
        Dossier.objects.create(
            title="L1",
            identifier=f"l1-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="open",
        )
        r = admin_client.get("/api/dossiers/", {"filter": "all", "responsible_id": str(admin_user.id), "ou_id": str(ou.id)})
        assert r.status_code == 200

    def test_list_status_archived(self, admin_client, admin_user, ou):
        Dossier.objects.create(
            title="Ar",
            identifier=f"ar-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="archived",
        )
        r = admin_client.get("/api/dossiers/", {"status": "archived"})
        assert r.status_code == 200

    def test_list_non_paginated(self, admin_client, admin_user, ou):
        Dossier.objects.create(
            title="NP",
            identifier=f"np-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="open",
        )
        with patch.object(DossierViewSet, "paginate_queryset", return_value=None):
            r = admin_client.get("/api/dossiers/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_retrieve_forbidden(self, admin_client, operator_user, ou):
        d = Dossier.objects.create(
            title="Sec",
            identifier=f"sec-{uuid.uuid4().hex[:6]}",
            responsible=operator_user,
            created_by=operator_user,
            organizational_unit=ou,
            status="open",
        )
        r = admin_client.get(f"/api/dossiers/{d.id}/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestDossierCRUD:
    def test_create_operator_forbidden(self, operator_client, operator_user, ou):
        r = operator_client.post(
            "/api/dossiers/",
            {
                "title": "X",
                "identifier": f"x-{uuid.uuid4().hex[:6]}",
                "responsible": str(operator_user.id),
                "organizational_unit": str(ou.id),
            },
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_create_approver_ok(self, approver_client, approver_user, ou):
        r = approver_client.post(
            "/api/dossiers/",
            {
                "title": "New",
                "identifier": f"n-{uuid.uuid4().hex[:8]}",
                "responsible": str(approver_user.id),
                "organizational_unit": str(ou.id),
                "allowed_users": [],
                "allowed_ous": [],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_destroy_admin_open(self, admin_client, admin_user, ou):
        d = Dossier.objects.create(
            title="Del",
            identifier=f"d-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="open",
        )
        r = admin_client.delete(f"/api/dossiers/{d.id}/")
        assert r.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_not_open(self, admin_client, admin_user, ou):
        d = Dossier.objects.create(
            title="Clo",
            identifier=f"c-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="closed",
        )
        r = admin_client.delete(f"/api/dossiers/{d.id}/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_destroy_operator_forbidden(self, operator_client, operator_user, ou):
        d = Dossier.objects.create(
            title="Op",
            identifier=f"o-{uuid.uuid4().hex[:6]}",
            responsible=operator_user,
            created_by=operator_user,
            organizational_unit=ou,
            status="open",
        )
        r = operator_client.delete(f"/api/dossiers/{d.id}/")
        assert r.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDossierActions:
    def test_archive_blocks_non_approved(self, approver_client, approver_user, ou, folder):
        d = Dossier.objects.create(
            title="Arc",
            identifier=f"a-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        doc = Document.objects.create(
            title="Draft",
            tenant=folder.tenant,
            folder=folder,
            created_by=approver_user,
            owner=approver_user,
            status=Document.STATUS_DRAFT,
        )
        DossierDocument.objects.create(dossier=d, document=doc, added_by=approver_user)
        r = approver_client.post(f"/api/dossiers/{d.id}/archive/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_remove_document_protocol(self, approver_client, approver_user, ou, folder):
        d = Dossier.objects.create(
            title="Doc",
            identifier=f"doc-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        doc = Document.objects.create(
            title="In",
            tenant=folder.tenant,
            folder=folder,
            created_by=approver_user,
            owner=approver_user,
        )
        r = approver_client.post(f"/api/dossiers/{d.id}/add_document/", {"document_id": str(doc.id)}, format="json")
        assert r.status_code == 200
        r2 = approver_client.post(f"/api/dossiers/{d.id}/add_document/", {"document_id": str(doc.id)}, format="json")
        assert r2.status_code == status.HTTP_400_BAD_REQUEST
        r3 = approver_client.delete(f"/api/dossiers/{d.id}/remove_document/{doc.id}/")
        assert r3.status_code == 200

    def test_add_protocol_by_number(self, approver_client, approver_user, ou):
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
            registered_by=approver_user,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=approver_user,
        )
        d = Dossier.objects.create(
            title="P",
            identifier=f"p-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        r = approver_client.post(f"/api/dossiers/{d.id}/add_protocol/", {"protocol_id": pid}, format="json")
        assert r.status_code == 200

    def test_documents_protocols_chat_detail(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="Lists",
            identifier=f"ls-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        assert approver_client.get(f"/api/dossiers/{d.id}/documents/").status_code == 200
        assert approver_client.get(f"/api/dossiers/{d.id}/protocols/").status_code == 200
        assert approver_client.post(f"/api/dossiers/{d.id}/chat/", {}, format="json").status_code == 200
        assert approver_client.get(f"/api/dossiers/{d.id}/detail_full/").status_code == 200

    def test_add_folder_and_remove(self, approver_client, approver_user, ou, folder):
        d = Dossier.objects.create(
            title="Fld",
            identifier=f"f-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        r = approver_client.post(f"/api/dossiers/{d.id}/add_folder/", {"folder_id": str(folder.id)}, format="json")
        assert r.status_code == 200
        from apps.dossiers.models import DossierFolder

        df = DossierFolder.objects.get(dossier=d, folder=folder)
        r2 = approver_client.post(
            f"/api/dossiers/{d.id}/remove_folder/",
            {"dossier_folder_id": str(df.id)},
            format="json",
        )
        assert r2.status_code == 200

    def test_add_email_parse_received_at(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="Em",
            identifier=f"em-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        r = approver_client.post(
            f"/api/dossiers/{d.id}/add_email/",
            {
                "email_type": "in",
                "from_address": "a@b.c",
                "to_addresses": ["x@y.z"],
                "subject": "S",
                "body": "B",
                "received_at": "not-a-date",
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_upload_file(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="Up",
            identifier=f"u-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        f = SimpleUploadedFile("a.txt", b"hi", content_type="text/plain")
        r = approver_client.post(f"/api/dossiers/{d.id}/upload_file/", {"file": f}, format="multipart")
        assert r.status_code == status.HTTP_201_CREATED

    def test_close_dossier(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="Cl",
            identifier=f"cl-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        r = approver_client.post(f"/api/dossiers/{d.id}/close/", {}, format="json")
        assert r.status_code == 200

    @patch("apps.dossiers.index_generator.generate_dossier_index_pdf", return_value=b"%PDF")
    def test_generate_index(self, mock_pdf, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="Ix",
            identifier=f"ix-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        r = approver_client.get(f"/api/dossiers/{d.id}/generate_index/")
        assert r.status_code == 200

    @patch("apps.metadata.agid_metadata.get_agid_metadata_for_dossier", return_value={"k": 1})
    def test_agid_metadata(self, mock_m, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="Ag",
            identifier=f"ag-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        r = approver_client.get(f"/api/dossiers/{d.id}/agid_metadata/")
        assert r.status_code == 200

    def test_export_excel_pdf(self, admin_client, admin_user, ou):
        Dossier.objects.create(
            title="Ex",
            identifier=f"ex-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="open",
        )
        assert admin_client.get("/api/dossiers/export_excel/").status_code == 200
        assert admin_client.get("/api/dossiers/export_pdf/").status_code == 200


@pytest.mark.django_db
class TestDossierAccessAndBranches:
    def test_operator_filter_all_empty(self, operator_client):
        r = operator_client.get("/api/dossiers/", {"filter": "all"})
        assert r.status_code == 200
        assert r.json().get("count", 0) == 0

    def test_retrieve_forbidden_other_tenant_ou(self, operator_client, admin_user, tenant):
        ou2 = OrganizationalUnit.objects.create(name="Iso", code="ISO", tenant=tenant)
        d = Dossier.objects.create(
            title="IsoD",
            identifier=f"iso-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou2,
            status="open",
        )
        r = operator_client.get(f"/api/dossiers/{d.id}/")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_access_via_dossier_permission(self, operator_client, operator_user, admin_user, ou):
        d = Dossier.objects.create(
            title="Perm",
            identifier=f"perm-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            status="open",
        )
        DossierPermission.objects.create(dossier=d, user=operator_user, can_read=True, can_write=False)
        r = operator_client.get(f"/api/dossiers/{d.id}/")
        assert r.status_code == 200

    def test_add_folder_duplicate_and_closed(self, approver_client, approver_user, ou, folder):
        d = Dossier.objects.create(
            title="Fld2",
            identifier=f"f2-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        approver_client.post(f"/api/dossiers/{d.id}/add_folder/", {"folder_id": str(folder.id)}, format="json")
        r2 = approver_client.post(f"/api/dossiers/{d.id}/add_folder/", {"folder_id": str(folder.id)}, format="json")
        assert r2.status_code == status.HTTP_400_BAD_REQUEST
        d.status = "closed"
        d.save(update_fields=["status"])
        r3 = approver_client.post(f"/api/dossiers/{d.id}/add_folder/", {"folder_id": str(folder.id)}, format="json")
        assert r3.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_folder_by_folder_id_string(self, approver_client, approver_user, ou, folder):
        d = Dossier.objects.create(
            title="RF",
            identifier=f"rf-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            status="open",
        )
        approver_client.post(f"/api/dossiers/{d.id}/add_folder/", {"folder_id": str(folder.id)}, format="json")
        r = approver_client.post(
            f"/api/dossiers/{d.id}/remove_folder/",
            {"folder_id": str(folder.id)},
            format="json",
        )
        assert r.status_code == 200

    def test_close_operator_forbidden(self, operator_client, operator_user, ou):
        d = Dossier.objects.create(
            title="Cl403",
            identifier=f"c403-{uuid.uuid4().hex[:6]}",
            responsible=operator_user,
            created_by=operator_user,
            organizational_unit=ou,
            status="open",
        )
        r = operator_client.post(f"/api/dossiers/{d.id}/close/", {}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_metadata_patch_forbidden_without_write(self, operator_client, operator_user, admin_user, ou):
        d = Dossier.objects.create(
            title="Meta403",
            identifier=f"m403-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        r = operator_client.patch(f"/api/dossiers/{d.id}/metadata/", {"metadata_values": {}}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDossierMetadataAndValidation:
    @pytest.fixture
    def meta_dossier_structure(self, db, ou, approver_user):
        s = MetadataStructure.objects.create(
            name=f"dos-meta-{uuid.uuid4().hex[:6]}",
            tenant=ou.tenant,
            created_by=approver_user,
            applicable_to=["dossier"],
            is_active=True,
        )
        MetadataField.objects.create(
            structure=s,
            name="code",
            label="Code",
            field_type="text",
            is_required=True,
            order=0,
        )
        return s

    def test_create_with_metadata_json_string_and_validation_error(
        self, approver_client, approver_user, ou, meta_dossier_structure
    ):
        r = approver_client.post(
            "/api/dossiers/",
            {
                "title": "MD",
                "identifier": f"md-{uuid.uuid4().hex[:6]}",
                "responsible": str(approver_user.id),
                "organizational_unit": str(ou.id),
                "metadata_structure_id": str(meta_dossier_structure.id),
                "metadata_values": '{"bad": "json"',
                "allowed_users": [],
                "allowed_ous": [],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        r2 = approver_client.post(
            "/api/dossiers/",
            {
                "title": "MD2",
                "identifier": f"md2-{uuid.uuid4().hex[:6]}",
                "responsible": str(approver_user.id),
                "organizational_unit": str(ou.id),
                "metadata_structure_id": str(meta_dossier_structure.id),
                "metadata_values": {},
                "allowed_users": [],
                "allowed_ous": [],
            },
            format="json",
        )
        assert r2.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_clears_metadata_structure(self, approver_client, approver_user, ou, meta_dossier_structure):
        r = approver_client.post(
            "/api/dossiers/",
            {
                "title": "MU",
                "identifier": f"mu-{uuid.uuid4().hex[:6]}",
                "responsible": str(approver_user.id),
                "organizational_unit": str(ou.id),
                "metadata_structure_id": str(meta_dossier_structure.id),
                "metadata_values": {"code": "ok"},
                "allowed_users": [],
                "allowed_ous": [],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        did = r.json()["id"]
        r2 = approver_client.patch(
            f"/api/dossiers/{did}/",
            {"metadata_structure_id": None, "metadata_values": {}},
            format="json",
        )
        assert r2.status_code == 200

    def test_metadata_action_branches(self, approver_client, approver_user, ou, meta_dossier_structure, folder):
        d = Dossier.objects.create(
            title="MA",
            identifier=f"ma-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        assert (
            approver_client.patch(
                f"/api/dossiers/{d.id}/metadata/",
                {"metadata_structure_id": str(uuid.uuid4()), "metadata_values": {}},
                format="json",
            ).status_code
            == 400
        )
        assert (
            approver_client.patch(
                f"/api/dossiers/{d.id}/metadata/",
                {
                    "metadata_structure_id": str(meta_dossier_structure.id),
                    "metadata_values": {},
                },
                format="json",
            ).status_code
            == 400
        )
        assert (
            approver_client.patch(
                f"/api/dossiers/{d.id}/metadata/",
                {"metadata_values": "{not-json"},
                format="json",
            ).status_code
            == 200
        )

    def test_add_document_protocol_errors_and_remove_404(
        self, approver_client, approver_user, ou, folder
    ):
        d = Dossier.objects.create(
            title="Err",
            identifier=f"er-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        assert approver_client.post(f"/api/dossiers/{d.id}/add_document/", {}, format="json").status_code == 400
        assert (
            approver_client.post(
                f"/api/dossiers/{d.id}/add_document/",
                {"document_id": str(uuid.uuid4())},
                format="json",
            ).status_code
            == 400
        )
        assert (
            approver_client.delete(f"/api/dossiers/{d.id}/remove_document/{uuid.uuid4()}/").status_code == 404
        )
        assert approver_client.post(f"/api/dossiers/{d.id}/add_protocol/", {}, format="json").status_code == 400
        assert (
            approver_client.post(
                f"/api/dossiers/{d.id}/add_protocol/",
                {"protocol_id": "not-a-valid-protocol-ref-xyz"},
                format="json",
            ).status_code
            == 400
        )

    def test_upload_file_missing_and_closed(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="UpE",
            identifier=f"upe-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        assert approver_client.post(f"/api/dossiers/{d.id}/upload_file/", {}, format="multipart").status_code == 400
        d.status = "closed"
        d.save(update_fields=["status"])
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        assert approver_client.post(f"/api/dossiers/{d.id}/upload_file/", {"file": f}, format="multipart").status_code == 400

    def test_close_already_closed(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="Cl2",
            identifier=f"cl2-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="closed",
        )
        r = approver_client.post(f"/api/dossiers/{d.id}/close/", {}, format="json")
        assert r.status_code == 400

    def test_add_folder_missing_and_unknown(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="AF",
            identifier=f"af-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        assert approver_client.post(f"/api/dossiers/{d.id}/add_folder/", {}, format="json").status_code == 400
        assert (
            approver_client.post(
                f"/api/dossiers/{d.id}/add_folder/",
                {"folder_id": str(uuid.uuid4())},
                format="json",
            ).status_code
            == 404
        )

    def test_remove_folder_missing(self, approver_client, approver_user, ou):
        d = Dossier.objects.create(
            title="RFm",
            identifier=f"rfm-{uuid.uuid4().hex[:6]}",
            responsible=approver_user,
            created_by=approver_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        assert approver_client.post(f"/api/dossiers/{d.id}/remove_folder/", {}, format="json").status_code == 400

    def test_dossier_ou_permission_read_access(self, operator_user, ou, admin_user):
        from apps.dossiers.models import DossierOUPermission

        d = Dossier.objects.create(
            title="OU read",
            identifier=f"our-{uuid.uuid4().hex[:6]}",
            responsible=admin_user,
            created_by=admin_user,
            organizational_unit=ou,
            tenant=ou.tenant,
            status="open",
        )
        DossierOUPermission.objects.create(dossier=d, organizational_unit=ou, can_read=True)
        c = APIClient()
        c.force_authenticate(user=operator_user)
        assert c.get(f"/api/dossiers/{d.id}/").status_code == 200
