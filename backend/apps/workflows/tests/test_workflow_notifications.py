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
from apps.organizations.models import Tenant
from apps.workflows.notifications import (
    notify_consulted,
    notify_informed,
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


@pytest.mark.django_db
def test_notify_step_completed_skips_when_no_owner_or_same_actor(users_and_workflow):
    admin, assignee, _doc, wi, si = users_and_workflow
    wi.started_by = None
    wi.save(update_fields=["started_by"])
    si.action_taken = "approve"
    si.save(update_fields=["action_taken"])
    before = Notification.objects.count()
    notify_step_completed(si, assignee)
    assert Notification.objects.count() == before

    wi.started_by = assignee
    wi.save(update_fields=["started_by"])
    notify_step_completed(si, assignee)
    assert Notification.objects.count() == before


@pytest.mark.django_db
def test_notify_step_rejected_skips_when_no_owner_or_same_actor(users_and_workflow):
    admin, assignee, _doc, wi, si = users_and_workflow
    wi.started_by = None
    wi.save(update_fields=["started_by"])
    before = Notification.objects.count()
    notify_step_rejected(si, assignee)
    assert Notification.objects.count() == before

    wi.started_by = assignee
    wi.save(update_fields=["started_by"])
    notify_step_rejected(si, assignee)
    assert Notification.objects.count() == before


@pytest.mark.django_db
def test_notify_workflow_completed_requires_started_by(users_and_workflow):
    admin, _a, _doc, wi, _si = users_and_workflow
    wi.started_by = None
    wi.save(update_fields=["started_by"])
    before = Notification.objects.count()
    notify_workflow_completed(wi)
    assert Notification.objects.count() == before

    wi.started_by = admin
    wi.save(update_fields=["started_by"])
    notify_workflow_completed(wi)
    assert Notification.objects.filter(recipient=admin, notification_type="workflow_completed").exists()


@pytest.mark.django_db
def test_notify_workflow_cancelled_skips_canceller_and_handles_no_in_progress(users_and_workflow):
    admin, assignee, _doc, wi, si = users_and_workflow
    si.status = "pending"
    si.save(update_fields=["status"])
    notify_workflow_cancelled(wi, assignee)
    assert Notification.objects.filter(recipient=admin, notification_type="system").exists()

    si.status = "in_progress"
    si.save(update_fields=["status"])
    before = Notification.objects.filter(recipient=assignee, notification_type="system").count()
    notify_workflow_cancelled(wi, assignee)
    after = Notification.objects.filter(recipient=assignee, notification_type="system").count()
    assert after == before


@pytest.mark.django_db
def test_notify_consulted_creates_rows(users_and_workflow):
    admin, assignee, _doc, wi, si = users_and_workflow
    si.step.consulted_users.add(admin)
    before = Notification.objects.filter(metadata__raci_role="consulted").count()
    notify_consulted(si)
    assert Notification.objects.filter(metadata__raci_role="consulted").count() == before + 1


@pytest.mark.django_db
def test_notify_informed_branches(users_and_workflow):
    admin, assignee, _doc, wi, si = users_and_workflow
    informed = User.objects.create_user(
        email="n-inf@test.com",
        password="Xx1!",
        role="OPERATOR",
        first_name="Inf",
        last_name="Ormed",
    )
    acc = User.objects.create_user(
        email="n-acc@test.com",
        password="Xx1!",
        role="OPERATOR",
        first_name="Acc",
        last_name="Able",
    )
    si.step.informed_users.add(informed)
    si.step.accountable_user = acc
    si.step.save(update_fields=["accountable_user"])
    notify_informed(si, "reject", assignee)
    assert Notification.objects.filter(recipient=informed, notification_type="workflow_approved").exists()
    assert Notification.objects.filter(recipient=acc, notification_type="workflow_approved").exists()

    notify_informed(si, "unknown_action", assignee)
    si.step.informed_users.add(assignee)
    notify_informed(si, "approve", assignee)


@pytest.mark.django_db
def test_notify_step_assigned_uses_document_tenant_id(db):
    admin = User.objects.create_user(
        email="n-ten@test.com",
        password="Xx1!",
        role="ADMIN",
        first_name="T",
        last_name="A",
    )
    tenant = Tenant.objects.create(name="TOrg", slug="torg-wf")
    folder = Folder.objects.create(name="TN", created_by=admin)
    document = Document.objects.create(
        title="Doc Tenant",
        folder=folder,
        created_by=admin,
        status=Document.STATUS_IN_REVIEW,
        tenant=tenant,
    )
    tpl = WorkflowTemplate.objects.create(name="TT", created_by=admin, is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="S1",
        order=1,
        action="review",
        assignee_type="role",
        assignee_role="ADMIN",
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
    si.assigned_to.add(admin)
    notify_step_assigned(si)
    n = Notification.objects.filter(recipient=admin).order_by("-id").first()
    assert n.tenant_id == tenant.id


@pytest.mark.django_db
def test_notify_step_assigned_falls_back_to_workflow_tenant(db):
    admin = User.objects.create_user(
        email="n-wf-ten@test.com",
        password="Xx1!",
        role="ADMIN",
        first_name="W",
        last_name="F",
    )
    tenant = Tenant.objects.create(name="WOrg", slug="worg-wf")
    folder = Folder.objects.create(name="WF", created_by=admin)
    document = Document.objects.create(
        title="Doc no tenant",
        folder=folder,
        created_by=admin,
        status=Document.STATUS_IN_REVIEW,
        tenant=None,
    )
    tpl = WorkflowTemplate.objects.create(name="TW", created_by=admin, is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="S1",
        order=1,
        action="review",
        assignee_type="role",
        assignee_role="ADMIN",
    )
    wi = WorkflowInstance.objects.create(
        template=tpl,
        document=document,
        started_by=admin,
        status="active",
        current_step_order=1,
        tenant=tenant,
    )
    si = WorkflowStepInstance.objects.create(
        workflow_instance=wi,
        step=step,
        status="in_progress",
        started_at=timezone.now(),
    )
    si.assigned_to.add(admin)
    notify_step_assigned(si)
    n = Notification.objects.filter(recipient=admin).order_by("-id").first()
    assert n.tenant_id == tenant.id
