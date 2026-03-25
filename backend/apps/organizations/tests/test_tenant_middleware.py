"""Test TenantMiddleware e thread-local."""
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.organizations.middleware import TenantMiddleware, get_current_tenant, set_current_tenant
from apps.organizations.models import Tenant

User = get_user_model()


@pytest.mark.django_db
def test_middleware_falls_back_to_default():
    Tenant.objects.get_or_create(slug="default", defaults={"name": "Def", "plan": "enterprise"})
    mw = TenantMiddleware(lambda r: r)
    rf = RequestFactory()
    req = rf.get("/api/health/")
    mw.process_request(req)
    assert req.tenant is not None
    assert req.tenant.slug == "default"


@pytest.mark.django_db
def test_middleware_sets_tenant_from_header():
    t = Tenant.objects.create(name="Acme", slug="acme", plan="starter")
    Tenant.objects.get_or_create(slug="default", defaults={"name": "Def", "plan": "enterprise"})
    mw = TenantMiddleware(lambda r: r)
    rf = RequestFactory()
    req = rf.get("/x/", HTTP_X_TENANT_ID=str(t.id))
    mw.process_request(req)
    assert req.tenant is not None
    assert req.tenant.id == t.id


@pytest.mark.django_db
def test_middleware_sets_tenant_from_user():
    Tenant.objects.get_or_create(slug="default", defaults={"name": "Def", "plan": "enterprise"})
    t = Tenant.objects.create(name="T", slug="t-user", plan="starter")
    u = User.objects.create_user(
        email="tu@test.com", password="Test1!", first_name="A", last_name="B", tenant=t
    )
    mw = TenantMiddleware(lambda r: r)
    rf = RequestFactory()
    req = rf.get("/x/")
    req.user = u
    mw.process_request(req)
    assert req.tenant is not None
    assert req.tenant.id == t.id


@pytest.mark.django_db
def test_get_current_tenant_returns_correct_tenant():
    t = Tenant.objects.create(name="Ctx", slug="ctx", plan="starter")
    set_current_tenant(t)
    assert get_current_tenant() == t
    set_current_tenant(None)
