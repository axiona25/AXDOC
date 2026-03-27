# FASE 35E.1 — Copertura: audit/security_views.py
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import SecurityIncident
from apps.users.models import User


class SecurityIncidentViewSetFinalTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="svf-adm@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="D",
            role="ADMIN",
        )
        self.approver = User.objects.create_user(
            email="svf-ap@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="P",
            role="APPROVER",
        )
        self.operator = User.objects.create_user(
            email="svf-op@test.com",
            password="TestPass123!",
            first_name="O",
            last_name="P",
            role="OPERATOR",
        )

    def test_operator_list_empty(self):
        SecurityIncident.objects.create(
            title="X",
            description="d",
            severity="low",
            category="other",
            detected_at=timezone.now(),
            reported_by=self.admin,
        )
        self.client.force_authenticate(self.operator)
        r = self.client.get("/api/security-incidents/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 0)

    def test_approver_sees_incidents_and_filters(self):
        SecurityIncident.objects.create(
            title="F1",
            description="d",
            severity="medium",
            category="other",
            status="open",
            detected_at=timezone.now(),
            reported_by=self.admin,
        )
        self.client.force_authenticate(self.approver)
        r = self.client.get(
            "/api/security-incidents/?severity=medium&status=open&category=other&search=F1"
            + f"&date_from={timezone.now().date()}&date_to={timezone.now().date()}"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data["results"]), 1)

    def test_export_admin_assignee_branch(self):
        self.client.force_authenticate(self.admin)
        assignee = User.objects.create_user(
            email="svf-as@test.com",
            password="TestPass123!",
            first_name="As",
            last_name="Si",
            role="OPERATOR",
        )
        SecurityIncident.objects.create(
            title="With",
            description="d",
            severity="low",
            category="other",
            detected_at=timezone.now(),
            reported_by=self.admin,
            assigned_to=assignee,
        )
        r = self.client.get("/api/security-incidents/export_excel/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r2 = self.client.get("/api/security-incidents/export_pdf/")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)

    def test_export_pdf_forbidden_for_non_admin(self):
        self.client.force_authenticate(self.operator)
        r = self.client.get("/api/security-incidents/export_pdf/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
