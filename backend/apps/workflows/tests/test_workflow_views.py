"""
Ciclo workflow via POST /api/workflows/instances/ e action (FASE 31).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder
from apps.workflows.models import WorkflowInstance, WorkflowStep, WorkflowStepInstance, WorkflowTemplate

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin-wfv@test.com",
        password="Admin123!",
        first_name="Admin",
        last_name="WF",
        role="ADMIN",
    )


@pytest.fixture
def reviewer_user(db):
    return User.objects.create_user(
        email="reviewer-wfv@test.com",
        password="Review123!",
        first_name="Reviewer",
        last_name="WF",
        role="REVIEWER",
    )


@pytest.fixture
def approver_user(db):
    return User.objects.create_user(
        email="approver-wfv@test.com",
        password="Approve123!",
        first_name="Approver",
        last_name="WF",
        role="APPROVER",
    )


@pytest.fixture
def workflow_template(db, admin_user):
    tpl = WorkflowTemplate.objects.create(
        name="Approvazione Test API",
        created_by=admin_user,
        is_published=True,
    )
    WorkflowStep.objects.create(
        template=tpl,
        name="Revisione",
        order=1,
        action="review",
        assignee_type="role",
        assignee_role="REVIEWER",
    )
    WorkflowStep.objects.create(
        template=tpl,
        name="Approvazione",
        order=2,
        action="approve",
        assignee_type="role",
        assignee_role="APPROVER",
    )
    return tpl


@pytest.fixture
def document(db, admin_user):
    folder = Folder.objects.create(name="WFV", created_by=admin_user)
    return Document.objects.create(
        title="Doc Workflow Views Test",
        folder=folder,
        status=Document.STATUS_DRAFT,
        created_by=admin_user,
    )


def _results(resp):
    data = resp.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
def test_start_workflow_via_instances_sets_document_in_review(
    api_client, admin_user, document, workflow_template
):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        "/api/workflows/instances/",
        {"document": str(document.id), "template": str(workflow_template.id)},
        format="json",
    )
    assert response.status_code == 201, response.data
    document.refresh_from_db()
    assert document.status == Document.STATUS_IN_REVIEW


@pytest.mark.django_db
def test_workflow_instances_create_step_instances(api_client, admin_user, document, workflow_template):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        "/api/workflows/instances/",
        {"document": str(document.id), "template": str(workflow_template.id)},
        format="json",
    )
    assert response.status_code == 201
    wi_id = response.data.get("id")
    assert WorkflowStepInstance.objects.filter(workflow_instance_id=wi_id).count() == 2


@pytest.mark.django_db
def test_reviewer_can_approve_step_via_instance_action(
    api_client, admin_user, reviewer_user, document, workflow_template
):
    api_client.force_authenticate(user=admin_user)
    resp = api_client.post(
        "/api/workflows/instances/",
        {"document": str(document.id), "template": str(workflow_template.id)},
        format="json",
    )
    assert resp.status_code == 201
    wi_id = resp.data["id"]
    step = WorkflowStepInstance.objects.filter(
        workflow_instance_id=wi_id,
        step__action="review",
    ).first()
    assert step is not None

    api_client.force_authenticate(user=reviewer_user)
    resp2 = api_client.post(
        f"/api/workflows/instances/{wi_id}/action/",
        {"action": "approve", "comment": "OK"},
        format="json",
    )
    assert resp2.status_code == 200
    step.refresh_from_db()
    assert step.status == "completed"


@pytest.mark.django_db
def test_full_approval_completes_workflow_and_document(
    api_client, admin_user, reviewer_user, approver_user, document, workflow_template
):
    api_client.force_authenticate(user=admin_user)
    resp = api_client.post(
        "/api/workflows/instances/",
        {"document": str(document.id), "template": str(workflow_template.id)},
        format="json",
    )
    wi_id = resp.data["id"]

    step1 = WorkflowStepInstance.objects.filter(
        workflow_instance_id=wi_id,
        step__action="review",
    ).first()
    api_client.force_authenticate(user=reviewer_user)
    api_client.post(
        f"/api/workflows/instances/{wi_id}/action/",
        {"action": "approve"},
        format="json",
    )

    step2 = WorkflowStepInstance.objects.filter(
        workflow_instance_id=wi_id,
        step__action="approve",
    ).first()
    api_client.force_authenticate(user=approver_user)
    resp2 = api_client.post(
        f"/api/workflows/instances/{wi_id}/action/",
        {"action": "approve"},
        format="json",
    )
    assert resp2.status_code == 200

    document.refresh_from_db()
    assert document.status == Document.STATUS_APPROVED
    wi = WorkflowInstance.objects.get(id=wi_id)
    assert wi.status == "completed"


@pytest.mark.django_db
def test_reject_step_rejects_workflow_and_document(
    api_client, admin_user, reviewer_user, document, workflow_template
):
    api_client.force_authenticate(user=admin_user)
    resp = api_client.post(
        "/api/workflows/instances/",
        {"document": str(document.id), "template": str(workflow_template.id)},
        format="json",
    )
    wi_id = resp.data["id"]
    api_client.force_authenticate(user=reviewer_user)
    resp2 = api_client.post(
        f"/api/workflows/instances/{wi_id}/action/",
        {"action": "reject", "comment": "Non conforme"},
        format="json",
    )
    assert resp2.status_code == 200
    document.refresh_from_db()
    assert document.status == Document.STATUS_REJECTED


@pytest.mark.django_db
def test_non_assigned_user_cannot_act_on_step(
    api_client, admin_user, approver_user, document, workflow_template
):
    api_client.force_authenticate(user=admin_user)
    resp = api_client.post(
        "/api/workflows/instances/",
        {"document": str(document.id), "template": str(workflow_template.id)},
        format="json",
    )
    wi_id = resp.data["id"]
    api_client.force_authenticate(user=approver_user)
    resp2 = api_client.post(
        f"/api/workflows/instances/{wi_id}/action/",
        {"action": "approve"},
        format="json",
    )
    assert resp2.status_code == 403


@pytest.mark.django_db
def test_list_workflow_instances(api_client, admin_user, document, workflow_template):
    api_client.force_authenticate(user=admin_user)
    api_client.post(
        "/api/workflows/instances/",
        {"document": str(document.id), "template": str(workflow_template.id)},
        format="json",
    )
    resp = api_client.get("/api/workflows/instances/")
    assert resp.status_code == 200
    rows = _results(resp)
    assert len(rows) >= 1


@pytest.mark.django_db
def test_workflow_template_crud(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    resp = api_client.post(
        "/api/workflows/templates/",
        {"name": "Nuovo Template CRUD", "description": ""},
        format="json",
    )
    assert resp.status_code == 201
    tpl_id = resp.data.get("id")
    assert tpl_id

    resp2 = api_client.get(f"/api/workflows/templates/{tpl_id}/")
    assert resp2.status_code == 200

    resp3 = api_client.patch(
        f"/api/workflows/templates/{tpl_id}/",
        {"name": "Template Aggiornato"},
        format="json",
    )
    assert resp3.status_code == 200
    assert resp3.data.get("name") == "Template Aggiornato"
