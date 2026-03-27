"""Rami TenantViewSet, OrganizationalUnitViewSet (filtri, tree, membri, export)."""
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.organizations.views import TenantViewSet

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def second_tenant(db):
    return Tenant.objects.create(name="Alt T", slug=f"alt-{uuid.uuid4().hex[:6]}", plan="starter")


@pytest.mark.django_db
class TestTenantViewsCoverage:
    def test_superuser_lists_all_active_tenants(self, db, tenant, second_tenant):
        su = User.objects.create_user(
            email=f"su-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
            is_superuser=True,
        )
        c = APIClient()
        c.force_authenticate(user=su)
        r = c.get("/api/tenants/")
        assert r.status_code == 200
        data = r.json()
        rows = data.get("results", data)
        ids = {x["id"] for x in rows}
        assert str(tenant.id) in ids
        assert str(second_tenant.id) in ids

    def test_non_superuser_sees_only_request_tenant(self, db, tenant, second_tenant):
        u = User.objects.create_user(
            email=f"tu-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        c = APIClient()
        c.force_authenticate(user=u)
        r = c.get("/api/tenants/")
        assert r.status_code == 200
        rows = r.json().get("results", r.json())
        assert len(rows) == 1
        assert rows[0]["id"] == str(tenant.id)

    def test_current_ok_with_tenant(self, db, tenant):
        u = User.objects.create_user(
            email=f"tcu-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        c = APIClient()
        c.force_authenticate(user=u)
        r = c.get("/api/tenants/current/")
        assert r.status_code == 200
        assert r.json().get("id") == str(tenant.id)

    def test_current_returns_404_without_tenant_on_request(self, db, tenant):
        u = User.objects.create_user(
            email=f"nt-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        factory = APIRequestFactory()
        request = factory.get("/api/tenants/current/")
        request.tenant = None
        force_authenticate(request, user=u)
        view = TenantViewSet.as_view(actions={"get": "current"})
        response = view(request)
        assert response.status_code == 404


@pytest.fixture
def ou_admin_setup(db, tenant):
    ou = OrganizationalUnit.objects.create(name="OU100", code=f"O{uuid.uuid4().hex[:5]}", tenant=tenant)
    admin = User.objects.create_user(
        email=f"ou-ad-{uuid.uuid4().hex[:8]}@t.com",
        password="Test123!",
        role="ADMIN",
    )
    admin.tenant = tenant
    admin.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
    c = APIClient()
    c.force_authenticate(user=admin)
    return c, admin, ou


@pytest.mark.django_db
class TestOrganizationalUnitViewsCoverage:
    def test_list_filters_mine_parent_code_name_is_active(self, ou_admin_setup):
        client, admin, ou = ou_admin_setup
        child = OrganizationalUnit.objects.create(
            name="Child U",
            code="CHILD",
            tenant=ou.tenant,
            parent=ou,
            is_active=False,
        )
        r = client.get("/api/organizations/", {"mine": "true"})
        assert r.status_code == 200
        rows = r.json().get("results", r.json())
        assert any(x["id"] == str(ou.id) for x in rows)

        r2 = client.get("/api/organizations/", {"parent": "null"})
        assert r2.status_code == 200

        r3 = client.get("/api/organizations/", {"parent": str(ou.id)})
        assert any(x["id"] == str(child.id) for x in r3.json().get("results", r3.json()))

        r4 = client.get("/api/organizations/", {"code": "CH", "name": "Child"})
        assert r4.status_code == 200

        r5 = client.get("/api/organizations/", {"is_active": "false"})
        assert any(x["id"] == str(child.id) for x in r5.json().get("results", r5.json()))

    def test_tree_and_members(self, ou_admin_setup):
        client, _, ou = ou_admin_setup
        r = client.get("/api/organizations/tree/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        r2 = client.get(f"/api/organizations/{ou.id}/members/")
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)

    def test_add_member_user_not_found(self, ou_admin_setup):
        client, _, ou = ou_admin_setup
        r = client.post(
            f"/api/organizations/{ou.id}/add_member/",
            {"user_id": str(uuid.uuid4()), "role": "OPERATOR"},
            format="json",
        )
        assert r.status_code == 404

    def test_add_member_duplicate(self, ou_admin_setup):
        client, admin, ou = ou_admin_setup
        r = client.post(
            f"/api/organizations/{ou.id}/add_member/",
            {"user_id": str(admin.id), "role": "OPERATOR"},
            format="json",
        )
        assert r.status_code == 400

    def test_remove_member_not_found(self, ou_admin_setup):
        client, _, ou = ou_admin_setup
        r = client.delete(f"/api/organizations/{ou.id}/remove_member/{uuid.uuid4()}/")
        assert r.status_code == 404

    def test_export_csv_when_buffer_none(self, ou_admin_setup):
        client, _, ou = ou_admin_setup
        with patch("apps.organizations.views.export_members_csv", return_value=None):
            r = client.get(f"/api/organizations/{ou.id}/export/")
            assert r.status_code == 404

    def test_remove_member_success(self, ou_admin_setup):
        client, admin, ou = ou_admin_setup
        other = User.objects.create_user(
            email=f"rm-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="OPERATOR",
        )
        other.tenant = ou.tenant
        other.save(update_fields=["tenant"])
        from apps.organizations.models import OrganizationalUnitMembership

        OrganizationalUnitMembership.objects.create(
            user=other,
            organizational_unit=ou,
            role="OPERATOR",
        )
        r = client.delete(f"/api/organizations/{ou.id}/remove_member/{other.id}/")
        assert r.status_code == 204
        m = OrganizationalUnitMembership.objects.get(user=other, organizational_unit=ou)
        assert m.is_active is False

    def test_destroy_ou_soft_delete(self, ou_admin_setup):
        client, _, ou = ou_admin_setup
        r = client.delete(f"/api/organizations/{ou.id}/")
        assert r.status_code in (204, 200)
        ou.refresh_from_db()
        assert ou.is_active is False
