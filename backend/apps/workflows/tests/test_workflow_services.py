"""Servizi workflow: assegnatari e scadenze (FASE 31)."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.documents.models import Document, Folder
from apps.workflows.models import WorkflowInstance, WorkflowStep, WorkflowStepInstance, WorkflowTemplate
from apps.workflows.services import WorkflowService

User = get_user_model()


@pytest.fixture
def document_with_folder(db):
    admin = User.objects.create_user(
        email="svc-admin@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="B",
    )
    rev = User.objects.create_user(
        email="svc-rev@test.com",
        password="Rev123!",
        role="REVIEWER",
        first_name="R",
        last_name="V",
    )
    folder = Folder.objects.create(name="SVC", created_by=admin)
    document = Document.objects.create(
        title="Doc SVC",
        folder=folder,
        created_by=admin,
    )
    return admin, rev, document


@pytest.mark.django_db
def test_get_assignees_returns_users_for_role(document_with_folder):
    _admin, reviewer, document = document_with_folder
    tpl = WorkflowTemplate.objects.create(name="T1", is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="R",
        order=1,
        assignee_type="role",
        assignee_role="REVIEWER",
    )
    users = WorkflowService.get_assignees(step, document)
    assert reviewer in users


@pytest.mark.django_db
def test_get_assignees_specific_user(document_with_folder):
    admin, reviewer, document = document_with_folder
    tpl = WorkflowTemplate.objects.create(name="T2", is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="U",
        order=1,
        assignee_type="specific_user",
        assignee_user=reviewer,
    )
    users = WorkflowService.get_assignees(step, document)
    assert users == [reviewer]


@pytest.mark.django_db
def test_get_assignees_empty_when_role_missing(document_with_folder):
    _admin, _reviewer, document = document_with_folder
    tpl = WorkflowTemplate.objects.create(name="T3", is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="X",
        order=1,
        assignee_type="role",
        assignee_role=None,
    )
    assert WorkflowService.get_assignees(step, document) == []


@pytest.mark.django_db
def test_get_assignees_ou_role(document_with_folder):
    admin, reviewer, document = document_with_folder
    from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership

    ou = OrganizationalUnit.objects.create(name="UO WF", code="UO-WF-SVC", created_by=admin)
    OrganizationalUnitMembership.objects.create(
        user=reviewer,
        organizational_unit=ou,
        role="REVIEWER",
        is_active=True,
    )
    tpl = WorkflowTemplate.objects.create(name="T-OU", is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="OU step",
        order=1,
        assignee_type="ou_role",
        assignee_ou=ou,
        assignee_ou_role="REVIEWER",
    )
    users = WorkflowService.get_assignees(step, document)
    assert reviewer in users


@pytest.mark.django_db
def test_get_assignees_document_ou(document_with_folder):
    admin, reviewer, document = document_with_folder
    from apps.documents.models import DocumentOUPermission
    from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership

    ou = OrganizationalUnit.objects.create(name="UO Doc", code="UO-DOC-SVC", created_by=admin)
    DocumentOUPermission.objects.create(
        document=document,
        organizational_unit=ou,
        can_read=True,
        can_write=False,
    )
    OrganizationalUnitMembership.objects.create(
        user=reviewer,
        organizational_unit=ou,
        role="OPERATOR",
        is_active=True,
    )
    tpl = WorkflowTemplate.objects.create(name="T-DOCOU", is_published=True)
    step = WorkflowStep.objects.create(
        template=tpl,
        name="Doc OU",
        order=1,
        assignee_type="document_ou",
    )
    users = WorkflowService.get_assignees(step, document)
    assert reviewer in users


@pytest.mark.django_db
def test_check_deadline_violations_returns_overdue_instances(document_with_folder):
    admin, reviewer, document = document_with_folder
    tpl = WorkflowTemplate.objects.create(name="T4", is_published=True)
    step = WorkflowStep.objects.create(template=tpl, name="D", order=1)
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
        deadline=timezone.now() - timedelta(days=1),
    )
    si.assigned_to.add(reviewer)
    overdue = WorkflowService.check_deadline_violations()
    assert si in overdue or any(x.id == si.id for x in overdue)
