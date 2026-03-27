# FASE 35.3 — Copertura archive/views.py (permessi, download, PdD, titolario)
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db.models.fields.files import FieldFile
from rest_framework.test import APIClient

from apps.archive.models import DocumentArchive, InformationPackage
from apps.documents.models import Document, Folder

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin(db):
    u = User.objects.create_user(email="ar353-adm@test.com", password="test", role="ADMIN")
    return u


@pytest.fixture
def approver(db):
    u = User.objects.create_user(email="ar353-ap@test.com", password="test", role="APPROVER")
    return u


@pytest.fixture
def reviewer(db):
    u = User.objects.create_user(email="ar353-rev@test.com", password="test", role="REVIEWER")
    return u


@pytest.fixture
def folder(db, admin):
    return Folder.objects.create(name="ARF", created_by=admin)


@pytest.fixture
def doc_current(db, folder, admin):
    return Document.objects.create(
        title="Arch doc",
        folder=folder,
        created_by=admin,
        owner=admin,
        status=Document.STATUS_APPROVED,
    )


@pytest.mark.django_db
class TestDocumentArchivePermissionsAndActions:
    def test_reviewer_sees_only_own_archive_records(self, client, reviewer, admin, folder):
        own = Document.objects.create(
            title="Mine",
            folder=folder,
            created_by=reviewer,
            owner=reviewer,
            status=Document.STATUS_APPROVED,
        )
        Document.objects.create(
            title="Other",
            folder=folder,
            created_by=admin,
            owner=admin,
            status=Document.STATUS_APPROVED,
        )
        client.force_authenticate(user=reviewer)
        r = client.get("/api/archive/documents/")
        assert r.status_code == 200
        rows = r.json().get("results", r.json())
        doc_ids = {x["document"] for x in rows}
        assert str(own.id) in doc_ids

    def test_stage_query_param(self, client, admin, folder):
        d = Document.objects.create(
            title="Stage filter doc",
            folder=folder,
            created_by=admin,
            owner=admin,
            status=Document.STATUS_APPROVED,
        )
        rec = DocumentArchive.objects.get(document=d)
        assert rec.stage == "current"
        client.force_authenticate(user=admin)
        r = client.get("/api/archive/documents/", {"stage": "current"})
        assert r.status_code == 200
        rows = r.json().get("results", r.json())
        assert any(str(x.get("document")) == str(d.id) for x in rows)

    def test_move_to_deposit_forbidden_and_bad_stage(self, client, reviewer, approver, admin, doc_current):
        rec = DocumentArchive.objects.get(document=doc_current)
        client.force_authenticate(user=reviewer)
        assert client.post(f"/api/archive/documents/{rec.id}/move_to_deposit/", {}).status_code == 403

        client.force_authenticate(user=approver)
        rec.stage = "historical"
        rec.save(update_fields=["stage"])
        assert (
            client.post(f"/api/archive/documents/{rec.id}/move_to_deposit/", {"notes": "x"}, format="json").status_code
            == 400
        )

    def test_move_to_historical_forbidden_and_bad_stage(self, client, approver, admin, doc_current):
        rec = DocumentArchive.objects.get(document=doc_current)
        rec.stage = "current"
        rec.save(update_fields=["stage"])
        client.force_authenticate(user=approver)
        assert client.post(f"/api/archive/documents/{rec.id}/move_to_historical/", {}).status_code == 403

        client.force_authenticate(user=admin)
        assert client.post(f"/api/archive/documents/{rec.id}/move_to_historical/", {}).status_code == 400

    def test_request_and_approve_discard_admin_only(self, client, reviewer, admin, doc_current):
        rec = DocumentArchive.objects.get(document=doc_current)
        client.force_authenticate(user=reviewer)
        assert client.post(f"/api/archive/documents/{rec.id}/request_discard/", {}).status_code == 403
        assert client.post(f"/api/archive/documents/{rec.id}/approve_discard/", {}).status_code == 403

        client.force_authenticate(user=admin)
        assert client.post(f"/api/archive/documents/{rec.id}/request_discard/", {}).status_code == 200
        assert client.post(f"/api/archive/documents/{rec.id}/approve_discard/", {}).status_code == 200
        rec.refresh_from_db()
        assert rec.discard_approved is True


