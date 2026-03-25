"""Permessi API pannello admin (FASE 31)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin-perm@test.com",
        password="Admin123!",
        first_name="A",
        last_name="B",
        role="ADMIN",
    )


@pytest.fixture
def operator_user(db):
    return User.objects.create_user(
        email="operator-perm@test.com",
        password="Op123456!",
        first_name="O",
        last_name="P",
        role="OPERATOR",
    )


@pytest.mark.django_db
def test_license_view_requires_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    r = api_client.get("/api/admin/license/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_settings_view_requires_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    r = api_client.get("/api/admin/settings/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_backup_view_requires_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    r = api_client.get("/api/admin/backups/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_operator_cannot_access_admin_views(api_client, operator_user):
    api_client.force_authenticate(user=operator_user)
    assert api_client.get("/api/admin/license/").status_code == 403
    assert api_client.get("/api/admin/settings/").status_code == 403
    assert api_client.get("/api/admin/system_info/").status_code == 403
    assert api_client.get("/api/admin/backups/").status_code == 403


@pytest.mark.django_db
def test_unauthenticated_cannot_access_admin_views(api_client):
    assert api_client.get("/api/admin/license/").status_code in (401, 403)
    assert api_client.get("/api/admin/settings/").status_code in (401, 403)
