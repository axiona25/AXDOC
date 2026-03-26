"""
Test API ricerca FASE 12.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.documents.models import Document, Folder
from apps.search.models import DocumentIndex

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="searchuser@test.com", password="test")


@pytest.fixture
def doc(user, db):
    f = Folder.objects.create(name="F")
    return Document.objects.create(
        title="Contratto Acme 2024",
        folder=f,
        created_by=user,
        status=Document.STATUS_DRAFT,
    )


@pytest.mark.django_db
class TestSearchAPI:
    def test_search_by_title(self, api_client, user, doc):
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "Contratto"})
        assert r.status_code == 200
        data = r.json()
        assert data["total_count"] >= 1
        assert any(x["title"] == "Contratto Acme 2024" for x in data["results"])

    def test_search_fulltext_after_index(self, api_client, user, doc):
        DocumentIndex.objects.create(document=doc, content="report annuale vendite 2024")
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "vendite"})
        assert r.status_code == 200
        data = r.json()
        assert data["total_count"] >= 1
        assert any(x["id"] == str(doc.id) for x in data["results"])

    def test_search_no_permission_other_user_docs(self, api_client, user, doc):
        other = User.objects.create_user(email="other@test.com", password="test")
        doc.created_by = other
        doc.save()
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "Contratto"})
        assert r.status_code == 200
        data = r.json()
        assert not any(x["id"] == str(doc.id) for x in data["results"])

    def test_search_empty_query_returns_accessible_docs(self, api_client, user, doc):
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": ""})
        assert r.status_code == 200
        data = r.json()
        assert data["total_count"] >= 1
        assert any(x["id"] == str(doc.id) for x in data["results"])