@pytest.mark.django_db
class TestInformationPackageBranches:
    def test_create_pdv_forbidden_and_empty(self, client, reviewer, admin, doc_current):
        client.force_authenticate(user=reviewer)
        r = client.post("/api/archive/packages/create_pdv/", {"document_ids": [str(doc_current.id)]}, format="json")
        assert r.status_code == 403

        client.force_authenticate(user=admin)
        r2 = client.post("/api/archive/packages/create_pdv/", {}, format="json")
        assert r2.status_code == 400

    def test_download_missing_file_returns_404(self, client, admin):
        pkg = InformationPackage.objects.create(
            package_type="PdV",
            package_id="PdV-empty",
            created_by=admin,
            status="draft",
        )
        client.force_authenticate(user=admin)
        r = client.get(f"/api/archive/packages/{pkg.id}/download/")
        assert r.status_code == 404

    def test_download_zip_success(self, client, admin, doc_current):
        client.force_authenticate(user=admin)
        r = client.post(
            "/api/archive/packages/create_pdv/",
            {"document_ids": [str(doc_current.id)]},
            format="json",
        )
        assert r.status_code == 201
        pkg_id = r.json()["id"]
        r2 = client.get(f"/api/archive/packages/{pkg_id}/download/")
        assert r2.status_code == 200
        assert r2["Content-Type"] == "application/zip"

    def test_download_read_oserror_returns_404(self, client, admin, doc_current):
        client.force_authenticate(user=admin)
        r = client.post(
            "/api/archive/packages/create_pdv/",
            {"document_ids": [str(doc_current.id)]},
            format="json",
        )
        pkg_id = r.json()["id"]
        with patch.object(FieldFile, "open", side_effect=OSError("read fail")):
            r2 = client.get(f"/api/archive/packages/{pkg_id}/download/")
        assert r2.status_code == 404

    def test_send_to_conservator_forbidden_for_reviewer(self, client, reviewer, admin, doc_current):
        client.force_authenticate(user=admin)
        r = client.post(
            "/api/archive/packages/create_pdv/",
            {"document_ids": [str(doc_current.id)]},
            format="json",
        )
        pkg_id = r.json()["id"]
        client.force_authenticate(user=reviewer)
        assert client.post(f"/api/archive/packages/{pkg_id}/send_to_conservator/", {}).status_code == 403

    def test_generate_pdd_forbidden_and_ok(self, client, reviewer, admin, doc_current):
        client.force_authenticate(user=admin)
        r = client.post(
            "/api/archive/packages/create_pdv/",
            {"document_ids": [str(doc_current.id)]},
            format="json",
        )
        assert r.status_code == 201
        pkg_id = r.json()["id"]

        client.force_authenticate(user=reviewer)
        assert client.get(f"/api/archive/packages/{pkg_id}/generate_pdd/").status_code == 403

        client.force_authenticate(user=admin)
        r2 = client.get(f"/api/archive/packages/{pkg_id}/generate_pdd/")
        assert r2.status_code == 200
        assert r2["Content-Type"] == "application/zip"


@pytest.mark.django_db
class TestRetentionAndTitolario:
    def test_retention_rules_empty_for_non_admin(self, client, reviewer):
        client.force_authenticate(user=reviewer)
        r = client.get("/api/archive/retention-rules/")
        assert r.status_code == 200
        rows = r.json().get("results", r.json())
        assert rows == []

    def test_retention_rule_update_hits_perform_update(self, client, admin):
        client.force_authenticate(user=admin)
        r = client.post(
            "/api/archive/retention-rules/",
            {
                "classification_code": "AR353-X",
                "classification_label": "Lbl",
                "retention_years": 3,
                "action_after_retention": "discard",
            },
            format="json",
        )
        assert r.status_code == 201
        rid = r.json()["id"]
        r2 = client.patch(f"/api/archive/retention-rules/{rid}/", {"retention_years": 4}, format="json")
        assert r2.status_code == 200
        assert r2.json()["retention_years"] == 4

    def test_titolario_detail_not_found(self, client, admin):
        client.force_authenticate(user=admin)
        r = client.get("/api/archive/titolario/ZZ-NONEXIST-99/")
        assert r.status_code == 404
