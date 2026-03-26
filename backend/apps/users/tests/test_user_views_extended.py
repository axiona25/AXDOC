"""Test estesi UserViewSet (FASE 33C)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

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
    return OrganizationalUnit.objects.create(name="UVX OU", code="UVX", tenant=tenant)


@pytest.fixture
def admin(db, tenant):
    u = User.objects.create_user(
        email="uvx-admin@test.com",
        password="Admin123!",
        role="ADMIN",
        user_type="internal",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    return u


@pytest.fixture
def operator(db, tenant, ou):
    u = User.objects.create_user(
        email="uvx-op@test.com",
        password="Op123456!",
        role="OPERATOR",
        user_type="internal",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def admin_client(admin):
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


@pytest.mark.django_db
class TestUserListFilters:
    def test_filter_role_and_user_type(self, admin_client, operator, admin):
        r = admin_client.get("/api/users/", {"role": "OPERATOR", "user_type": "internal"})
        assert r.status_code == 200
        data = r.json()
        rows = data.get("results", data)
        emails = {x.get("email") for x in rows}
        assert operator.email in emails

    def test_filter_ou(self, admin_client, operator, ou):
        r = admin_client.get("/api/users/", {"ou": str(ou.id)})
        assert r.status_code == 200


@pytest.mark.django_db
class TestCreateManualAndType:
    def test_create_manual_internal(self, admin_client, ou):
        r = admin_client.post(
            "/api/users/create_manual/",
            {
                "email": "manual-new@test.com",
                "first_name": "M",
                "last_name": "N",
                "user_type": "internal",
                "role": "OPERATOR",
                "organizational_unit_id": str(ou.id),
                "password": "TempPass1",
                "send_welcome_email": False,
            },
            format="json",
        )
        assert r.status_code == 201
        assert User.objects.filter(email="manual-new@test.com").exists()

    def test_change_type_to_guest(self, admin_client, operator):
        r = admin_client.post(
            f"/api/users/{operator.id}/change_type/",
            {"user_type": "guest"},
            format="json",
        )
        assert r.status_code == 200
        operator.refresh_from_db()
        assert operator.user_type == "guest"


@pytest.mark.django_db
class TestConsentsExportAnonymize:
    def test_my_consents_get_post(self, operator):
        c = APIClient()
        c.force_authenticate(user=operator)
        r = c.get("/api/users/my_consents/")
        assert r.status_code == 200
        r2 = c.post(
            "/api/users/my_consents/",
            {
                "consent_type": "privacy_policy",
                "version": "1.0",
                "granted": True,
            },
            format="json",
        )
        assert r2.status_code == 201

    def test_export_my_data(self, operator):
        c = APIClient()
        c.force_authenticate(user=operator)
        r = c.get("/api/users/export_my_data/")
        assert r.status_code == 200
        assert r["Content-Type"].startswith("application/json")

    def test_anonymize_other_user(self, admin_client, admin, tenant):
        target = User.objects.create_user(
            email="to-anon@test.com",
            password="Xyz12345!",
            role="OPERATOR",
            user_type="internal",
        )
        target.tenant = tenant
        target.save(update_fields=["tenant"])
        r = admin_client.post(f"/api/users/{target.id}/anonymize/", {}, format="json")
        assert r.status_code == 200

    def test_anonymize_self_forbidden(self, admin_client, admin):
        r = admin_client.post(f"/api/users/{admin.id}/anonymize/", {}, format="json")
        assert r.status_code == 400


@pytest.mark.django_db
class TestResetPasswordProfile:
    def test_reset_password_admin(self, admin_client, operator):
        r = admin_client.post(f"/api/users/{operator.id}/reset_password/", {}, format="json")
        assert r.status_code == 200
        assert "generated_password" in r.json()
        operator.refresh_from_db()
        assert operator.must_change_password is True

    def test_operator_patch_own_profile(self, operator):
        c = APIClient()
        c.force_authenticate(user=operator)
        r = c.patch(
            f"/api/users/{operator.id}/",
            {"first_name": "UpdatedName", "phone": "+3900000"},
            format="json",
        )
        assert r.status_code == 200
        operator.refresh_from_db()
        assert operator.first_name == "UpdatedName"
