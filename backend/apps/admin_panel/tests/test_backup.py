"""Test backup API (FASE 15)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user(email="backup-admin@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_backup_list_requires_admin(api_client):
    """GET /api/admin/backups/ without auth returns 403."""
    r = api_client.get("/api/admin/backups/")
    assert r.status_code in (401, 403)


@pytest.mark.django_db
def test_backup_list_returns_db_and_media(api_client, admin_user):
    """GET /api/admin/backups/ as ADMIN returns db and media lists."""
    api_client.force_authenticate(user=admin_user)
    r = api_client.get("/api/admin/backups/")
    assert r.status_code == 200
    data = r.json()
    assert "db" in data
    assert "media" in data
    assert isinstance(data["db"], list)
    assert isinstance(data["media"], list)
