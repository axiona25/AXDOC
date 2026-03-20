"""Test invito e accettazione invito (RF-018)."""
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from apps.authentication.models import UserInvitation, AuditLog
from apps.organizations.models import OrganizationalUnit

User = get_user_model()


class InviteUserTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin1!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.admin.is_staff = True
        self.admin.save()
        self.ou = OrganizationalUnit.objects.create(name="IT", code="IT")

    def test_invite_creates_invitation_and_returns_201(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/auth/invite/",
            {"email": "newuser@test.com", "role": "OPERATOR"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserInvitation.objects.filter(email="newuser@test.com").exists())

    def test_invite_duplicate_email_registered_400(self):
        User.objects.create_user(
            email="existing@test.com", password="X", first_name="E", last_name="X"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/auth/invite/",
            {"email": "existing@test.com", "role": "OPERATOR"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invite_duplicate_pending_400(self):
        UserInvitation.objects.create(
            email="pending@test.com",
            invited_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/auth/invite/",
            {"email": "pending@test.com", "role": "OPERATOR"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AcceptInvitationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com", password="A1!", first_name="A", last_name="dmin", role="ADMIN"
        )
        self.ou = OrganizationalUnit.objects.create(name="IT", code="IT")
        self.inv = UserInvitation.objects.create(
            email="invited@test.com",
            invited_by=self.admin,
            role="OPERATOR",
            ou_role="OPERATOR",
            organizational_unit=self.ou,
            expires_at=timezone.now() + timedelta(days=7),
        )

    def test_get_invitation_returns_email(self):
        response = self.client.get(f"/api/auth/accept-invitation/{self.inv.token}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "invited@test.com")

    def test_accept_creates_user_and_returns_jwt(self):
        response = self.client.post(
            f"/api/auth/accept-invitation/{self.inv.token}/",
            {
                "first_name": "Invited",
                "last_name": "User",
                "password": "NewPass123!",
                "password_confirm": "NewPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("user", response.data)
        user = User.objects.get(email="invited@test.com")
        self.assertEqual(user.first_name, "Invited")
        self.inv.refresh_from_db()
        self.assertTrue(self.inv.is_used)

    def test_accept_expired_token_400(self):
        self.inv.expires_at = timezone.now() - timedelta(days=1)
        self.inv.save()
        response = self.client.post(
            f"/api/auth/accept-invitation/{self.inv.token}/",
            {
                "first_name": "X",
                "last_name": "Y",
                "password": "NewPass123!",
                "password_confirm": "NewPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
