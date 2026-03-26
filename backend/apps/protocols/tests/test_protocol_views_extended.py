"""Test estesi ProtocolViewSet (FASE 33C)."""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol

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
    return OrganizationalUnit.objects.create(name="PVX OU", code="PVX", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(email="pvx-adm@test.com", password="Test123!", role="ADMIN")
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def internal_operator(db, tenant, ou):
    u = User.objects.create_user(email="pvx-op@test.com", password="Test123!", role="OPERATOR", user_type="internal")
    u.tenant = tenant
    u.save(update_fields=["tenant", "user_type"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def guest_user(db, tenant):
    u = User.objects.create_user(
        email="pvx-guest@test.com",
        password="Guest123!",
        role="OPERATOR",
        user_type="guest",
    )
    u.tenant_id = tenant.id
    u.save(update_fields=["tenant", "user_type"])
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def operator_client(internal_operator):
    c = APIClient()
    c.force_authenticate(user=internal_operator)
    return c


@pytest.fixture
def protocol(db, tenant, admin_user, ou):
    now = timezone.now()
    return Protocol.objects.create(
        tenant=tenant,
        protocol_id="2099/PVX/0999",
        subject="Proto ext",
        direction="in",
        status="active",
        created_by=admin_user,
        organizational_unit=ou,
        registered_by=admin_user,
        registered_at=now,
        year=2099,
        number=999,
    )


@pytest.fixture
def document_for_protocol(db, tenant, admin_user):
    folder = Folder.objects.create(name="PF", tenant=tenant, created_by=admin_user)
    return Document.objects.create(
        title="Doc proto",
        tenant=tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
        status=Document.STATUS_DRAFT,
    )


@pytest.mark.django_db
class TestProtocolGuestAndExports:
    def test_guest_forbidden_list(self, guest_user):
        c = APIClient()
        c.force_authenticate(user=guest_user)
        r = c.get("/api/protocols/")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_export_excel_pdf(self, admin_client):
        r = admin_client.get("/api/protocols/export_excel/")
        assert r.status_code == 200
        r2 = admin_client.get("/api/protocols/export_pdf/")
        assert r2.status_code == 200


@pytest.mark.django_db
class TestProtocolCRUDAndFilters:
    def test_create_in_and_out(self, operator_client, ou):
        r = operator_client.post(
            "/api/protocols/",
            {
                "subject": "Entrata test",
                "direction": "in",
                "organizational_unit": str(ou.id),
                "sender_receiver": "Mario",
            },
            format="json",
        )
        assert r.status_code == 201
        r2 = operator_client.post(
            "/api/protocols/",
            {
                "subject": "Uscita test",
                "direction": "out",
                "organizational_unit": str(ou.id),
            },
            format="json",
        )
        assert r2.status_code == 201

    def test_list_filters(self, admin_client, protocol, ou):
        r = admin_client.get(
            "/api/protocols/",
            {"direction": "in", "ou_id": str(ou.id), "year": "2099", "status": "active"},
        )
        assert r.status_code == 200

    def test_daily_register(self, admin_client, protocol):
        day = protocol.registered_at.date().isoformat()
        r = admin_client.get("/api/protocols/daily_register/", {"date": day})
        assert r.status_code == 200
        assert "protocols" in r.json()

    def test_daily_register_missing_date_400(self, admin_client):
        r = admin_client.get("/api/protocols/daily_register/")
        assert r.status_code == 400


@pytest.mark.django_db
class TestProtocolActions:
    def test_archive(self, admin_client, protocol):
        r = admin_client.post(f"/api/protocols/{protocol.id}/archive/", {}, format="json")
        assert r.status_code == 200
        protocol.refresh_from_db()
        assert protocol.status == "archived"

    def test_download_404_without_file(self, admin_client, protocol):
        r = admin_client.get(f"/api/protocols/{protocol.id}/download/")
        assert r.status_code == 404

    def test_add_attachment(self, admin_client, protocol, document_for_protocol):
        r = admin_client.post(
            f"/api/protocols/{protocol.id}/add_attachment/",
            {"document_id": str(document_for_protocol.id)},
            format="json",
        )
        assert r.status_code == 200

    def test_share_and_shares(self, admin_client, protocol, internal_operator):
        r = admin_client.post(
            f"/api/protocols/{protocol.id}/share/",
            {
                "recipient_type": "internal",
                "recipient_user_id": str(internal_operator.id),
            },
            format="json",
        )
        assert r.status_code == 201
        r2 = admin_client.get(f"/api/protocols/{protocol.id}/shares/")
        assert r2.status_code == 200

    def test_coverpage_pdf(self, admin_client, protocol):
        r = admin_client.get(f"/api/protocols/{protocol.id}/coverpage/")
        assert r.status_code == 200
        assert "pdf" in r["Content-Type"].lower()
