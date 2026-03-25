"""Dashboard statistiche avanzate (FASE 25)."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder
from apps.protocols.models import Protocol
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.workflows.models import WorkflowTemplate, WorkflowInstance

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="IT", code="IT")


@pytest.fixture
def admin(db):
    u = User.objects.create_user(email="dash_adv@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def operator(db):
    return User.objects.create_user(email="op_adv@test.com", password="test", role="OPERATOR")


@pytest.mark.django_db
class TestDashboardAdvanced:
    def test_documents_trend_returns_monthly_data(self, api_client, admin):
        folder = Folder.objects.create(name="F", created_by=admin)
        Document.objects.create(title="D1", folder=folder, created_by=admin)
        api_client.force_authenticate(user=admin)
        r = api_client.get("/api/dashboard/documents_trend/", {"months": 12})
        assert r.status_code == status.HTTP_200_OK
        data = r.json()["results"]
        assert isinstance(data, list)
        assert any(x["count"] >= 1 for x in data)

    def test_protocols_trend_returns_direction_breakdown(self, api_client, admin, ou):
        Protocol.objects.create(
            organizational_unit=ou,
            year=2025,
            number=1,
            protocol_id="2025/IT/9001",
            direction="in",
            subject="A",
            status="active",
        )
        Protocol.objects.create(
            organizational_unit=ou,
            year=2025,
            number=2,
            protocol_id="2025/IT/9002",
            direction="out",
            subject="B",
            status="active",
        )
        api_client.force_authenticate(user=admin)
        r = api_client.get("/api/dashboard/protocols_trend/", {"months": 12})
        assert r.status_code == 200
        rows = r.json()["results"]
        directions = {x["direction"] for x in rows}
        assert "IN" in directions or "OUT" in directions

    def test_protocols_trend_operator_scoped_to_ou(self, api_client, operator, ou):
        Protocol.objects.create(
            organizational_unit=ou,
            year=2025,
            number=3,
            protocol_id="2025/IT/9003",
            direction="in",
            subject="Op",
            status="active",
        )
        OrganizationalUnitMembership.objects.create(user=operator, organizational_unit=ou, role="OPERATOR")
        api_client.force_authenticate(user=operator)
        r = api_client.get("/api/dashboard/protocols_trend/", {"months": 12})
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_workflow_stats_admin_ok(self, api_client, admin):
        folder = Folder.objects.create(name="WF", created_by=admin)
        doc = Document.objects.create(title="W", folder=folder, created_by=admin)
        tpl = WorkflowTemplate.objects.create(name="T", created_by=admin, is_published=True)
        WorkflowInstance.objects.create(template=tpl, document=doc, status="active")
        api_client.force_authenticate(user=admin)
        r = api_client.get("/api/dashboard/workflow_stats/")
        assert r.status_code == 200
        body = r.json()
        assert "active" in body
        assert body["active"] >= 1

    def test_workflow_stats_operator_forbidden(self, api_client, operator):
        api_client.force_authenticate(user=operator)
        r = api_client.get("/api/dashboard/workflow_stats/")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_storage_trend_returns_results(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        r = api_client.get("/api/dashboard/storage_trend/", {"months": 6})
        assert r.status_code == 200
        assert "results" in r.json()
