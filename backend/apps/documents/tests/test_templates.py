"""Template documenti (FASE 26)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Folder, DocumentTemplate
from apps.metadata.models import MetadataStructure

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    u = User.objects.create_user(email="adm_tpl@test.com", password="test")
    u.role = "ADMIN"
    u.save()
    return u


@pytest.fixture
def operator(db):
    return User.objects.create_user(email="op_tpl@test.com", password="test", role="OPERATOR")


@pytest.mark.django_db
class TestDocumentTemplate:
    def test_admin_can_create_template(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        r = api_client.post(
            "/api/document-templates/",
            {"name": "Standard", "description": "Test", "is_active": True},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json()["name"] == "Standard"

    def test_operator_cannot_create_template(self, api_client, operator):
        api_client.force_authenticate(user=operator)
        r = api_client.post(
            "/api/document-templates/",
            {"name": "X"},
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_only_active_for_non_admin(self, api_client, admin, operator):
        DocumentTemplate.objects.create(name="On", created_by=admin, is_active=True)
        DocumentTemplate.objects.create(name="Off", created_by=admin, is_active=False)
        api_client.force_authenticate(user=operator)
        r = api_client.get("/api/document-templates/")
        assert r.status_code == status.HTTP_200_OK
        names = [x["name"] for x in r.json().get("results", r.json()) if isinstance(x, dict)]
        if "results" in r.json():
            names = [x["name"] for x in r.json()["results"]]
        else:
            names = [x["name"] for x in r.json()] if isinstance(r.json(), list) else []
        assert "On" in names
        assert "Off" not in names

    def test_template_with_folder_and_metadata(self, api_client, admin):
        folder = Folder.objects.create(name="D", created_by=admin)
        meta = MetadataStructure.objects.create(name="M", is_active=True, applicable_to=["document"])
        api_client.force_authenticate(user=admin)
        r = api_client.post(
            "/api/document-templates/",
            {
                "name": "Full",
                "default_folder": str(folder.id),
                "default_metadata_structure": str(meta.id),
                "default_metadata_values": {"a": "1"},
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        t = DocumentTemplate.objects.get(id=r.json()["id"])
        assert t.default_folder_id == folder.id
        assert t.default_metadata_structure_id == meta.id

    def test_delete_template(self, api_client, admin):
        t = DocumentTemplate.objects.create(name="Del", created_by=admin)
        api_client.force_authenticate(user=admin)
        r = api_client.delete(f"/api/document-templates/{t.id}/")
        assert r.status_code == status.HTTP_204_NO_CONTENT
        assert not DocumentTemplate.objects.filter(id=t.id).exists()
