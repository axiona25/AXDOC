"""API classificazione e OCR forzato (FASE 30)."""
import io

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.organizations.models import Tenant

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D", "plan": "enterprise"})
    return t


@pytest.fixture
def admin_client(db, tenant):
    u = User.objects.create_user(email="ai_admin@test.com", password="x", role="ADMIN", tenant=tenant)
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
def test_classify_text_endpoint(admin_client):
    r = admin_client.post(
        "/api/documents/classify_text/",
        {"text": "Fattura n. 1 con IVA e totale € 100,00 P.IVA 11223344556"},
        format="json",
    )
    assert r.status_code == status.HTTP_200_OK
    assert len(r.data.get("suggestions", [])) >= 1


@pytest.mark.django_db
def test_classify_text_empty_returns_400(admin_client):
    r = admin_client.post("/api/documents/classify_text/", {"text": "x"}, format="json")
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_classify_document_without_text_returns_400(admin_client, tenant):
    u = User.objects.get(email="ai_admin@test.com")
    d = Document.objects.create(
        title="Empty",
        created_by=u,
        owner=u,
        tenant=tenant,
        ocr_status="pending",
        extracted_text="",
    )
    r = admin_client.get(f"/api/documents/{d.id}/classify/")
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_classify_document_returns_suggestions(admin_client, tenant):
    u = User.objects.get(email="ai_admin@test.com")
    d = Document.objects.create(
        title="Fatt",
        created_by=u,
        owner=u,
        tenant=tenant,
        extracted_text="Fattura numero 99 P.IVA 12345678901 totale € 200",
        ocr_status="completed",
    )
    r = admin_client.get(f"/api/documents/{d.id}/classify/")
    assert r.status_code == status.HTTP_200_OK
    assert "suggestions" in r.data


@pytest.mark.django_db
def test_run_ocr_endpoint(admin_client, tenant):
    u = User.objects.get(email="ai_admin@test.com")
    d = Document.objects.create(
        title="OCR doc",
        created_by=u,
        owner=u,
        tenant=tenant,
    )
    from apps.documents.models import DocumentVersion

    v = DocumentVersion.objects.create(
        document=d,
        version_number=1,
        file_name="t.txt",
        file_size=3,
        file_type="text/plain",
        checksum="abc",
        created_by=u,
        is_current=True,
    )
    v.file.save("t.txt", io.BytesIO(b"hi\n"), save=True)
    r = admin_client.post(f"/api/documents/{d.id}/run_ocr/")
    assert r.status_code == status.HTTP_200_OK
    assert r.data.get("ocr_status") == "processing"


@pytest.mark.django_db
def test_ocr_status_field_on_document(tenant):
    u = User.objects.create_user(email="ocrf@test.com", password="x", tenant=tenant)
    d = Document.objects.create(
        title="T",
        created_by=u,
        owner=u,
        tenant=tenant,
        ocr_status="completed",
        ocr_confidence=88.5,
    )
    d.refresh_from_db()
    assert d.ocr_status == "completed"
    assert d.ocr_confidence == 88.5
