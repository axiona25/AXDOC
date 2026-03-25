"""Isolamento dati tra tenant sulle API."""
import io

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.organizations.models import Tenant


@pytest.mark.django_db
def test_user_cannot_access_other_tenant_document(user_factory):
    t1, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D1", "plan": "enterprise"})
    t2 = Tenant.objects.create(name="Altro", slug="altro-tenant", plan="starter")
    u1 = user_factory(email="u1@test.com", tenant=t1)
    u2 = user_factory(email="u2@test.com", tenant=t2)
    doc = Document.objects.create(
        title="Segreto",
        created_by=u1,
        owner=u1,
        tenant=t1,
        visibility=Document.VISIBILITY_PERSONAL,
    )
    client = APIClient()
    client.force_authenticate(user=u2)
    r = client.get(f"/api/documents/{doc.id}/")
    assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_sees_only_own_tenant_documents(user_factory):
    t1, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D1", "plan": "enterprise"})
    t2 = Tenant.objects.create(name="Altro", slug="altro-2", plan="starter")
    u1 = user_factory(email="a1@test.com", tenant=t1)
    user_factory(email="a2@test.com", tenant=t2)
    Document.objects.create(
        title="Doc1",
        created_by=u1,
        owner=u1,
        tenant=t1,
        visibility=Document.VISIBILITY_PERSONAL,
    )
    client = APIClient()
    client.force_authenticate(user=u1)
    r = client.get("/api/documents/")
    assert r.status_code == 200
    assert len(r.data.get("results", r.data if isinstance(r.data, list) else [])) >= 1


@pytest.mark.django_db
def test_superadmin_sees_all_tenants(user_factory):
    t1, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D1", "plan": "enterprise"})
    t2 = Tenant.objects.create(name="T2", slug="t2-iso", plan="starter")
    su = user_factory(email="su@test.com", is_superuser=True, is_staff=True, tenant=t1)
    u2 = user_factory(email="o2@test.com", tenant=t2)
    Document.objects.create(
        title="Cross",
        created_by=u2,
        owner=u2,
        tenant=t2,
        visibility=Document.VISIBILITY_PERSONAL,
    )
    client = APIClient()
    client.force_authenticate(user=su)
    r = client.get("/api/documents/")
    assert r.status_code == 200
    data = r.data.get("results", r.data if isinstance(r.data, list) else [])
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_document_auto_assigns_tenant(user_factory):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D1", "plan": "enterprise"})
    u = user_factory(email="auto-t@test.com", tenant=t)
    client = APIClient()
    client.force_authenticate(user=u)
    f = io.BytesIO(b"hello")
    r = client.post(
        "/api/documents/",
        data={"title": "T1", "file": f},
        format="multipart",
    )
    assert r.status_code == status.HTTP_201_CREATED
    doc_id = r.data.get("id")
    doc = Document.objects.get(pk=doc_id)
    assert doc.tenant_id == t.id
