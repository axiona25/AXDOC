"""Notifiche workflow (FASE 31)."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.documents.models import Document, Folder
from apps.notifications.models import Notification
from apps.workflows.models import (
    WorkflowInstance,
    WorkflowStep,
    WorkflowStepInstance,
    WorkflowTemplate,
)
from apps.workflows.notifications import (
    notify_step_assigned,
    notify_step_completed,
    notify_step_rejected,
    notify_workflow_cancelled,
    notify_workflow_completed,
)

User = get_user_model()


@pytest.fixture
def users_and_workflow(db):
    admin = User.objects.create_user(
        email="n-admin@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="Admin",
    )
    assignee = User.objects.create_user(
        email="n-assign@test.com",
        password="Rev123!",
        role="REVIEWER",
        first_name="R",
        last_name="User",
    )
    folder = Folder.objects.create(name="N", created_by=admin)
    document = Document.objects.create(
        title="Doc Notif",
        folder=folder,
        created_by=admin,
        status=Document.STATUS_IN_REVIEW,
    )
    tpl = WorkflowTemplate.objects.create(name="T", created_by=admin, is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="S1",
        order=1,
        action="review",
        assignee_type="role",
        assignee_role="REVIEWER",
    )
    wi = WorkflowInstance.objects.create(
        template=tpl,
        document=document,
        started_by=admin,
        status="active",
        current_step_order=1,
    )
    si = WorkflowStepInstance.objects.create(
        workflow_instance=wi,
        step=step,
        status="in_progress",
        started_at=timezone.now(),
    )
    si.assigned_to.add(assignee)
    return admin, assignee, document, wi, si


@pytest.mark.django_db
def test_notify_step_assigned_creates_notification(users_and_workflow):
    _admin, assignee, _doc, _wi, si = users_and_workflow
    before = Notification.objects.filter(recipient=assignee).count()
    notify_step_assigned(si)
    assert Notification.objects.filter(recipient=assignee).count() == before + 1


@pytest.mark.django_db
def test_notify_step_completed_notifies_owner(users_and_workflow):
    admin, assignee, _doc, _wi, si = users_and_workflow
    si.action_taken = "approve"
    si.save(update_fields=["action_taken"])
    notify_step_completed(si, assignee)
    assert Notification.objects.filter(recipient=admin, notification_type="workflow_approved").exists()


@pytest.mark.django_db
def test_notify_step_rejected_notifies_owner(users_and_workflow):
    admin, assignee, _doc, _wi, si = users_and_workflow
    si.comment = "Motivo test"
    si.save(update_fields=["comment"])
    notify_step_rejected(si, assignee)
    assert Notification.objects.filter(recipient=admin, notification_type="workflow_rejected").exists()


@pytest.mark.django_db
def test_notify_workflow_completed_notifies_owner(users_and_workflow):
    admin, _assignee, _doc, wi, _si = users_and_workflow
    notify_workflow_completed(wi)
    assert Notification.objects.filter(recipient=admin, notification_type="workflow_completed").exists()


@pytest.mark.django_db
def test_notify_workflow_cancelled_notifies_assignees(users_and_workflow):
    admin, assignee, _doc, wi, si = users_and_workflow
    notify_workflow_cancelled(wi, admin)
    qs = Notification.objects.filter(notification_type="system", title="Workflow annullato")
    assert qs.filter(recipient=assignee).exists()
