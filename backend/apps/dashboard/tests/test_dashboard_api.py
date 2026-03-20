"""Test API Dashboard (FASE 14)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.documents.models import Document, Folder
from apps.authentication.models import AuditLog

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user(email="admin-dash@test.com", password="test", role="ADMIN")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def operator_user(db):
    return User.objects.create_user(email="op-dash@test.com", password="test", role="OPERATOR")


@pytest.mark.django_db
class TestDashboardStats:
    def test_stats_admin_includes_admin_fields(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        r = api_client.get("/api/dashboard/stats/")
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert "total_users" in data
        assert "total_documents" in data
        assert "total_dossiers" in data
        assert "total_protocols" in data
        assert "documents_by_status" in data
        assert "active_workflows" in data
        assert "storage_used_mb" in data

    def test_stats_operator_no_admin_fields(self, api_client, operator_user):
        api_client.force_authenticate(user=operator_user)
        r = api_client.get("/api/dashboard/stats/")
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert "my_documents" in data
        assert "my_pending_steps" in data
        assert "recent_activity" in data
        assert "total_users" not in data

    def test_recent_documents_only_accessible(self, api_client, operator_user):
        folder = Folder.objects.create(name="F")
        doc = Document.objects.create(title="Doc1", folder=folder, created_by=operator_user)
        api_client.force_authenticate(user=operator_user)
        r = api_client.get("/api/dashboard/recent_documents/")
        assert r.status_code == 200
        results = r.json().get("results", [])
        assert len(results) >= 1
        assert any(d["title"] == "Doc1" for d in results)
