"""Test API incidenti di sicurezza (FASE 28)."""
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User
from apps.audit.models import SecurityIncident


class SecurityIncidentApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="inc_admin@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="Dmin",
            must_change_password=False,
            role="ADMIN",
        )
        self.operator = User.objects.create_user(
            email="inc_op@test.com",
            password="TestPass123!",
            first_name="O",
            last_name="P",
            must_change_password=False,
            role="OPERATOR",
        )

    def test_admin_can_create_incident(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(
            "/api/security-incidents/",
            {
                "title": "Test incident",
                "description": "Desc",
                "severity": "low",
                "category": "other",
                "detected_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SecurityIncident.objects.count(), 1)

    def test_non_admin_cannot_create(self):
        self.client.force_authenticate(self.operator)
        r = self.client.post(
            "/api/security-incidents/",
            {
                "title": "X",
                "description": "Y",
                "severity": "low",
                "category": "other",
                "detected_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_severity(self):
        SecurityIncident.objects.create(
            title="High",
            description="d",
            severity="high",
            category="other",
            detected_at=timezone.now(),
            reported_by=self.admin,
        )
        SecurityIncident.objects.create(
            title="Low",
            description="d",
            severity="low",
            category="other",
            detected_at=timezone.now(),
            reported_by=self.admin,
        )
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/security-incidents/?severity=high")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data["results"][0]["title"], "High")

    def test_update_status_to_resolved(self):
        inc = SecurityIncident.objects.create(
            title="R",
            description="d",
            severity="medium",
            category="other",
            status="open",
            detected_at=timezone.now(),
            reported_by=self.admin,
        )
        self.client.force_authenticate(self.admin)
        r = self.client.patch(
            f"/api/security-incidents/{inc.id}/",
            {"status": "resolved"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        inc.refresh_from_db()
        self.assertEqual(inc.status, "resolved")
