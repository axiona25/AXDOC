# FASE 35.2 — Copertura workflows/serializers.py (SerializerMethodField)
import pytest
from django.contrib.auth import get_user_model

from apps.organizations.models import OrganizationalUnit
from apps.workflows.models import WorkflowInstance, WorkflowStep, WorkflowStepInstance, WorkflowTemplate
from apps.workflows.serializers import (
    WorkflowInstanceSerializer,
    WorkflowStepSerializer,
    WorkflowTemplateDetailSerializer,
    WorkflowTemplateListSerializer,
)

User = get_user_model()


@pytest.mark.django_db
class TestWorkflowStepSerializerDisplays:
    def test_assignee_display_branches(self, db):
        admin = User.objects.create_user(
            email="ws100-a@test.com",
            password="Xx1!",
            first_name="Ada",
            last_name="Min",
            role="ADMIN",
        )
        other = User.objects.create_user(
            email="ws100-u@test.com",
            password="Xx1!",
            first_name="Ugo",
            last_name="User",
            role="OPERATOR",
        )
        tpl = WorkflowTemplate.objects.create(name="S", created_by=admin)
        ou = OrganizationalUnit.objects.create(name="UO1", code="WS100-UO", created_by=admin)

        s_role = WorkflowStep.objects.create(
            template=tpl,
            name="R1",
            order=1,
            assignee_type="role",
            assignee_role="REVIEWER",
        )
        s_role_empty = WorkflowStep.objects.create(
            template=tpl,
            name="R2",
            order=2,
            assignee_type="role",
            assignee_role="",
        )
        s_user = WorkflowStep.objects.create(
            template=tpl,
            name="U",
            order=3,
            assignee_type="specific_user",
            assignee_user=other,
        )
        s_user_empty = WorkflowStep.objects.create(
            template=tpl,
            name="U2",
            order=7,
            assignee_type="specific_user",
            assignee_user=None,
        )
        s_ou = WorkflowStep.objects.create(
            template=tpl,
            name="OU",
            order=4,
            assignee_type="ou_role",
            assignee_ou=ou,
            assignee_ou_role="MANAGER",
            assignee_role="REVIEWER",
        )
        s_ou_no_ou = WorkflowStep.objects.create(
            template=tpl,
            name="OU2",
            order=5,
            assignee_type="ou_role",
            assignee_ou=None,
            assignee_ou_role="X",
        )
        s_doc_ou = WorkflowStep.objects.create(
            template=tpl,
            name="DO",
            order=6,
            assignee_type="document_ou",
        )

        ser = WorkflowStepSerializer()
        assert "REVIEWER" in ser.get_assignee_display(s_role)
        assert ser.get_assignee_display(s_role_empty) == "—"
        assert ser.get_assignee_display(s_user) == "Ugo User"
        assert ser.get_assignee_display(s_user_empty) == "—"
        assert "UO1" in ser.get_assignee_display(s_ou)
        assert ser.get_assignee_display(s_ou_no_ou) == "—"
        assert ser.get_assignee_display(s_doc_ou) == "UO del documento"

    def test_accountable_and_raci_displays(self, db):
        admin = User.objects.create_user(
            email="ws100-b@test.com",
            password="Xx1!",
            first_name="",
            last_name="",
            role="ADMIN",
        )
        tpl = WorkflowTemplate.objects.create(name="T2", created_by=admin)
        step = WorkflowStep.objects.create(
            template=tpl,
            name="S",
            order=1,
            assignee_type="role",
            assignee_role="ADMIN",
            accountable_user=admin,
        )
        c = User.objects.create_user(email="ws100-c@test.com", password="Xx1!", role="OPERATOR")
        i = User.objects.create_user(email="ws100-i@test.com", password="Xx1!", role="OPERATOR")
        step.consulted_users.add(c)
        step.informed_users.add(i)

        ser = WorkflowStepSerializer()
        assert ser.get_accountable_user_display(step) == "ws100-b@test.com"
        step.accountable_user = None
        assert ser.get_accountable_user_display(step) is None
        step.accountable_user = admin
        assert c.email in ser.get_consulted_users_display(step)
        assert i.email in ser.get_informed_users_display(step)


@pytest.mark.django_db
class TestWorkflowTemplateSerializers:
    def test_step_count_on_list_and_detail(self, db):
        admin = User.objects.create_user(email="ws100-d@test.com", password="Xx1!", role="ADMIN")
        tpl = WorkflowTemplate.objects.create(name="LC", created_by=admin)
        WorkflowStep.objects.create(template=tpl, name="A", order=1, assignee_type="role", assignee_role="ADMIN")
        assert WorkflowTemplateListSerializer().get_step_count(tpl) == 1
        assert WorkflowTemplateDetailSerializer().get_step_count(tpl) == 1
        data = WorkflowTemplateDetailSerializer(tpl).data
        assert len(data["steps"]) == 1


@pytest.mark.django_db
class TestWorkflowInstanceSerializerCurrentStep:
    def test_current_step_instance_none_when_order_mismatch(self, db):
        admin = User.objects.create_user(email="ws100-e@test.com", password="Xx1!", role="ADMIN")
        from apps.documents.models import Document, Folder

        folder = Folder.objects.create(name="W", created_by=admin)
        doc = Document.objects.create(title="D", folder=folder, created_by=admin)
        tpl = WorkflowTemplate.objects.create(name="I", created_by=admin, is_published=True)
        step = WorkflowStep.objects.create(
            template=tpl,
            name="S",
            order=1,
            assignee_type="role",
            assignee_role="ADMIN",
        )
        wi = WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=admin,
            status="active",
            current_step_order=99,
        )
        WorkflowStepInstance.objects.create(workflow_instance=wi, step=step, status="pending")
        data = WorkflowInstanceSerializer(wi).data
        assert data["current_step_instance"] is None
