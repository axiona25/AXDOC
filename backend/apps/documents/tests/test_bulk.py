"""Operazioni bulk documenti (FASE 26)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder, DocumentVersion

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def folder(db):
    return Folder.objects.create(name="F")


@pytest.fixture
def admin(db):
    u = User.objects.create_user(email="adm_bulk@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def operator(db):
    return User.objects.create_user(email="op_bulk@test.com", password="test", role="OPERATOR")


def _doc(user, folder, title="D"):
    d = Document.objects.create(title=title, folder=folder, created_by=user, owner=user)
    DocumentVersion.objects.create(
        document=d,
        version_number=1,
        file_name="x.pdf",
        file_size=10,
        checksum="a",
        created_by=user,
        is_current=True,
    )
    d.current_version = 1
    d.save()
    return d


@pytest.mark.django_db
class TestBulkDelete:
    def test_bulk_delete_soft_deletes_documents(self, api_client, admin, folder):
        d1 = _doc(admin, folder, "A")
        d2 = _doc(admin, folder, "B")
        api_client.force_authenticate(user=admin)
        r = api_client.post(
            "/api/documents/bulk_delete/",
            {"document_ids": [str(d1.id), str(d2.id)]},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["deleted"] == 2
        assert Document.objects.filter(id=d1.id, is_deleted=True).exists()

    def test_bulk_delete_max_100(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        r = api_client.post("/api/documents/bulk_delete/", {"document_ids": []}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_delete_only_own_for_non_admin(self, api_client, operator, admin, folder):
        mine = _doc(operator, folder, "Mine")
        other = _doc(admin, folder, "Other")
        api_client.force_authenticate(user=operator)
        r = api_client.post(
            "/api/documents/bulk_delete/",
            {"document_ids": [str(mine.id), str(other.id)]},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["deleted"] == 1
        assert Document.objects.filter(id=mine.id, is_deleted=True).exists()
        assert Document.objects.filter(id=other.id, is_deleted=False).exists()


@pytest.mark.django_db
class TestBulkMove:
    def test_bulk_move_to_folder(self, api_client, admin, folder):
        f2 = Folder.objects.create(name="Target", created_by=admin)
        d = _doc(admin, folder)
        api_client.force_authenticate(user=admin)
        r = api_client.post(
            "/api/documents/bulk_move/",
            {"document_ids": [str(d.id)], "folder_id": str(f2.id)},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["moved"] == 1
        d.refresh_from_db()
        assert d.folder_id == f2.id

    def test_bulk_move_to_root(self, api_client, admin, folder):
        d = _doc(admin, folder)
        api_client.force_authenticate(user=admin)
        r = api_client.post(
            "/api/documents/bulk_move/",
            {"document_ids": [str(d.id)], "folder_id": None},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        d.refresh_from_db()
        assert d.folder_id is None


@pytest.mark.django_db
class TestBulkStatus:
    def test_bulk_status_admin_can_archive(self, api_client, admin, folder):
        d = _doc(admin, folder)
        api_client.force_authenticate(user=admin)
        r = api_client.post(
            "/api/documents/bulk_status/",
            {"document_ids": [str(d.id)], "status": "ARCHIVED"},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        d.refresh_from_db()
        assert d.status == Document.STATUS_ARCHIVED

    def test_bulk_status_operator_forbidden(self, api_client, operator, folder):
        d = _doc(operator, folder)
        api_client.force_authenticate(user=operator)
        r = api_client.post(
            "/api/documents/bulk_status/",
            {"document_ids": [str(d.id)], "status": "ARCHIVED"},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN
