"""
Test autenticazione: login, logout, reset password, me, audit log.
"""
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.authentication.models import PasswordResetToken, AuditLog


class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="login@test.com",
            password="TestPass123!",
            first_name="Login",
            last_name="User",
            must_change_password=False,
        )

    def test_login_success(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@test.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "login@test.com")

    def test_login_wrong_password(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@test.com", "password": "WrongPass1!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "nonexistent@test.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_5_failed_attempts_locks_account(self):
        for _ in range(5):
            self.client.post(
                "/api/auth/login/",
                {"email": "login@test.com", "password": "WrongPass1!"},
                format="json",
            )
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@test.com", "password": "WrongPass1!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
        self.assertIn("locked_until", response.data)

    def test_locked_account_correct_password_still_locked(self):
        self.user.failed_login_attempts = 5
        self.user.locked_until = timezone.now() + timedelta(minutes=15)
        self.user.save()
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@test.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)


class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="logout@test.com",
            password="TestPass123!",
            first_name="Logout",
            last_name="User",
            must_change_password=False,
        )

    def test_logout_blacklists_token(self):
        login_resp = self.client.post(
            "/api/auth/login/",
            {"email": "logout@test.com", "password": "TestPass123!"},
            format="json",
        )
        refresh = login_resp.data["refresh"]
        self.client.post(
            "/api/auth/logout/",
            {"refresh": refresh},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )
        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="reset@test.com",
            password="TestPass123!",
            first_name="Reset",
            last_name="User",
        )

    def test_password_reset_request_existing_email(self):
        response = self.client.post(
            "/api/auth/password-reset/",
            {"email": "reset@test.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            PasswordResetToken.objects.filter(user=self.user).exists()
        )

    def test_password_reset_request_nonexistent_email(self):
        response = self.client.post(
            "/api/auth/password-reset/",
            {"email": "nonexistent@test.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset_confirm_valid_token(self):
        pr = PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "token": str(pr.token),
                "new_password": "NewPass123!",
                "new_password_confirm": "NewPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pr.refresh_from_db()
        self.assertTrue(pr.used)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

    def test_password_reset_confirm_expired_token(self):
        pr = PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "token": str(pr.token),
                "new_password": "NewPass123!",
                "new_password_confirm": "NewPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_used_token(self):
        pr = PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
            used=True,
        )
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "token": str(pr.token),
                "new_password": "NewPass123!",
                "new_password_confirm": "NewPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="me@test.com",
            password="TestPass123!",
            first_name="Me",
            last_name="User",
            must_change_password=False,
        )

    def test_me_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@test.com")

    def test_me_unauthenticated(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuditLogTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # reset rate limit so login can succeed (FASE 14)
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="audit@test.com",
            password="TestPass123!",
            first_name="Audit",
            last_name="User",
            must_change_password=False,
        )

    def test_audit_log_created_on_login(self):
        self.client.post(
            "/api/auth/login/",
            {"email": "audit@test.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertTrue(
            AuditLog.objects.filter(user=self.user, action="LOGIN").exists()
        )

    def test_audit_log_created_on_failed_login(self):
        self.client.post(
            "/api/auth/login/",
            {"email": "audit@test.com", "password": "WrongPass1!"},
            format="json",
        )
        self.assertTrue(
            AuditLog.objects.filter(user=self.user, action="LOGIN_FAILED").exists()
        )
