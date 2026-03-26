"""Test API posta (FASE 33)."""
import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(
        email="mail-admin@test.com",
        password="Test123!",
        role="ADMIN",
    )
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def operator_client(db):
    u = User.objects.create_user(
        email="mail-op@test.com",
        password="Test123!",
        role="OPERATOR",
    )
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.mark.django_db
class TestMailAPI:
    def test_list_mail_accounts(self, admin_client):
        r = admin_client.get("/api/mail/accounts/")
        assert r.status_code == 200

    def test_list_mail_accounts_operator_forbidden(self, operator_client):
        r = operator_client.get("/api/mail/accounts/")
        assert r.status_code == 403

    def test_list_mail_messages(self, admin_client):
        r = admin_client.get("/api/mail/messages/")
        assert r.status_code == 200
