"""Test integrazione endpoint admin (FASE 31)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_settings_get_returns_200_for_admin(api_client):
    admin = User.objects.create_user(
        email="adm-views@test.com",
        password="Admin123!",
        first_name="A",
        last_name="B",
        role="ADMIN",
    )
    api_client.force_authenticate(user=admin)
    resp = api_client.get("/api/admin/settings/")
    assert resp.status_code == 200
    assert "email" in resp.data


@pytest.mark.django_db
def test_settings_update_by_admin(api_client):
    admin = User.objects.create_user(
        email="adm2-views@test.com",
        password="Admin123!",
        first_name="A",
        last_name="B",
        role="ADMIN",
    )
    api_client.force_authenticate(user=admin)
    resp = api_client.patch(
        "/api/admin/settings/",
        {"organization": {"name": "Test Org"}},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data.get("organization", {}).get("name") == "Test Org"


@pytest.mark.django_db
def test_settings_forbidden_for_operator(api_client):
    user = User.objects.create_user(
        email="op-views@test.com",
        password="Op123456!",
        first_name="A",
        last_name="B",
        role="OPERATOR",
    )
    api_client.force_authenticate(user=user)
    resp = api_client.get("/api/admin/settings/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_license_view_forbidden_for_operator(api_client):
    user = User.objects.create_user(
        email="op2-views@test.com",
        password="Op123456!",
        first_name="A",
        last_name="B",
        role="OPERATOR",
    )
    api_client.force_authenticate(user=user)
    resp = api_client.get("/api/admin/license/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_system_info_requires_admin(api_client):
    user = User.objects.create_user(
        email="op3-views@test.com",
        password="Op123456!",
        first_name="A",
        last_name="B",
        role="OPERATOR",
    )
    api_client.force_authenticate(user=user)
    resp = api_client.get("/api/admin/system_info/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_backup_list_requires_admin(api_client):
    user = User.objects.create_user(
        email="op4-views@test.com",
        password="Op123456!",
        first_name="A",
        last_name="B",
        role="OPERATOR",
    )
    api_client.force_authenticate(user=user)
    resp = api_client.get("/api/admin/backups/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_cannot_access_settings(api_client):
    resp = api_client.get("/api/admin/settings/")
    assert resp.status_code in (401, 403)
