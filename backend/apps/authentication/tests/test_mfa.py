"""
Test MFA TOTP: setup, confirm, login con MFA, verify, disable (RF-002, RNF-008).
"""
from unittest.mock import patch
from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from apps.authentication.models import AuditLog
from apps.authentication.mfa import verify_totp, generate_totp_secret, verify_backup_code

User = get_user_model()


class MFASetupTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="mfa@test.com",
            password="TestPass123!",
            first_name="MFA",
            last_name="User",
            mfa_enabled=False,
        )

    def tearDown(self):
        cache.clear()

    def test_setup_init_returns_qr_and_secret(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/mfa/setup/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("secret", response.data)
        self.assertIn("qr_code_base64", response.data)
        self.assertIn("otpauth_uri", response.data)
        self.assertTrue(cache.get(f"mfa_setup_{self.user.id}"))

    def test_setup_init_already_enabled_400(self):
        self.user.mfa_enabled = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/mfa/setup/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MFASetupConfirmTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="confirm@test.com",
            password="TestPass123!",
            first_name="Confirm",
            last_name="User",
            mfa_enabled=False,
        )
        self.secret = generate_totp_secret()
        cache.set(f"mfa_setup_{self.user.id}", self.secret, timeout=600)

    def tearDown(self):
        cache.clear()

    @patch("apps.authentication.views.encrypt_secret")
    def test_confirm_valid_totp_enables_mfa(self, mock_encrypt):
        mock_encrypt.return_value = "encrypted"
        import pyotp
        code = pyotp.TOTP(self.secret).now()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/auth/mfa/setup/confirm/",
            {"code": code},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertIn("backup_codes", response.data)
        self.assertEqual(len(response.data["backup_codes"]), 8)
        self.user.refresh_from_db()
        self.assertTrue(self.user.mfa_enabled)

    def test_confirm_invalid_code_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/auth/mfa/setup/confirm/",
            {"code": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginMFAFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="mfalogin@test.com",
            password="TestPass123!",
            first_name="MFA",
            last_name="Login",
            mfa_enabled=True,
            mfa_secret="encrypted_dummy",
        )

    def test_login_with_mfa_returns_pending_token(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "mfalogin@test.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("mfa_required"))
        self.assertIn("mfa_pending_token", response.data)
        self.assertNotIn("access", response.data)


class MFAVerifyTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="verify@test.com",
            password="TestPass123!",
            first_name="Verify",
            last_name="User",
            mfa_enabled=True,
        )
        from apps.authentication.encryption import encrypt_secret
        self.secret = generate_totp_secret()
        self.user.mfa_secret = encrypt_secret(self.secret)
        self.user.mfa_backup_codes = []
        self.user.save()

    def test_verify_with_valid_totp_returns_jwt(self):
        from apps.authentication.views import _create_mfa_pending_token
        import pyotp
        token = _create_mfa_pending_token(self.user)
        code = pyotp.TOTP(self.secret).now()
        response = self.client.post(
            "/api/auth/mfa/verify/",
            {"mfa_pending_token": token, "code": code},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)


class MFADisableTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="disable@test.com",
            password="TestPass123!",
            first_name="Disable",
            last_name="User",
            mfa_enabled=True,
        )
        from apps.authentication.encryption import encrypt_secret
        self.secret = generate_totp_secret()
        self.user.mfa_secret = encrypt_secret(self.secret)
        self.user.save()

    def test_disable_with_valid_totp(self):
        import pyotp
        code = pyotp.TOTP(self.secret).now()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/auth/mfa/disable/",
            {"code": code},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.mfa_enabled)
        self.assertEqual(self.user.mfa_secret, "")
