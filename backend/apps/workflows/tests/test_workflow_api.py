"""
Test API workflow: CRUD template, publish, start_workflow, workflow_action (RF-048..RF-056).
"""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.documents.models import Document, Folder, DocumentPermission
from apps.workflows.models import WorkflowTemplate, WorkflowStep, WorkflowInstance, WorkflowStepInstance

User = get_user_model()


class WorkflowAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.reviewer = User.objects.create_user(
            email="reviewer@test.com",
            password="Rev123!",
            first_name="Rev",
            last_name="User",
            role="REVIEWER",
        )
        self.approver = User.objects.create_user(
            email="approver@test.com",
            password="App123!",
            first_name="App",
            last_name="User",
            role="APPROVER",
        )
        self.folder = Folder.objects.create(name="F", created_by=self.admin)
        self.document = Document.objects.create(
            title="Doc Test",
            folder=self.folder,
            status=Document.STATUS_DRAFT,
            created_by=self.admin,
        )
        DocumentPermission.objects.create(document=self.document, user=self.reviewer, can_read=True, can_write=False)
        DocumentPermission.objects.create(document=self.document, user=self.approver, can_read=True, can_write=False)
        self.template = WorkflowTemplate.objects.create(
            name="Approvazione Standard",
            created_by=self.admin,
            is_published=True,
        )
        self.step1 = WorkflowStep.objects.create(
            template=self.template,
            name="Revisione",
            order=1,
            action="review",
            assignee_type="role",
            assignee_role="REVIEWER",
        )
        self.step2 = WorkflowStep.objects.create(
            template=self.template,
            name="Approvazione",
            order=2,
            action="approve",
            assignee_type="role",
            assignee_role="APPROVER",
        )

    def test_crud_template_admin_only(self):
        self.client.force_authenticate(user=self.reviewer)
        r = self.client.post(
            "/api/workflows/templates/",
            {"name": "Nuovo", "description": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 403)
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            "/api/workflows/templates/",
            {"name": "Nuovo", "description": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["name"], "Nuovo")

    def test_publish_workflow(self):
        template = WorkflowTemplate.objects.create(name="Bozza", created_by=self.admin, is_published=False)
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(f"/api/workflows/templates/{template.id}/publish/")
        self.assertEqual(r.status_code, 200)
        template.refresh_from_db()
        self.assertTrue(template.is_published)

    def test_start_workflow_on_document(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            f"/api/documents/{self.document.id}/start_workflow/",
            {"template_id": str(self.template.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, Document.STATUS_IN_REVIEW)
        instance = self.document.workflow_instances.get(status="active")
        self.assertEqual(instance.current_step_order, 1)
        step_instances = list(instance.step_instances.order_by("step__order"))
        self.assertEqual(step_instances[0].status, "in_progress")
        self.assertIn(self.reviewer, step_instances[0].assigned_to.all())

    def test_workflow_action_approve_advances(self):
        instance = WorkflowInstance.objects.create(
            template=self.template,
            document=self.document,
            started_by=self.admin,
            status="active",
            current_step_order=1,
        )
        si1 = WorkflowStepInstance.objects.create(workflow_instance=instance, step=self.step1, status="in_progress")
        si1.assigned_to.add(self.reviewer)
        WorkflowStepInstance.objects.create(workflow_instance=instance, step=self.step2, status="pending")
        self.document.status = Document.STATUS_IN_REVIEW
        self.document.save()
        self.client.force_authenticate(user=self.reviewer)
        r = self.client.post(
            f"/api/documents/{self.document.id}/workflow_action/",
            {"action": "approve", "comment": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        instance.refresh_from_db()
        self.assertEqual(instance.current_step_order, 2)
        si1.refresh_from_db()
        self.assertEqual(si1.status, "completed")

    def test_workflow_action_approve_last_completes(self):
        instance = WorkflowInstance.objects.create(
            template=self.template,
            document=self.document,
            started_by=self.admin,
            status="active",
            current_step_order=2,
        )
        WorkflowStepInstance.objects.create(workflow_instance=instance, step=self.step1, status="completed")
        si2 = WorkflowStepInstance.objects.create(workflow_instance=instance, step=self.step2, status="in_progress")
        si2.assigned_to.add(self.approver)
        self.client.force_authenticate(user=self.approver)
        r = self.client.post(
            f"/api/documents/{self.document.id}/workflow_action/",
            {"action": "approve", "comment": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        instance.refresh_from_db()
        self.assertEqual(instance.status, "completed")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, Document.STATUS_APPROVED)

    def test_workflow_action_reject(self):
        instance = WorkflowInstance.objects.create(
            template=self.template,
            document=self.document,
            started_by=self.admin,
            status="active",
            current_step_order=1,
        )
        si1 = WorkflowStepInstance.objects.create(workflow_instance=instance, step=self.step1, status="in_progress")
        si1.assigned_to.add(self.reviewer)
        self.client.force_authenticate(user=self.reviewer)
        r = self.client.post(
            f"/api/documents/{self.document.id}/workflow_action/",
            {"action": "reject", "comment": "Non conforme."},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        instance.refresh_from_db()
        self.assertEqual(instance.status, "rejected")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, Document.STATUS_REJECTED)

    def test_workflow_action_not_assigned_403(self):
        instance = WorkflowInstance.objects.create(
            template=self.template,
            document=self.document,
            started_by=self.admin,
            status="active",
            current_step_order=1,
        )
        si1 = WorkflowStepInstance.objects.create(workflow_instance=instance, step=self.step1, status="in_progress")
        si1.assigned_to.add(self.reviewer)
        self.client.force_authenticate(user=self.approver)
        r = self.client.post(
            f"/api/documents/{self.document.id}/workflow_action/",
            {"action": "approve", "comment": ""},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_mine_filter(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.get("/api/workflows/templates/?mine=true")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.data.get("results", r.data) if isinstance(r.data, dict) else r.data), 1)
