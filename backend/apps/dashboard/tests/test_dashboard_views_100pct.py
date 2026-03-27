"""Rami dashboard: trend filtrati, workflow, storage, stats per ruolo."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentVersion, Folder
from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol
from apps.workflows.models import WorkflowInstance, WorkflowStep, WorkflowStepInstance, WorkflowTemplate

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
    return OrganizationalUnit.objects.create(name="DB100", code=f"D{uuid.uuid4().hex[:5]}", tenant=tenant)


@pytest.mark.django_db
class TestDashboardViewsCoverage:
    def test_protocols_trend_empty_when_operator_has_no_ou(self, db, tenant):
        u = User.objects.create_user(
            email=f"noprot-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="OPERATOR",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        c = APIClient()
        c.force_authenticate(user=u)
        r = c.get("/api/dashboard/protocols_trend/")
        assert r.status_code == 200
        assert r.json().get("results") == []

    def test_documents_and_storage_trend_filtered_for_operator(self, db, tenant, ou):
        u = User.objects.create_user(
            email=f"optr-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="OPERATOR",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
        folder = Folder.objects.create(name="DF", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="Mine", tenant=tenant, folder=folder, created_by=u, owner=u)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.bin",
            file_size=1024,
            created_by=u,
            is_current=True,
        )
        c = APIClient()
        c.force_authenticate(user=u)
        assert c.get("/api/dashboard/documents_trend/").status_code == 200
        assert c.get("/api/dashboard/storage_trend/").status_code == 200

    def test_workflow_stats_forbidden_for_operator(self, db, tenant, ou):
        u = User.objects.create_user(
            email=f"wff-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="OPERATOR",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
        c = APIClient()
        c.force_authenticate(user=u)
        r = c.get("/api/dashboard/workflow_stats/")
        assert r.status_code == 403

    def test_workflow_stats_avg_completion_hours(self, db, tenant, ou):
        admin = User.objects.create_user(
            email=f"wfad-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        folder = Folder.objects.create(name="WF", tenant=tenant, created_by=admin)
        doc = Document.objects.create(title="W", tenant=tenant, folder=folder, created_by=admin, owner=admin)
        tpl = WorkflowTemplate.objects.create(name="TplAvg", is_published=True)
        wi = WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=admin,
            status="completed",
            completed_at=timezone.now(),
        )
        WorkflowInstance.objects.filter(pk=wi.pk).update(
            started_at=timezone.now() - timedelta(hours=2),
        )
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get("/api/dashboard/workflow_stats/")
        assert r.status_code == 200
        body = r.json()
        assert body.get("avg_completion_hours") is not None

    def test_dashboard_stats_approver_branch(self, db, tenant, ou):
        appr = User.objects.create_user(
            email=f"appr-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="APPROVER",
        )
        appr.tenant = tenant
        appr.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=appr, organizational_unit=ou, role="APPROVER")
        folder = Folder.objects.create(name="DS", tenant=tenant, created_by=appr)
        doc = Document.objects.create(title="Doss", tenant=tenant, folder=folder, created_by=appr, owner=appr)
        Dossier.objects.create(
            title="R1",
            responsible=appr,
            created_by=appr,
            tenant=tenant,
            organizational_unit=ou,
        )
        tpl = WorkflowTemplate.objects.create(name="TplAp", is_published=True)
        step = WorkflowStep.objects.create(template=tpl, name="S1", order=1, action="approve")
        wi = WorkflowInstance.objects.create(template=tpl, document=doc, started_by=appr, status="active")
        si = WorkflowStepInstance.objects.create(
            workflow_instance=wi,
            step=step,
            status="pending",
        )
        si.assigned_to.add(appr)
        c = APIClient()
        c.force_authenticate(user=appr)
        r = c.get("/api/dashboard/stats/")
        assert r.status_code == 200
        j = r.json()
        assert "pending_approvals" in j
        assert "dossiers_responsible" in j

    def test_recent_documents_and_my_tasks(self, db, tenant, ou):
        u = User.objects.create_user(
            email=f"rd-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="OPERATOR",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
        folder = Folder.objects.create(name="RD", tenant=tenant, created_by=u)
        Document.objects.create(title="Recent", tenant=tenant, folder=folder, created_by=u, owner=u)
        c = APIClient()
        c.force_authenticate(user=u)
        assert c.get("/api/dashboard/recent_documents/").status_code == 200
        assert c.get("/api/dashboard/my_tasks/").status_code == 200

    def test_operator_protocols_trend_filters_by_ou(self, db, tenant, ou):
        u = User.objects.create_user(
            email=f"pop-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="OPERATOR",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
        Protocol.objects.create(
            tenant=tenant,
            organizational_unit=ou,
            direction="in",
            created_by=u,
        )
        c = APIClient()
        c.force_authenticate(user=u)
        r = c.get("/api/dashboard/protocols_trend/")
        assert r.status_code == 200
        assert len(r.json().get("results", [])) >= 1

    def test_protocols_trend_direction_labels(self, db, tenant, ou):
        admin = User.objects.create_user(
            email=f"pt-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        Protocol.objects.create(
            tenant=tenant,
            organizational_unit=ou,
            direction="in",
            created_by=admin,
        )
        Protocol.objects.create(
            tenant=tenant,
            organizational_unit=ou,
            direction="OUT",
            created_by=admin,
        )
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get("/api/dashboard/protocols_trend/")
        assert r.status_code == 200
        labels = {x["direction"] for x in r.json().get("results", [])}
        assert "IN" in labels and "OUT" in labels

    def test_protocols_trend_fallback_direction_em_dash(self, db, tenant, ou):
        admin = User.objects.create_user(
            email=f"unk-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        p = Protocol.objects.create(
            tenant=tenant,
            organizational_unit=ou,
            direction="in",
            created_by=admin,
        )
        Protocol.objects.filter(pk=p.pk).update(direction="")
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get("/api/dashboard/protocols_trend/")
        assert r.status_code == 200
        assert any(x.get("direction") == "—" for x in r.json().get("results", []))

    def test_dashboard_stats_admin_payload(self, db, tenant, ou):
        admin = User.objects.create_user(
            email=f"dsa-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get("/api/dashboard/stats/")
        assert r.status_code == 200
        j = r.json()
        assert "total_users" in j and "total_documents" in j
        assert "storage_used_mb" in j

    def test_my_tasks_lists_pending_steps(self, db, tenant, ou):
        u = User.objects.create_user(
            email=f"tsk-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="OPERATOR",
        )
        u.tenant = tenant
        u.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
        folder = Folder.objects.create(name="TF", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="TD", tenant=tenant, folder=folder, created_by=u, owner=u)
        tpl = WorkflowTemplate.objects.create(name="TplT", is_published=True)
        step = WorkflowStep.objects.create(template=tpl, name="St", order=1, action="review")
        wi = WorkflowInstance.objects.create(template=tpl, document=doc, started_by=u, status="active")
        si = WorkflowStepInstance.objects.create(workflow_instance=wi, step=step, status="pending")
        si.assigned_to.add(u)
        c = APIClient()
        c.force_authenticate(user=u)
        r = c.get("/api/dashboard/my_tasks/")
        assert r.status_code == 200
        assert len(r.json().get("results", [])) >= 1

    def test_protocols_trend_skips_aggregate_row_with_null_month(self, db, tenant, ou):
        """Riga difensiva: TruncMonth può teoricamente produrre month=None in edge case DB."""
        admin = User.objects.create_user(
            email=f"pnm-{uuid.uuid4().hex[:8]}@t.com",
            password="Test123!",
            role="ADMIN",
        )
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        c = APIClient()
        c.force_authenticate(user=admin)
        m = timezone.make_aware(datetime(2024, 6, 1, 0, 0, 0), timezone.get_current_timezone())
        rows = [
            {"month": None, "direction": "in", "count": 999},
            {"month": m, "direction": "in", "count": 2},
        ]
        chain = MagicMock()
        chain.annotate.return_value = chain
        chain.values.return_value = chain
        chain.order_by.return_value = rows
        with patch("apps.dashboard.views.Protocol.objects.filter", return_value=chain):
            r = c.get("/api/dashboard/protocols_trend/")
        assert r.status_code == 200
        out = r.json().get("results", [])
        assert len(out) == 1
        assert out[0]["month"] == "2024-06"
        assert out[0]["count"] == 2
        assert all(x["count"] != 999 for x in out)
