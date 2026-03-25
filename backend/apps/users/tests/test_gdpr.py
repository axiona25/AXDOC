"""Test GDPR: consensi, export, anonimizzazione (FASE 28)."""
import json

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, ConsentRecord
from apps.authentication.models import AuditLog


class GdprConsentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="gdpr@test.com",
            password="TestPass123!",
            first_name="G",
            last_name="Dpr",
            must_change_password=False,
        )

    def test_get_my_consents_empty(self):
        self.client.force_authenticate(self.user)
        r = self.client.get("/api/users/my_consents/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data, [])

    def test_post_consent_record(self):
        self.client.force_authenticate(self.user)
        r = self.client.post(
            "/api/users/my_consents/",
            {
                "consent_type": "privacy_policy",
                "granted": True,
                "version": "1.0",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(r.data["granted"])
        self.assertEqual(ConsentRecord.objects.filter(user=self.user).count(), 1)

    def test_export_my_data_returns_json(self):
        self.client.force_authenticate(self.user)
        r = self.client.get("/api/users/export_my_data/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = json.loads(r.content.decode())
        self.assertIn("personal_info", data)
        self.assertEqual(data["personal_info"]["email"], "gdpr@test.com")

    def test_anonymize_user_admin_only(self):
        other = User.objects.create_user(
            email="victim@test.com",
            password="TestPass123!",
            first_name="V",
            last_name="ictim",
            must_change_password=False,
        )
        self.client.force_authenticate(self.user)
        r = self.client.post(f"/api/users/{other.id}/anonymize/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymize_replaces_personal_data(self):
        admin = User.objects.create_user(
            email="admin_gdpr@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="Dmin",
            must_change_password=False,
            role="ADMIN",
        )
        other = User.objects.create_user(
            email="victim2@test.com",
            password="TestPass123!",
            first_name="V",
            last_name="Two",
            must_change_password=False,
        )
        ConsentRecord.objects.create(
            user=other,
            consent_type="privacy_policy",
            version="1.0",
            granted=True,
        )
        self.client.force_authenticate(admin)
        r = self.client.post(f"/api/users/{other.id}/anonymize/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        other.refresh_from_db()
        self.assertTrue(other.is_deleted)
        self.assertFalse(other.is_active)
        self.assertIn("anonymized_", other.email)
        self.assertEqual(ConsentRecord.objects.filter(user=other).count(), 0)
        self.assertTrue(
            AuditLog.objects.filter(action="USER_ANONYMIZED", user=admin).exists()
        )

    def test_cannot_anonymize_self(self):
        admin = User.objects.create_user(
            email="admin_self@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="Self",
            must_change_password=False,
            role="ADMIN",
        )
        self.client.force_authenticate(admin)
        r = self.client.post(f"/api/users/{admin.id}/anonymize/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
