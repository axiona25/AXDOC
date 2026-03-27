"""Test TenantMiddleware e thread-local."""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory

from apps.organizations.middleware import (
    TenantMiddleware,
    _decode_access_tenant_id,
    get_current_tenant,
    set_current_tenant,
)
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


@pytest.mark.django_db
def test_middleware_invalid_x_tenant_id_swallows_exception():
    Tenant.objects.get_or_create(slug="default", defaults={"name": "Def", "plan": "enterprise"})
    mw = TenantMiddleware(lambda r: r)
    rf = RequestFactory()
    req = rf.get("/x/", HTTP_X_TENANT_ID="not-a-valid-uuid")
    mw.process_request(req)
    assert req.tenant is not None
    assert req.tenant.slug == "default"


@pytest.mark.django_db
def test_middleware_subdomain_slug():
    Tenant.objects.get_or_create(slug="default", defaults={"name": "Def", "plan": "enterprise"})
    t = Tenant.objects.create(name="SubCo", slug="subco", plan="starter")
    mw = TenantMiddleware(lambda r: r)
    rf = RequestFactory()
    req = rf.get("/x/")
    req.META["HTTP_HOST"] = "subco.example.com"
    req.get_host = lambda: "subco.example.com"
    mw.process_request(req)
    assert req.tenant.id == t.id


def test_decode_access_tenant_id_no_bearer():
    rf = RequestFactory()
    assert _decode_access_tenant_id(rf.get("/")) is None
    assert _decode_access_tenant_id(rf.get("/", HTTP_AUTHORIZATION="Basic x")) is None


def test_decode_access_tenant_id_bad_token():
    rf = RequestFactory()
    assert _decode_access_tenant_id(rf.get("/", HTTP_AUTHORIZATION="Bearer not.jwt.here")) is None


@pytest.mark.django_db
def test_process_response_clears_thread_local():
    Tenant.objects.get_or_create(slug="default", defaults={"name": "Def", "plan": "enterprise"})
    t = Tenant.objects.create(name="R", slug=f"r-{uuid.uuid4().hex[:6]}", plan="starter")
    set_current_tenant(t)
    mw = TenantMiddleware(lambda r: r)
    rf = RequestFactory()
    req = rf.get("/")
    resp = mw.process_response(req, HttpResponse())
    assert resp.status_code == 200
    assert get_current_tenant() is None
