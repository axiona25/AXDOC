# FASE 35.1 — Copertura authentication/views.py ≥95%
import sys
import types
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, force_authenticate

from apps.authentication.models import PasswordResetToken, UserInvitation
from apps.authentication.views import (
    LDAPStatusView,
    LDAPSyncView,
    _decode_mfa_pending_token,
    sso_jwt_redirect_view,
)
from apps.authentication.mfa import generate_backup_codes
from apps.authentication.token_utils import issue_refresh_for_user
from apps.organizations.models import OrganizationalUnit, Tenant

User = get_user_model()


@pytest.mark.django_db
class TestDecodeMfaPendingToken:
    # Copre righe: 66, 74, 77, 79-80 (authentication/views.py _decode_mfa_pending_token)
    def test_empty_and_invalid_payloads(self, db):
        assert _decode_mfa_pending_token("") is None
        assert _decode_mfa_pending_token(None) is None
        bad = jwt.encode(
            {"scope": "other", "user_id": str(uuid.uuid4()), "exp": datetime.utcnow() + timedelta(minutes=5), "iat": datetime.utcnow()},
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        tok = bad if isinstance(bad, str) else bad.decode()
        assert _decode_mfa_pending_token(tok) is None
        no_uid = jwt.encode(
            {"scope": "mfa_pending", "exp": datetime.utcnow() + timedelta(minutes=5), "iat": datetime.utcnow()},
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        tok2 = no_uid if isinstance(no_uid, str) else no_uid.decode()
        assert _decode_mfa_pending_token(tok2) is None
        assert _decode_mfa_pending_token("not-a-jwt") is None

    def test_valid_returns_user(self, db):
        u = User.objects.create_user(email="mfa-dec@test.com", password="Xx1!", first_name="A", last_name="B", role="OPERATOR")
        payload = {
            "user_id": str(u.id),
            "scope": "mfa_pending",
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        }
        raw = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        tok = raw if isinstance(raw, str) else raw.decode()
        assert _decode_mfa_pending_token(tok).id == u.id


@pytest.mark.django_db
class TestLoginRateLimitAndLogoutBlacklist:
    # Copre righe: 119, 230-231
    def test_login_rate_limited_429(self, db):
        u = User.objects.create_user(email="rl@test.com", password="GoodPass1", first_name="A", last_name="B", role="OPERATOR")
        c = APIClient()
        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = 30
            r = c.post("/api/auth/login/", {"email": u.email, "password": "GoodPass1"}, format="json")
            assert r.status_code == 429

    def test_logout_blacklist_exception_swallowed(self, db):
        u = User.objects.create_user(email="lo@test.com", password="GoodPass1", first_name="A", last_name="B", role="OPERATOR")
        refresh = issue_refresh_for_user(u)
        c = APIClient()
        c.force_authenticate(user=u)
        mock_tok = MagicMock()
        mock_tok.blacklist.side_effect = ValueError("bl")
        with patch("rest_framework_simplejwt.tokens.RefreshToken", return_value=mock_tok):
            r = c.post("/api/auth/logout/", {"refresh": str(refresh)}, format="json")
            assert r.status_code == 204


@pytest.mark.django_db
class TestPasswordFlows:
    # Copre righe: 302-304, 335-337, 357-375
    def test_reset_confirm_weak_password_400(self, db):
        u = User.objects.create_user(email="pr@test.com", password="OldPass12!", first_name="A", last_name="B", role="OPERATOR")
        pr = PasswordResetToken.objects.create(user=u, expires_at=timezone.now() + timedelta(hours=1))
        c = APIClient()
        with patch(
            "django.contrib.auth.password_validation.validate_password",
            side_effect=DjangoValidationError(["Troppo debole."]),
        ):
            r = c.post(
                "/api/auth/password-reset/confirm/",
                {
                    "token": str(pr.token),
                    "new_password": "Zz9ValidPass!",
                    "new_password_confirm": "Zz9ValidPass!",
                },
                format="json",
            )
        assert r.status_code == 400
        assert "new_password" in r.json()

    def test_change_password_weak_new_400(self, db):
        u = User.objects.create_user(email="cp@test.com", password="GoodPass1", first_name="A", last_name="B", role="OPERATOR")
        c = APIClient()
        c.force_authenticate(user=u)
        with patch(
            "django.contrib.auth.password_validation.validate_password",
            side_effect=DjangoValidationError(["Policy."]),
        ):
            r = c.post(
                "/api/auth/change-password/",
                {
                    "old_password": "GoodPass1",
                    "new_password": "Zz9OtherPass!",
                    "new_password_confirm": "Zz9OtherPass!",
                },
                format="json",
            )
        assert r.status_code == 400
        assert "new_password" in r.json()

    def test_change_password_required_forbidden_and_ok(self, db):
        u = User.objects.create_user(
            email="cpr@test.com",
            password="TempPass1!",
            first_name="A",
            last_name="B",
            role="OPERATOR",
            must_change_password=False,
        )
        c = APIClient()
        c.force_authenticate(user=u)
        assert c.post("/api/auth/change_password/", {"new_password": "Zz9NewX!", "confirm_password": "Zz9NewX!"}, format="json").status_code == 403
        u.must_change_password = True
        u.save(update_fields=["must_change_password"])
        r2 = c.post(
            "/api/auth/change_password/",
            {"new_password": "bad", "confirm_password": "bad"},
            format="json",
        )
        assert r2.status_code == 400
        with patch(
            "django.contrib.auth.password_validation.validate_password",
            side_effect=DjangoValidationError(["django"]),
        ):
            r2b = c.post(
                "/api/auth/change_password/",
                {"new_password": "Zz9MidX!", "confirm_password": "Zz9MidX!"},
                format="json",
            )
        assert r2b.status_code == 400
        assert "new_password" in r2b.json()
        r3 = c.post(
            "/api/auth/change_password/",
            {"new_password": "Zz9NewX!", "confirm_password": "Zz9NewX!"},
            format="json",
        )
        assert r3.status_code == 200
        u.refresh_from_db()
        assert u.must_change_password is False


@pytest.mark.django_db
class TestInviteAcceptOuAndWeakPassword:
    # Copre righe: 408-409, 464-466
    def test_invite_with_ou_and_accept_weak_password(self, db):
        t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D", "plan": "enterprise"})
        ou = OrganizationalUnit.objects.create(name="AuthOU", code="AO", tenant=t)
        admin = User.objects.create_user(
            email="inv-adm@test.com",
            password="Admin123!",
            role="ADMIN",
            first_name="A",
            last_name="D",
        )
        admin.tenant = t
        admin.save(update_fields=["tenant"])
        c = APIClient()
        c.force_authenticate(user=admin)
        em = f"inv-{uuid.uuid4().hex[:8]}@test.com"
        with patch("apps.authentication.views.send_mail"):
            r = c.post(
                "/api/auth/invite/",
                {"email": em, "organizational_unit_id": str(ou.id), "role": "OPERATOR", "ou_role": "OPERATOR"},
                format="json",
            )
        assert r.status_code == 201
        inv = UserInvitation.objects.get(email__iexact=em)
        ac = APIClient()
        r2 = ac.post(
            f"/api/auth/accept-invitation/{inv.token}/",
            {
                "first_name": "N",
                "last_name": "U",
                "password": "x",
                "password_confirm": "x",
            },
            format="json",
        )
        assert r2.status_code == 400
        body = r2.json()
        assert "password" in body or "non_field_errors" in body

    def test_accept_invitation_get_invalid(self):
        assert APIClient().get(f"/api/auth/accept-invitation/{uuid.uuid4()}/").status_code == 400

    def test_accept_invitation_post_validate_password_view_branch(self, db):
        t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D", "plan": "enterprise"})
        ou = OrganizationalUnit.objects.create(name="AccOU", code="AC", tenant=t)
        inv = UserInvitation.objects.create(
            email=f"acc-{uuid.uuid4().hex[:8]}@test.com",
            invited_by=User.objects.create_user(
                email="acc-ad@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B"
            ),
            organizational_unit=ou,
            expires_at=timezone.now() + timedelta(days=1),
        )
        with patch(
            "django.contrib.auth.password_validation.validate_password",
            side_effect=DjangoValidationError(["django policy"]),
        ):
            r = APIClient().post(
                f"/api/auth/accept-invitation/{inv.token}/",
                {
                    "first_name": "A",
                    "last_name": "B",
                    "password": "Zz9ValidPass!",
                    "password_confirm": "Zz9ValidPass!",
                },
                format="json",
            )
        assert r.status_code == 400
        assert "password" in r.json()

    def test_accept_invitation_success_sets_tenant_from_ou(self, db):
        t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D", "plan": "enterprise"})
        ou = OrganizationalUnit.objects.create(name="Acc2", code="A2", tenant=t)
        adm = User.objects.create_user(email="acc2-ad@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B")
        adm.tenant = t
        adm.save(update_fields=["tenant"])
        em = f"ok-{uuid.uuid4().hex[:8]}@test.com"
        inv = UserInvitation.objects.create(
            email=em,
            invited_by=adm,
            organizational_unit=ou,
            expires_at=timezone.now() + timedelta(days=1),
        )
        with patch("apps.authentication.views.send_mail"):
            r = APIClient().post(
                f"/api/auth/accept-invitation/{inv.token}/",
                {
                    "first_name": "N",
                    "last_name": "U",
                    "password": "Zz9AcceptOk!",
                    "password_confirm": "Zz9AcceptOk!",
                },
                format="json",
            )
        assert r.status_code == 200
        nu = User.objects.get(email__iexact=em)
        assert nu.tenant_id == t.id


@pytest.mark.django_db
class TestMFASetupConfirmDisableVerifyBranches:
    # Copre righe: 543, 549, 556, 590, 599-602, 604, 628, 641-645, 647
    def test_mfa_setup_already_enabled_400(self, db):
        u = User.objects.create_user(
            email="mfa-s@test.com",
            password="GoodPass1",
            first_name="A",
            last_name="B",
            role="OPERATOR",
            mfa_enabled=True,
        )
        c = APIClient()
        c.force_authenticate(user=u)
        assert c.get("/api/auth/mfa/setup/").status_code == 400

    def test_mfa_confirm_bad_code_length_and_expired_cache(self, db):
        u = User.objects.create_user(email="mfa-c@test.com", password="GoodPass1", first_name="A", last_name="B", mfa_enabled=False)
        c = APIClient()
        c.force_authenticate(user=u)
        assert c.post("/api/auth/mfa/setup/confirm/", {"code": "12"}, format="json").status_code == 400
        assert c.post("/api/auth/mfa/setup/confirm/", {"code": "123456"}, format="json").status_code == 400

    def test_mfa_disable_not_enabled_400(self, db):
        u = User.objects.create_user(email="mfa-d@test.com", password="GoodPass1", first_name="A", last_name="B", mfa_enabled=False)
        c = APIClient()
        c.force_authenticate(user=u)
        assert c.post("/api/auth/mfa/disable/", {"code": "123456"}, format="json").status_code == 400

    def test_mfa_disable_invalid_code_400(self, db):
        u = User.objects.create_user(
            email="mfa-d2@test.com",
            password="GoodPass1",
            first_name="A",
            last_name="B",
            mfa_enabled=True,
            mfa_secret="enc",
            mfa_backup_codes=[],
        )
        c = APIClient()
        c.force_authenticate(user=u)
        with patch("apps.authentication.views.decrypt_secret", return_value=""):
            assert c.post("/api/auth/mfa/disable/", {"code": "999999"}, format="json").status_code == 400

    def test_mfa_verify_invalid_token_and_bad_code(self, db):
        c = APIClient()
        assert (
            c.post("/api/auth/mfa/verify/", {"mfa_pending_token": "bad", "code": "123456"}, format="json").status_code == 401
        )
        u = User.objects.create_user(
            email="mfa-v@test.com",
            password="GoodPass1",
            first_name="A",
            last_name="B",
            mfa_enabled=True,
            mfa_secret="x",
        )
        payload = {
            "user_id": str(u.id),
            "scope": "mfa_pending",
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        }
        raw = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        tok = raw if isinstance(raw, str) else raw.decode()
        with patch("apps.authentication.views.decrypt_secret", return_value="secret"):
            with patch("apps.authentication.views.verify_totp", return_value=False):
                r = c.post("/api/auth/mfa/verify/", {"mfa_pending_token": tok, "code": "123456"}, format="json")
                assert r.status_code == 400

    def test_mfa_setup_confirm_when_already_enabled_post(self, db):
        u = User.objects.create_user(
            email="mfa-ce@test.com",
            password="GoodPass1",
            first_name="A",
            last_name="B",
            mfa_enabled=True,
        )
        c = APIClient()
        c.force_authenticate(user=u)
        assert c.post("/api/auth/mfa/setup/confirm/", {"code": "123456"}, format="json").status_code == 400

    def test_mfa_disable_and_verify_with_backup_code(self, db):
        plain, hashed = generate_backup_codes()
        u = User.objects.create_user(
            email="mfa-bu@test.com",
            password="GoodPass1",
            first_name="A",
            last_name="B",
            mfa_enabled=True,
            mfa_secret="enc",
            mfa_backup_codes=hashed,
        )
        c = APIClient()
        c.force_authenticate(user=u)
        with patch("apps.authentication.views.decrypt_secret", return_value=""):
            r = c.post("/api/auth/mfa/disable/", {"backup_code": plain[0]}, format="json")
            assert r.status_code == 200
        u.mfa_enabled = True
        u.mfa_backup_codes = hashed
        u.save(update_fields=["mfa_enabled", "mfa_backup_codes"])
        payload = {
            "user_id": str(u.id),
            "scope": "mfa_pending",
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        }
        raw = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        tok = raw if isinstance(raw, str) else raw.decode()
        with patch("apps.authentication.views.decrypt_secret", return_value=""):
            r2 = APIClient().post(
                "/api/auth/mfa/verify/",
                {"mfa_pending_token": tok, "backup_code": plain[0]},
                format="json",
            )
            assert r2.status_code == 200
            assert "access" in r2.json()


@pytest.mark.django_db
class TestSSOAndJwtRedirect:
    # Copre righe: 699-703, 710-726
    @override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="k", SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET="s")
    def test_sso_google_returns_auth_url(self):
        c = APIClient()
        r = c.get("/api/auth/sso/google/")
        assert r.status_code == 200
        assert "auth_url" in r.json()

    def test_sso_jwt_redirect_unauthenticated(self):
        req = RequestFactory().get("/api/auth/sso/jwt-redirect/")
        req.user = AnonymousUser()
        resp = sso_jwt_redirect_view(req)
        assert resp.status_code == 302
        assert "error=sso_failed" in resp["Location"]

    def test_sso_jwt_redirect_authenticated(self, db):
        u = User.objects.create_user(email="sso-j@test.com", password="GoodPass1", first_name="A", last_name="B", role="OPERATOR")
        req = RequestFactory().get("/api/auth/sso/jwt-redirect/")
        req.user = u
        resp = sso_jwt_redirect_view(req)
        assert resp.status_code == 302
        assert "access=" in resp["Location"]

    def test_sso_jwt_redirect_non_user_model_instance(self, db):
        u = User.objects.create_user(email="sso-nu@test.com", password="GoodPass1", first_name="A", last_name="B", role="OPERATOR")

        class _AuthLike:
            is_authenticated = True

        alt = _AuthLike()
        alt.pk = u.pk
        req = RequestFactory().get("/api/auth/sso/jwt-redirect/")
        req.user = alt
        resp = sso_jwt_redirect_view(req)
        assert resp.status_code == 302
        assert "access=" in resp["Location"]


@pytest.mark.django_db
class TestLDAPViews:
    # Copre righe: 736-753, 765-777
    @override_settings(LDAP_ENABLED=False)
    def test_ldap_status_disabled(self):
        req = RequestFactory().get("/")
        admin = User.objects.create_user(email="ldap-ad@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B")
        force_authenticate(req, user=admin)
        view = LDAPStatusView.as_view()
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["connected"] is False

    @override_settings(
        LDAP_ENABLED=True,
        AUTH_LDAP_SERVER_URI="ldap://127.0.0.1:65530",
        AUTH_LDAP_BIND_DN="cn=admin",
        AUTH_LDAP_BIND_PASSWORD="x",
    )
    def test_ldap_status_connection_error(self):
        req = RequestFactory().get("/")
        admin = User.objects.create_user(email="ldap-ad2@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B")
        force_authenticate(req, user=admin)
        view = LDAPStatusView.as_view()
        resp = view(req)
        assert resp.status_code == 200
        assert resp.data["connected"] is False
        assert resp.data.get("error")

    @override_settings(LDAP_ENABLED=False)
    def test_ldap_sync_disabled_503(self):
        req = RequestFactory().post("/")
        admin = User.objects.create_user(email="ldap-s@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B")
        force_authenticate(req, user=admin)
        view = LDAPSyncView.as_view()
        resp = view(req)
        assert resp.status_code == 503

    @override_settings(LDAP_ENABLED=True)
    def test_ldap_sync_exception_500(self):
        req = RequestFactory().post("/")
        admin = User.objects.create_user(email="ldap-s2@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B")
        force_authenticate(req, user=admin)
        with patch("django.core.management.call_command", side_effect=RuntimeError("cmd")):
            view = LDAPSyncView.as_view()
            resp = view(req)
            assert resp.status_code == 500

    @override_settings(LDAP_ENABLED=True)
    def test_ldap_sync_success(self):
        req = RequestFactory().post("/")
        admin = User.objects.create_user(email="ldap-s3@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B")
        force_authenticate(req, user=admin)
        with patch("django.core.management.call_command"):
            view = LDAPSyncView.as_view()
            resp = view(req)
            assert resp.status_code == 200

    @override_settings(
        LDAP_ENABLED=True,
        AUTH_LDAP_SERVER_URI="ldap://mock",
        AUTH_LDAP_BIND_DN="",
        AUTH_LDAP_BIND_PASSWORD="",
    )
    def test_ldap_status_connected_true_with_fake_ldap(self):
        req = RequestFactory().get("/")
        admin = User.objects.create_user(email="ldap-ok@test.com", password="Admin123!", role="ADMIN", first_name="A", last_name="B")
        force_authenticate(req, user=admin)
        fake_mod = types.ModuleType("ldap")
        conn = MagicMock()
        conn.simple_bind_s = MagicMock()
        conn.unbind_s = MagicMock()
        fake_mod.initialize = lambda *a, **k: conn
        old = sys.modules.get("ldap")
        sys.modules["ldap"] = fake_mod
        try:
            view = LDAPStatusView.as_view()
            resp = view(req)
            assert resp.status_code == 200
            assert resp.data["connected"] is True
        finally:
            if old is not None:
                sys.modules["ldap"] = old
            else:
                sys.modules.pop("ldap", None)
