"""Pipeline social-auth: create_or_update_user."""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.authentication.pipeline import create_or_update_user

User = get_user_model()


@pytest.fixture
def strategy():
    class S:
        pass

    return S()


@pytest.fixture
def backend():
    class B:
        name = "google-oauth2"

    return B()


@pytest.mark.django_db
class TestSSOPipeline:
    def test_empty_details_without_user(self, strategy, backend):
        assert create_or_update_user(strategy, {}, backend) == {}

    def test_empty_details_when_no_email(self, strategy, backend):
        assert create_or_update_user(strategy, {"first_name": "A"}, backend) == {}

    def test_existing_session_user_updates_names(self, strategy, backend):
        u = User.objects.create_user(
            email=f"pipe-{uuid.uuid4().hex[:8]}@t.com",
            password="x",
            first_name="Old",
            last_name="Name",
        )
        out = create_or_update_user(
            strategy,
            {"first_name": "New", "last_name": "Sur", "email": u.email},
            backend,
            user=u,
        )
        assert out == {"user": u}
        u.refresh_from_db()
        assert u.first_name == "New" and u.last_name == "Sur"

    def test_associate_by_email_existing(self, strategy, backend):
        u = User.objects.create_user(email=f"ex-{uuid.uuid4().hex[:8]}@sso.it", password="x")
        out = create_or_update_user(
            strategy,
            {"email": u.email.upper(), "first_name": "X", "last_name": "Y"},
            backend,
        )
        assert out["user"].id == u.id

    def test_create_new_sso_user(self, strategy, backend):
        em = f"new-{uuid.uuid4().hex[:8]}@sso.it"
        out = create_or_update_user(
            strategy,
            {"email": em, "first_name": "Nu", "last_name": "Vo"},
            backend,
        )
        nu = out["user"]
        assert nu.email == em
        assert nu.role == "OPERATOR"
        assert not nu.has_usable_password()

    def test_user_update_keeps_names_when_details_blank(self, strategy, backend):
        u = User.objects.create_user(
            email=f"keep-{uuid.uuid4().hex[:8]}@sso.it",
            password="x",
            first_name="Keep",
            last_name="Me",
        )
        create_or_update_user(
            strategy,
            {"first_name": "", "last_name": "", "email": u.email},
            backend,
            user=u,
        )
        u.refresh_from_db()
        assert u.first_name == "Keep" and u.last_name == "Me"
