"""Test estesi viste authentication (FASE 33C)."""
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.token_utils import issue_refresh_for_user

User = get_user_model()


@pytest.fixture
def user_login(db):
    return User.objects.create_user(
        email="auth-ext@test.com",
        password="GoodPass1",
        first_name="A",
        last_name="B",
        role="OPERATOR",
    )


@pytest.mark.django_db
class TestLoginLogoutRefresh:
    def test_login_success(self, user_login):
        c = APIClient()
        r = c.post(
            "/api/auth/login/",
            {"email": user_login.email, "password": "GoodPass1"},
            format="json",
        )
        assert r.status_code == 200
        assert "access" in r.json() and "refresh" in r.json()

    def test_login_wrong_password_401(self, user_login):
        c = APIClient()
        r = c.post(
            "/api/auth/login/",
            {"email": user_login.email, "password": "WrongPass1"},
            format="json",
        )
        assert r.status_code == 401

    def test_refresh_token(self, user_login):
        refresh = issue_refresh_for_user(user_login)
        c = APIClient()
        r = c.post("/api/auth/refresh/", {"refresh": str(refresh)}, format="json")
        assert r.status_code == 200
        assert "access" in r.json()

    def test_logout_then_refresh_fails(self, user_login):
        refresh = issue_refresh_for_user(user_login)
        c = APIClient()
        c.force_authenticate(user=user_login)
        out = c.post("/api/auth/logout/", {"refresh": str(refresh)}, format="json")
        assert out.status_code == 204
        r2 = APIClient().post("/api/auth/refresh/", {"refresh": str(refresh)}, format="json")
        assert r2.status_code in (401, 403)

    def test_logout_missing_refresh_400(self, user_login):
        c = APIClient()
        c.force_authenticate(user=user_login)
        r = c.post("/api/auth/logout/", {}, format="json")
        assert r.status_code == 400

    def test_me_requires_auth(self):
        r = APIClient().get("/api/auth/me/")
        assert r.status_code == 401

    def test_me_ok(self, user_login):
        c = APIClient()
        c.force_authenticate(user=user_login)
        r = c.get("/api/auth/me/")
        assert r.status_code == 200
        assert r.json().get("email") == user_login.email


@pytest.mark.django_db
class TestPasswordResetAndChange:
    @patch("apps.authentication.views.send_mail")
    def test_password_reset_sends_mail(self, mock_send, user_login):
        c = APIClient()
        r = c.post("/api/auth/password-reset/", {"email": user_login.email}, format="json")
        assert r.status_code == 200
        mock_send.assert_called()

    def test_password_reset_confirm_invalid_token(self):
        c = APIClient()
        r = c.post(
            "/api/auth/password-reset/confirm/",
            {
                "token": str(uuid.uuid4()),
                "new_password": "NewPass12",
                "new_password_confirm": "NewPass12",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_change_password_wrong_old(self, user_login):
        c = APIClient()
        c.force_authenticate(user=user_login)
        r = c.post(
            "/api/auth/change-password/",
            {
                "old_password": "not-this",
                "new_password": "NewPass12",
                "new_password_confirm": "NewPass12",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_change_password_success(self, user_login):
        c = APIClient()
        c.force_authenticate(user=user_login)
        r = c.post(
            "/api/auth/change-password/",
            {
                "old_password": "GoodPass1",
                "new_password": "Zz9NewPasswordX!",
                "new_password_confirm": "Zz9NewPasswordX!",
            },
            format="json",
        )
        assert r.status_code == 200, r.json()
        user_login.refresh_from_db()
        assert user_login.check_password("Zz9NewPasswordX!")
