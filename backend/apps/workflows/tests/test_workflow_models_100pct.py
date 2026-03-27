# FASE 35.2 — Copertura workflows/models.py
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.documents.models import Document, Folder
from apps.workflows.models import WorkflowInstance, WorkflowStep, WorkflowStepInstance, WorkflowTemplate

User = get_user_model()


@pytest.mark.django_db
class TestWorkflowModelMethods:
    def test_str_and_can_be_applied(self, db):
        admin = User.objects.create_user(email="wm100-a@test.com", password="Xx1!", role="ADMIN")
        tpl = WorkflowTemplate.objects.create(name="NomeTpl", created_by=admin)
        folder = Folder.objects.create(name="F", created_by=admin)
        doc = Document.objects.create(title="Titolo", folder=folder, created_by=admin)
        step = WorkflowStep.objects.create(
            template=tpl,
            name="Step1",
            order=1,
            assignee_type="role",
            assignee_role="ADMIN",
        )
        wi = WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=admin,
            current_step_order=1,
        )
        assert str(tpl) == "NomeTpl"
        assert "NomeTpl" in str(step)
        assert "Titolo" in str(wi)
        assert tpl.can_be_applied_to(doc) is True
        si = WorkflowStepInstance.objects.create(workflow_instance=wi, step=step, status="pending")
        assert "Step1" in str(si)

    def test_get_current_step_advance_and_assignees_delegate(self, db):
        admin = User.objects.create_user(email="wm100-b@test.com", password="Xx1!", role="ADMIN")
        tpl = WorkflowTemplate.objects.create(name="T", created_by=admin)
        folder = Folder.objects.create(name="F2", created_by=admin)
        doc = Document.objects.create(title="D", folder=folder, created_by=admin)
        s1 = WorkflowStep.objects.create(
            template=tpl,
            name="S1",
            order=1,
            assignee_type="role",
            assignee_role="ADMIN",
        )
        s2 = WorkflowStep.objects.create(
            template=tpl,
            name="S2",
            order=2,
            assignee_type="role",
            assignee_role="ADMIN",
        )
        wi = WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=admin,
            current_step_order=1,
        )
        si1 = WorkflowStepInstance.objects.create(workflow_instance=wi, step=s1, status="in_progress")
        WorkflowStepInstance.objects.create(workflow_instance=wi, step=s2, status="pending")
        assert wi.get_current_step().id == si1.id
        wi.advance()
        wi.refresh_from_db()
        assert wi.current_step_order == 2
        si2 = WorkflowStepInstance.objects.get(workflow_instance=wi, step=s2)
        assert wi.get_current_step().id == si2.id

        with patch("apps.workflows.services.WorkflowService.get_assignees", return_value=[admin]) as m:
            out = wi.get_assignees_for_step(s1)
        m.assert_called_once_with(s1, doc)
        assert out == [admin]
