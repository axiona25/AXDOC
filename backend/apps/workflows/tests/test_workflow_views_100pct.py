# FASE 35.2 — Copertura workflows/views.py (branch mancanti)
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder
from apps.workflows.models import (
    WorkflowInstance,
    WorkflowStep,
    WorkflowStepInstance,
    WorkflowTemplate,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        email="wf100-admin@test.com",
        password="Admin123!",
        first_name="A",
        last_name="Admin",
        role="ADMIN",
    )


@pytest.fixture
def reviewer(db):
    return User.objects.create_user(
        email="wf100-rev@test.com",
        password="Rev123!",
        first_name="R",
        last_name="Reviewer",
        role="REVIEWER",
    )


@pytest.fixture
def approver(db):
    return User.objects.create_user(
        email="wf100-app@test.com",
        password="App123!",
        first_name="P",
        last_name="Approver",
        role="APPROVER",
    )


@pytest.fixture
def folder(db, admin):
    return Folder.objects.create(name="WF100", created_by=admin)


@pytest.fixture
def document(db, admin, folder):
    return Document.objects.create(
        title="Doc WF100",
        folder=folder,
        status=Document.STATUS_DRAFT,
        created_by=admin,
    )


@pytest.fixture
def tpl_two_step(db, admin, reviewer, approver):
    tpl = WorkflowTemplate.objects.create(
        name="Tpl Two Step",
        created_by=admin,
        is_published=True,
    )
    WorkflowStep.objects.create(
        template=tpl,
        name="Rev",
        order=1,
        action="review",
        assignee_type="role",
        assignee_role="REVIEWER",
    )
    WorkflowStep.objects.create(
        template=tpl,
        name="App",
        order=2,
        action="approve",
        assignee_type="role",
        assignee_role="APPROVER",
    )
    return tpl


@pytest.mark.django_db
class TestWorkflowInstanceCreateBranches:
    def test_missing_template_or_document_returns_400(self, api_client, admin, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        r = api_client.post("/api/workflows/instances/", {"document": str(document.id)}, format="json")
        assert r.status_code == 400
        r2 = api_client.post("/api/workflows/instances/", {"template": str(tpl_two_step.id)}, format="json")
        assert r2.status_code == 400

    def test_template_not_found_or_unpublished_404(self, api_client, admin, document):
        api_client.force_authenticate(user=admin)
        from uuid import uuid4

        r = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(uuid4())},
            format="json",
        )
        assert r.status_code == 404
        draft = WorkflowTemplate.objects.create(name="Draft", created_by=admin, is_published=False)
        WorkflowStep.objects.create(template=draft, name="S", order=1, assignee_type="role", assignee_role="ADMIN")
        r2 = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(draft.id)},
            format="json",
        )
        assert r2.status_code == 404

    def test_document_not_found_404(self, api_client, admin, tpl_two_step):
        api_client.force_authenticate(user=admin)
        from uuid import uuid4

        r = api_client.post(
            "/api/workflows/instances/",
            {"document": str(uuid4()), "template": str(tpl_two_step.id)},
            format="json",
        )
        assert r.status_code == 404

    def test_duplicate_active_workflow_400(self, api_client, admin, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        r1 = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        assert r1.status_code == 201
        r2 = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        assert r2.status_code == 400

    def test_template_without_steps_400(self, api_client, admin, document):
        api_client.force_authenticate(user=admin)
        empty = WorkflowTemplate.objects.create(name="No steps", created_by=admin, is_published=True)
        r = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(empty.id)},
            format="json",
        )
        assert r.status_code == 400


