# FASE 35.3 — Copertura search/views.py (filtri, ordinamento, snippet, facet)

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder
from apps.search.models import DocumentIndex

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="s353@test.com", password="test")


@pytest.fixture
def folder(db):
    return Folder.objects.create(name="S353")


@pytest.mark.django_db
class TestSearchViewBranches:
    def test_non_document_type_returns_empty(self, api_client, user, folder):
        doc = Document.objects.create(
            title="Alpha unique S353",
            folder=folder,
            created_by=user,
            status=Document.STATUS_DRAFT,
            metadata_values={"city": "Milano"},
        )
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "Alpha", "type": "folders"})
        assert r.status_code == 200
        data = r.json()
        assert data["results"] == []
        assert data["total_count"] == 0

    def test_page_clamped_and_folder_metadata_status_filters(self, api_client, user, folder):
        doc = Document.objects.create(
            title="Beta S353",
            folder=folder,
            created_by=user,
            status=Document.STATUS_DRAFT,
            metadata_values={"ref_code": "REF99"},
        )
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "", "page": "0", "folder_id": str(folder.id)})
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

        r2 = api_client.get(
            "/api/search/",
            {
                "q": "Beta",
                "status": Document.STATUS_DRAFT,
                "created_by": str(user.id),
                "date_from": "2000-01-01",
                "date_to": "2099-12-31",
                "metadata_ref_code": "REF99",
            },
        )
        assert r2.status_code == 200
        assert r2.json()["total_count"] >= 1

    def test_metadata_structure_id_and_order_by_title(self, api_client, user, folder):
        from apps.metadata.models import MetadataStructure

        ms = MetadataStructure.objects.create(name="S353 Meta Structure XYZ")
        doc = Document.objects.create(
            title="Zeta S353",
            folder=folder,
            created_by=user,
            status=Document.STATUS_DRAFT,
            metadata_structure=ms,
        )
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "Zeta", "metadata_structure_id": str(ms.id), "order_by": "title"})
        assert r.status_code == 200
        assert any(x["id"] == str(doc.id) for x in r.json()["results"])

    def test_order_by_relevance_and_invalid_fallback(self, api_client, user, folder):
        Document.objects.create(
            title="Gamma S353 relevance",
            folder=folder,
            created_by=user,
            status=Document.STATUS_DRAFT,
        )
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "Gamma", "order_by": "relevance"})
        assert r.status_code == 200
        r2 = api_client.get("/api/search/", {"q": "Gamma", "order_by": "not-a-valid-field"})
        assert r2.status_code == 200

    def test_snippet_from_index_and_title(self, api_client, user, folder):
        doc = Document.objects.create(
            title="Delta S353 titlehit",
            description="Desc body",
            folder=folder,
            created_by=user,
            status=Document.STATUS_DRAFT,
        )
        DocumentIndex.objects.create(document=doc, content="long text " * 30 + "needleS353" + " tail " * 30)
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": "needleS353"})
        assert r.status_code == 200
        rows = r.json()["results"]
        assert any("needleS353" in (x.get("snippet") or "") for x in rows)

        r2 = api_client.get("/api/search/", {"q": "titlehit"})
        assert r2.status_code == 200
        rows2 = r2.json()["results"]
        assert any(x.get("title") and "titlehit" in x["title"] for x in rows2)

    def test_empty_query_uses_description_snippet_and_facets(self, api_client, user, folder):
        Document.objects.create(
            title="Epsilon S353",
            description="D" * 400,
            folder=folder,
            created_by=user,
            status=Document.STATUS_DRAFT,
        )
        api_client.force_authenticate(user=user)
        r = api_client.get("/api/search/", {"q": ""})
        assert r.status_code == 200
        data = r.json()
        assert "status" in data.get("facets", {})
        assert any("Epsilon" in (x.get("title") or "") for x in data["results"])

    def test_facets_block_swallows_query_exception(self, api_client, user, folder):
        Document.objects.create(
            title="FacetFail S353",
            folder=folder,
            created_by=user,
            status=Document.STATUS_DRAFT,
        )
        api_client.force_authenticate(user=user)
        _orig_values = QuerySet.values

        def _values(self, *fields, **kwargs):
            if fields == ("status",):
                raise RuntimeError("facet query boom")
            return _orig_values(self, *fields, **kwargs)

        with patch.object(QuerySet, "values", _values):
            r = api_client.get("/api/search/", {"q": ""})
        assert r.status_code == 200
        assert r.json().get("facets") == {}
