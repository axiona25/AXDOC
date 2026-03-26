"""Test estesi FolderViewSet (FASE 33D)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Fld OU", code="FLD", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="fld-ext-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="F",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(
        email="fld-ext-op@test.com",
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
def operator_client(operator_user):
    c = APIClient()
    c.force_authenticate(user=operator_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="Fld Ext", tenant=tenant, created_by=admin_user)


@pytest.fixture
def document(db, tenant, admin_user, folder):
    return Document.objects.create(
        title="In folder",
        tenant=tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
    )


@pytest.mark.django_db
class TestFolderViewsExtended:
    def test_rename_folder(self, admin_client, folder):
        r = admin_client.patch(
            f"/api/folders/{folder.id}/",
            {"name": "Renamed Ext"},
            format="json",
        )
        assert r.status_code == 200
        folder.refresh_from_db()
        assert folder.name == "Renamed Ext"

    def test_move_folder(self, admin_client, folder, admin_user, tenant):
        parent = Folder.objects.create(name="Parent Ext", tenant=tenant, created_by=admin_user)
        r = admin_client.patch(
            f"/api/folders/{folder.id}/",
            {"name": folder.name, "parent_id": str(parent.id)},
            format="json",
        )
        assert r.status_code == 200
        folder.refresh_from_db()
        assert folder.parent_id == parent.id

    def test_folder_tree_all_param(self, admin_client, folder):
        r = admin_client.get("/api/folders/", {"all": "true"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_delete_folder_with_contents(self, admin_client, folder, document):
        r = admin_client.delete(f"/api/folders/{folder.id}/")
        assert r.status_code == 400

    def test_folder_permissions_operator_lists(self, operator_client, operator_user, tenant):
        Folder.objects.create(name="Op Folder", tenant=tenant, created_by=operator_user)
        r = operator_client.get("/api/folders/")
        assert r.status_code == 200

    def test_breadcrumb(self, admin_client, admin_user, tenant):
        root = Folder.objects.create(name="Root Br", tenant=tenant, created_by=admin_user)
        child = Folder.objects.create(name="Child Br", parent=root, tenant=tenant, created_by=admin_user)
        r = admin_client.get(f"/api/folders/{child.id}/breadcrumb/")
        assert r.status_code == 200
        names = [x["name"] for x in r.json()]
        assert names == ["Root Br"]

    def test_metadata_patch_empty_structure(self, admin_client, folder):
        r = admin_client.patch(
            f"/api/folders/{folder.id}/metadata/",
            {"metadata_structure_id": None, "metadata_values": {}},
            format="json",
        )
        assert r.status_code == 200

    def test_folder_retrieve_detail(self, admin_client, folder):
        r = admin_client.get(f"/api/folders/{folder.id}/")
        assert r.status_code == 200
        assert r.json().get("name") == folder.name

    def test_list_subfolders_by_parent_id(self, admin_client, admin_user, tenant):
        parent = Folder.objects.create(name="P Sub", tenant=tenant, created_by=admin_user)
        Folder.objects.create(name="Child1", parent=parent, tenant=tenant, created_by=admin_user)
        r = admin_client.get("/api/folders/", {"parent_id": str(parent.id)})
        assert r.status_code == 200
        names = [x["name"] for x in r.json()]
        assert "Child1" in names

    def test_metadata_invalid_structure_id(self, admin_client, folder):
        import uuid

        r = admin_client.patch(
            f"/api/folders/{folder.id}/metadata/",
            {"metadata_structure_id": str(uuid.uuid4()), "metadata_values": {}},
            format="json",
        )
        assert r.status_code == 400

    def test_metadata_operator_forbidden(self, db, tenant, ou):
        op1 = User.objects.create_user(
            email="fld-op1@test.com",
            password="O123456!",
            role="OPERATOR",
            first_name="O",
            last_name="1",
        )
        op1.tenant = tenant
        op1.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=op1, organizational_unit=ou, role="OPERATOR")
        op2 = User.objects.create_user(
            email="fld-op2@test.com",
            password="O123456!",
            role="OPERATOR",
            first_name="O",
            last_name="2",
        )
        op2.tenant = tenant
        op2.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=op2, organizational_unit=ou, role="OPERATOR")
        f = Folder.objects.create(name="Shared meta", tenant=tenant, created_by=op1)
        Document.objects.create(
            title="Doc in shared folder",
            tenant=tenant,
            folder=f,
            created_by=op2,
            owner=op2,
        )
        c = APIClient()
        c.force_authenticate(user=op2)
        r = c.patch(
            f"/api/folders/{f.id}/metadata/",
            {"metadata_structure_id": None, "metadata_values": {}},
            format="json",
        )
        assert r.status_code == 403

    def test_request_signature_bulk(self, admin_client, folder, admin_user, tenant):
        from django.contrib.auth import get_user_model

        U = get_user_model()
        signer = U.objects.create_user(
            email="fld-signer@test.com",
            password="S123456!",
            role="OPERATOR",
            first_name="S",
            last_name="G",
        )
        signer.tenant = tenant
        signer.save(update_fields=["tenant"])
        doc = Document.objects.create(
            title="Approved in folder",
            tenant=tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
        )
        from apps.documents.models import DocumentVersion

        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        r = admin_client.post(
            f"/api/folders/{folder.id}/request_signature/",
            {"signer_id": str(signer.id), "format": "pades_invisible", "reason": "bulk"},
            format="json",
        )
        assert r.status_code == 201
        body = r.json()
        assert body.get("count", 0) >= 1
        assert body.get("signature_requests")

    def test_request_signature_unknown_signer(self, admin_client, folder):
        import uuid

        r = admin_client.post(
            f"/api/folders/{folder.id}/request_signature/",
            {"signer_id": str(uuid.uuid4()), "format": "pades_invisible"},
            format="json",
        )
        assert r.status_code == 400