@pytest.mark.django_db
class TestWorkflowInstanceListFilters:
    def test_non_admin_filters_and_query_params(self, api_client, admin, reviewer, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        api_client.force_authenticate(user=reviewer)
        r = api_client.get(
            "/api/workflows/instances/",
            {
                "document_id": str(document.id),
                "template_id": str(tpl_two_step.id),
                "status": "active",
            },
        )
        assert r.status_code == 200
        data = r.data.get("results", r.data)
        assert len(data) >= 1


@pytest.mark.django_db
class TestWorkflowTemplateAdminActions:
    def test_destroy_blocked_with_active_instance(self, api_client, admin, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        tpl_two_step.is_published = False
        tpl_two_step.save(update_fields=["is_published"])
        r = api_client.delete(f"/api/workflows/templates/{tpl_two_step.id}/")
        assert r.status_code == 400

    def test_destroy_soft_delete_ok(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="To delete", created_by=admin, is_published=False)
        r = api_client.delete(f"/api/workflows/templates/{tpl.id}/")
        assert r.status_code == 204
        tpl.refresh_from_db()
        assert tpl.is_deleted is True

    def test_update_published_forbidden(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="Pub", created_by=admin, is_published=True)
        r = api_client.patch(f"/api/workflows/templates/{tpl.id}/", {"name": "X"}, format="json")
        assert r.status_code == 400

    def test_update_with_active_instances_forbidden(self, api_client, admin, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        tpl_two_step.is_published = False
        tpl_two_step.save(update_fields=["is_published"])
        r = api_client.patch(f"/api/workflows/templates/{tpl_two_step.id}/", {"name": "Y"}, format="json")
        assert r.status_code == 400

    def test_publish_idempotent_400(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="P", created_by=admin, is_published=True)
        r = api_client.post(f"/api/workflows/templates/{tpl.id}/publish/")
        assert r.status_code == 400

    def test_unpublish_with_active_instances_400(self, api_client, admin, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        r = api_client.post(f"/api/workflows/templates/{tpl_two_step.id}/unpublish/")
        assert r.status_code == 400

    def test_unpublish_ok(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="U", created_by=admin, is_published=True)
        r = api_client.post(f"/api/workflows/templates/{tpl.id}/unpublish/")
        assert r.status_code == 200
        tpl.refresh_from_db()
        assert tpl.is_published is False

    def test_list_mine_true(self, api_client, admin, reviewer):
        api_client.force_authenticate(user=admin)
        WorkflowTemplate.objects.create(name="Mine", created_by=admin, is_published=False)
        api_client.force_authenticate(user=reviewer)
        WorkflowTemplate.objects.create(name="Yours", created_by=reviewer, is_published=False)
        api_client.force_authenticate(user=admin)
        r = api_client.get("/api/workflows/templates/", {"mine": "true"})
        assert r.status_code == 200
        rows = r.data.get("results", r.data)
        names = {row["name"] for row in rows}
        assert "Mine" in names
        assert "Yours" not in names


@pytest.mark.django_db
class TestWorkflowStepPublishedGuards:
    def test_cannot_modify_published_template_steps(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="Locked", created_by=admin, is_published=True)
        step = WorkflowStep.objects.create(
            template=tpl,
            name="S",
            order=1,
            assignee_type="role",
            assignee_role="ADMIN",
        )
        r = api_client.post(
            f"/api/workflows/templates/{tpl.id}/steps/",
            {
                "name": "New",
                "action": "review",
                "assignee_type": "role",
                "assignee_role": "ADMIN",
            },
            format="json",
        )
        assert r.status_code == 400
        r2 = api_client.patch(
            f"/api/workflows/templates/{tpl.id}/steps/{step.id}/",
            {"name": "Renamed"},
            format="json",
        )
        assert r2.status_code == 400
        r3 = api_client.delete(f"/api/workflows/templates/{tpl.id}/steps/{step.id}/")
        assert r3.status_code == 400


@pytest.mark.django_db
class TestStepActionAndCancel:
    @patch("apps.workflows.views.notify_step_assigned")
    @patch("apps.workflows.views.notify_consulted")
    @patch("apps.workflows.views.notify_step_completed")
    @patch("apps.workflows.views.notify_informed")
    @patch("apps.workflows.views.notify_workflow_completed")
    @patch("apps.workflows.views.notify_step_rejected")
    def test_action_invalid_not_active_bad_action_no_step(
        self,
        _rej,
        _wc,
        _inf,
        _comp,
        _cons,
        _asg,
        api_client,
        admin,
        reviewer,
        document,
        tpl_two_step,
    ):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        wi_id = resp.data["id"]
        api_client.force_authenticate(user=reviewer)
        api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        api_client.force_authenticate(user=admin)
        api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        wi = WorkflowInstance.objects.get(id=wi_id)
        assert wi.status == "completed"

        r_na = api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        assert r_na.status_code == 400

        api_client.force_authenticate(user=admin)
        doc2 = Document.objects.create(title="D2", folder=document.folder, created_by=admin, status=Document.STATUS_DRAFT)
        resp2 = api_client.post(
            "/api/workflows/instances/",
            {"document": str(doc2.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        wi2 = resp2.data["id"]
        api_client.force_authenticate(user=reviewer)
        r_bad = api_client.post(f"/api/workflows/instances/{wi2}/action/", {"action": "nope"}, format="json")
        assert r_bad.status_code == 400

        WorkflowStepInstance.objects.filter(workflow_instance_id=wi2).update(status="pending", started_at=None)
        WorkflowInstance.objects.filter(id=wi2).update(current_step_order=1)
        r_no = api_client.post(f"/api/workflows/instances/{wi2}/action/", {"action": "approve"}, format="json")
        assert r_no.status_code == 400

    def test_not_assigned_forbidden_non_admin(self, api_client, admin, approver, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        wi_id = resp.data["id"]
        api_client.force_authenticate(user=approver)
        r = api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        assert r.status_code == 403

    def test_admin_can_act_without_assignment(self, api_client, admin, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        wi_id = resp.data["id"]
        api_client.force_authenticate(user=admin)
        r = api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        assert r.status_code == 200

    def test_complete_action_finishes_workflow(self, api_client, admin, reviewer, approver, document):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="Cpl", created_by=admin, is_published=True)
        WorkflowStep.objects.create(
            template=tpl,
            name="R",
            order=1,
            action="review",
            assignee_type="role",
            assignee_role="REVIEWER",
        )
        WorkflowStep.objects.create(
            template=tpl,
            name="A",
            order=2,
            action="acknowledge",
            assignee_type="role",
            assignee_role="APPROVER",
        )
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl.id)},
            format="json",
        )
        wi_id = resp.data["id"]
        api_client.force_authenticate(user=reviewer)
        api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        api_client.force_authenticate(user=approver)
        r = api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "complete"}, format="json")
        assert r.status_code == 200
        document.refresh_from_db()
        assert document.status == Document.STATUS_APPROVED

    def test_skip_optional_step_without_assignees(self, api_client, admin, reviewer, approver, document):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="Skip", created_by=admin, is_published=True)
        WorkflowStep.objects.create(
            template=tpl,
            name="R",
            order=1,
            action="review",
            assignee_type="role",
            assignee_role="REVIEWER",
            is_required=True,
        )
        WorkflowStep.objects.create(
            template=tpl,
            name="Skip me",
            order=2,
            action="review",
            assignee_type="document_ou",
            is_required=False,
        )
        WorkflowStep.objects.create(
            template=tpl,
            name="A",
            order=3,
            action="approve",
            assignee_type="role",
            assignee_role="APPROVER",
            is_required=True,
        )
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl.id)},
            format="json",
        )
        wi_id = resp.data["id"]
        api_client.force_authenticate(user=reviewer)
        api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        wi = WorkflowInstance.objects.get(id=wi_id)
        assert wi.current_step_order == 3
        mid = WorkflowStepInstance.objects.get(workflow_instance=wi, step__order=2)
        assert mid.status == "skipped"

    @patch("apps.workflows.views.notify_workflow_cancelled")
    def test_cancel_workflow_branches(self, mock_cancel, api_client, admin, reviewer, document, tpl_two_step):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        wi_id = resp.data["id"]
        api_client.force_authenticate(user=reviewer)
        r403 = api_client.post(f"/api/workflows/instances/{wi_id}/cancel/")
        assert r403.status_code == 403

        api_client.force_authenticate(user=admin)
        api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        api_client.post(f"/api/workflows/instances/{wi_id}/action/", {"action": "approve"}, format="json")
        r400 = api_client.post(f"/api/workflows/instances/{wi_id}/cancel/")
        assert r400.status_code == 400

        doc2 = Document.objects.create(title="D3", folder=document.folder, created_by=admin, status=Document.STATUS_DRAFT)
        resp2 = api_client.post(
            "/api/workflows/instances/",
            {"document": str(doc2.id), "template": str(tpl_two_step.id)},
            format="json",
        )
        wi2 = resp2.data["id"]
        api_client.force_authenticate(user=admin)
        r_ok = api_client.post(f"/api/workflows/instances/{wi2}/cancel/")
        assert r_ok.status_code == 200
        assert mock_cancel.called


@pytest.mark.django_db
class TestRaciPermissionsOnCreate:
    @patch("apps.workflows.views.notify_step_assigned")
    @patch("apps.workflows.views.notify_consulted")
    def test_create_grants_read_to_raci_users(self, _cons, _asg, api_client, admin, reviewer, document):
        from apps.documents.models import DocumentPermission

        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="RACI", created_by=admin, is_published=True)
        s1 = WorkflowStep.objects.create(
            template=tpl,
            name="R",
            order=1,
            action="review",
            assignee_type="role",
            assignee_role="REVIEWER",
            accountable_user=admin,
        )
        s1.consulted_users.add(admin)
        s1.informed_users.add(admin)
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl.id)},
            format="json",
        )
        assert resp.status_code == 201
        assert DocumentPermission.objects.filter(document=document, user=admin, can_read=True).exists()
