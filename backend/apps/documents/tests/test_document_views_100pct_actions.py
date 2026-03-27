# FASE 34 — Azioni DocumentViewSet (workflow, share, allegati, ecc.)
import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.archive.models import RetentionRule
from apps.documents.models import Document, DocumentVersion, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.search.models import DocumentIndex
from apps.workflows.models import WorkflowStep, WorkflowTemplate

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Act OU", code="ACT", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="act100-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="C",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def other_user(db, tenant, ou):
    u = User.objects.create_user(
        email="act100-oth@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="O",
        last_name="T",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def other_client(other_user):
    c = APIClient()
    c.force_authenticate(user=other_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="Act F", tenant=tenant, created_by=admin_user)


def _doc_file(admin_user, folder, **kwargs):
    defaults = dict(
        title="Act doc",
        tenant=folder.tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
        current_version=1,
        status=Document.STATUS_DRAFT,
    )
    defaults.update(kwargs)
    doc = Document.objects.create(**defaults)
    v = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        file_name="a.pdf",
        is_current=True,
        created_by=admin_user,
        file_type="application/pdf",
    )
    v.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF-1.4", content_type="application/pdf"), save=True)
    return doc


@pytest.mark.django_db
class TestMyFilesTreeAndClassify:
    def test_my_files_tree(self, admin_client, admin_user, folder):
        _doc_file(admin_user, folder, title="Tree1", owner=admin_user)
        r = admin_client.get("/api/documents/my_files_tree/")
        assert r.status_code == 200
        assert "personal" in r.json()

    def test_classify_uses_index_and_enriches(self, admin_client, admin_user, folder, tenant):
        doc = _doc_file(admin_user, folder, extracted_text="")
        DocumentIndex.objects.create(document=doc, content="x" * 20)
        WorkflowTemplate.objects.create(
            tenant=tenant,
            name="approval workflow x",
            is_published=True,
            is_deleted=False,
            created_by=admin_user,
        )
        RetentionRule.objects.create(
            classification_code="CL99",
            classification_label="Lbl",
            retention_years=5,
            is_active=True,
        )
        with patch(
            "apps.documents.classification_service.DocumentClassificationService.classify",
            return_value={
                "workflow_suggestion": "approval_workflow",
                "classification_suggestion": "CL99",
            },
        ):
            r = admin_client.get(f"/api/documents/{doc.id}/classify/")
        assert r.status_code == 200
        assert "workflow_template" in r.json() or r.json().get("classification")

    def test_classify_short_text_400(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder, extracted_text="short")
        r = admin_client.get(f"/api/documents/{doc.id}/classify/")
        assert r.status_code == 400

    def test_viewer_info_no_version_404(self, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="Nov",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=2,
        )
        r = admin_client.get(f"/api/documents/{doc.id}/viewer_info/")
        assert r.status_code == 404


@pytest.mark.django_db
class TestVisibilityUploadDownloadLock:
    def test_visibility_protocolled_and_invalid(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        Document.objects.filter(pk=doc.pk).update(is_protocolled=True)
        assert (
            admin_client.patch(f"/api/documents/{doc.id}/visibility/", {"visibility": "office"}, format="json").status_code
            == 400
        )
        Document.objects.filter(pk=doc.pk).update(is_protocolled=False)
        assert (
            admin_client.patch(f"/api/documents/{doc.id}/visibility/", {"visibility": "invalid"}, format="json").status_code
            == 400
        )
        assert (
            admin_client.patch(f"/api/documents/{doc.id}/visibility/", {"visibility": "shared"}, format="json").status_code
            == 200
        )

    @patch("apps.documents.tasks.process_uploaded_file.delay")
    def test_upload_version_locked_conflict(self, mock_delay, admin_client, admin_user, other_user, folder):
        doc = _doc_file(admin_user, folder)
        doc.locked_by = other_user
        doc.save(update_fields=["locked_by"])
        f = SimpleUploadedFile("b.pdf", b"%PDF", content_type="application/pdf")
        r = admin_client.post(f"/api/documents/{doc.id}/upload_version/", {"file": f}, format="multipart")
        assert r.status_code == status.HTTP_409_CONFLICT

    @patch("apps.documents.tasks.process_uploaded_file.delay")
    def test_upload_version_ok(self, mock_delay, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        f = SimpleUploadedFile("b.pdf", b"%PDF-1.4", content_type="application/pdf")
        r = admin_client.post(f"/api/documents/{doc.id}/upload_version/", {"file": f}, format="multipart")
        assert r.status_code == status.HTTP_201_CREATED

    def test_download_version_bad_param_falls_back(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        r = admin_client.get(f"/api/documents/{doc.id}/download/", {"version": "nope"})
        assert r.status_code == 200

    def test_download_open_error(self, admin_client, admin_user, folder, monkeypatch):
        from django.db.models.fields.files import FieldFile

        doc = Document.objects.create(
            title="DLOpen",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="dl_open_fail.pdf",
            is_current=True,
            created_by=admin_user,
            file_type="application/pdf",
        )
        v.file.save(
            "dl_open_fail.pdf",
            SimpleUploadedFile("dl_open_fail.pdf", b"%PDF-1.4", content_type="application/pdf"),
            save=True,
        )
        real_open = FieldFile.open

        def _open(self, mode="rb"):
            if "dl_open_fail" in (getattr(self, "name", "") or ""):
                raise OSError("x")
            return real_open(self, mode)

        monkeypatch.setattr(FieldFile, "open", _open)
        r = admin_client.get(f"/api/documents/{doc.id}/download/")
        assert r.status_code == 404

    def test_versions_list(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        r = admin_client.get(f"/api/documents/{doc.id}/versions/")
        assert r.status_code == 200

    def test_lock_unlock(self, admin_client, admin_user, other_client, other_user, folder):
        doc = _doc_file(
            admin_user,
            folder,
            visibility=Document.VISIBILITY_OFFICE,
            owner=admin_user,
        )
        assert admin_client.post(f"/api/documents/{doc.id}/lock/").status_code == 200
        assert other_client.post(f"/api/documents/{doc.id}/lock/").status_code == 400
        assert other_client.post(f"/api/documents/{doc.id}/unlock/").status_code == 403
        assert admin_client.post(f"/api/documents/{doc.id}/unlock/").status_code == 200


@pytest.mark.django_db
class TestCopyMetadataProtocollo:
    @patch("apps.documents.views.File")
    def test_copy_file_error_500(self, mock_file_cls, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        mock_file_cls.side_effect = OSError("read fail")
        r = admin_client.post(f"/api/documents/{doc.id}/copy/", {}, format="json")
        assert r.status_code == 500

    def test_copy_ok(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        r = admin_client.post(f"/api/documents/{doc.id}/copy/", {"new_title": "Copy1"}, format="json")
        assert r.status_code == 201

    def test_update_metadata_forbidden_and_ok(self, admin_client, admin_user, other_client, folder):
        doc = _doc_file(admin_user, folder)
        assert other_client.patch(f"/api/documents/{doc.id}/metadata/", {"metadata_values": {}}, format="json").status_code in (
            403,
            404,
        )
        assert (
            admin_client.patch(f"/api/documents/{doc.id}/metadata/", {"metadata_values": {"k": "v"}}, format="json").status_code
            == 200
        )

    def test_protocollo_validation(self, admin_client, admin_user, folder, ou):
        doc = _doc_file(admin_user, folder)
        assert (
            admin_client.post(f"/api/documents/{doc.id}/protocollo/", {}, format="json").status_code
            == status.HTTP_400_BAD_REQUEST
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc.id}/protocollo/",
                {"organizational_unit_id": str(uuid.uuid4()), "subject": "S"},
                format="json",
            ).status_code
            == 400
        )
        r = admin_client.post(
            f"/api/documents/{doc.id}/protocollo/",
            {"organizational_unit_id": str(ou.id), "subject": "Out doc"},
            format="json",
        )
        assert r.status_code == 201


@pytest.mark.django_db
class TestWorkflowActions:
    def _template_with_steps(self, tenant, admin_user, n_steps=1):
        wt = WorkflowTemplate.objects.create(
            tenant=tenant,
            name="WF Act",
            is_published=True,
            is_deleted=False,
            created_by=admin_user,
        )
        for i in range(n_steps):
            WorkflowStep.objects.create(
                template=wt,
                name=f"S{i}",
                order=i,
                action="approve",
                assignee_type="specific_user",
                assignee_user=admin_user,
                deadline_days=1 if i == 0 else None,
            )
        return wt

    @patch("apps.notifications.services.NotificationService.notify_workflow_assigned")
    @patch("apps.notifications.services.NotificationService.notify_workflow_completed")
    def test_start_workflow_approve_complete(self, mock_done, mock_asg, admin_client, admin_user, folder, tenant):
        doc = _doc_file(admin_user, folder, status=Document.STATUS_DRAFT)
        wt = self._template_with_steps(tenant, admin_user, n_steps=1)
        r = admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        assert r.status_code == 201
        r2 = admin_client.post(
            f"/api/documents/{doc.id}/workflow_action/",
            {"action": "approve", "comment": ""},
            format="json",
        )
        assert r2.status_code == 200

    @patch("apps.notifications.services.NotificationService.notify_workflow_assigned")
    def test_workflow_two_steps_advance(self, mock_asg, admin_client, admin_user, folder, tenant):
        doc = _doc_file(admin_user, folder, status=Document.STATUS_DRAFT)
        wt = self._template_with_steps(tenant, admin_user, n_steps=2)
        admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        r = admin_client.post(
            f"/api/documents/{doc.id}/workflow_action/",
            {"action": "approve", "comment": ""},
            format="json",
        )
        assert r.status_code == 200
        detail = r.json().get("detail", "")
        assert "Prossimo" in detail or "step" in detail.lower()

    def test_workflow_reject_and_request_changes(self, admin_client, admin_user, folder, tenant):
        doc = _doc_file(admin_user, folder, status=Document.STATUS_DRAFT)
        wt = self._template_with_steps(tenant, admin_user, 1)
        admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        assert (
            admin_client.post(
                f"/api/documents/{doc.id}/workflow_action/",
                {"action": "reject", "comment": ""},
                format="json",
            ).status_code
            == 400
        )
        rj = admin_client.post(
            f"/api/documents/{doc.id}/workflow_action/",
            {"action": "reject", "comment": "no"},
            format="json",
        )
        assert rj.status_code == 200

        doc2 = _doc_file(admin_user, folder, title="W2", status=Document.STATUS_DRAFT)
        admin_client.post(f"/api/documents/{doc2.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        rc = admin_client.post(
            f"/api/documents/{doc2.id}/workflow_action/",
            {"action": "request_changes", "comment": "fix"},
            format="json",
        )
        assert rc.status_code == 200

    def test_workflow_history(self, admin_client, admin_user, folder, tenant):
        doc = _doc_file(admin_user, folder, status=Document.STATUS_DRAFT)
        wt = self._template_with_steps(tenant, admin_user, 1)
        admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        r = admin_client.get(f"/api/documents/{doc.id}/workflow_history/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestSignatureShareAttachments:
    @patch("apps.signatures.services.SignatureService.request")
    def test_request_signature_approved(self, mock_req, admin_client, admin_user, folder, other_user):
        mock_req.return_value = (MagicMock(id=uuid.uuid4()), "otp")
        doc = _doc_file(admin_user, folder, status=Document.STATUS_APPROVED)
        r = admin_client.post(
            f"/api/documents/{doc.id}/request_signature/",
            {"signer_id": str(other_user.id), "format": "pades_invisible"},
            format="json",
        )
        assert r.status_code == 201

    def test_signatures_list(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        r = admin_client.get(f"/api/documents/{doc.id}/signatures/")
        assert r.status_code == 200

    def test_share_and_shares_forbidden(self, admin_client, other_client, admin_user, other_user, folder):
        doc = _doc_file(
            admin_user,
            folder,
            owner=admin_user,
            visibility=Document.VISIBILITY_OFFICE,
        )
        r = admin_client.post(
            f"/api/documents/{doc.id}/share/",
            {
                "recipient_type": "external",
                "recipient_email": "e@ex.com",
                "can_download": True,
                "expires_in_days": 1,
            },
            format="json",
        )
        assert r.status_code == 201
        assert other_client.get(f"/api/documents/{doc.id}/shares/").status_code == 403

    def test_chat_and_move(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        assert admin_client.post(f"/api/documents/{doc.id}/chat/", {}, format="json").status_code == 200
        f2 = Folder.objects.create(name="Sub", tenant=folder.tenant, created_by=admin_user)
        assert (
            admin_client.patch(f"/api/documents/{doc.id}/move/", {"folder_id": str(f2.id)}, format="json").status_code == 200
        )

    def test_attachments_crud(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        r = admin_client.get(f"/api/documents/{doc.id}/attachments/")
        assert r.status_code == 200
        up = SimpleUploadedFile("att.txt", b"hi", content_type="text/plain")
        r2 = admin_client.post(f"/api/documents/{doc.id}/attachments/", {"file": up}, format="multipart")
        assert r2.status_code == 201
        att_id = r2.json()["id"]
        assert admin_client.get(f"/api/documents/{doc.id}/attachments/{att_id}/download/").status_code == 200
        assert admin_client.delete(f"/api/documents/{doc.id}/attachments/{att_id}/").status_code == 204


@pytest.mark.django_db
class TestEncryptDecryptAdmin:
    @patch("apps.documents.views.DocumentEncryption.encrypt_file")
    def test_encrypt_ok(self, mock_enc, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        fd, path = tempfile.mkstemp(suffix=".enc")
        os.write(fd, b"cipher")
        os.close(fd)
        mock_enc.return_value = (path, "saltb64")
        r = admin_client.post(f"/api/documents/{doc.id}/encrypt/", {"password": "abcdefgh"}, format="json")
        assert r.status_code == 200
        if os.path.isfile(path):
            os.unlink(path)

    @patch("apps.documents.views.DocumentEncryption.decrypt_file", return_value=b"plain-bytes")
    def test_decrypt_download_ok(self, mock_dec, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        v = doc.versions.get(version_number=1)
        v.is_encrypted = True
        v.save(update_fields=["is_encrypted"])
        r = admin_client.post(f"/api/documents/{doc.id}/decrypt_download/", {"password": "abcdefgh"}, format="json")
        assert r.status_code == 200


@pytest.mark.django_db
class TestCreateUpdateDestroyBranches:
    def test_create_missing_file(self, admin_client):
        assert admin_client.post("/api/documents/", {"title": "X"}, format="json").status_code == 400

    def test_update_protocolled(self, admin_client, admin_user, folder):
        doc = _doc_file(admin_user, folder)
        Document.objects.filter(pk=doc.pk).update(is_protocolled=True)
        assert admin_client.patch(f"/api/documents/{doc.id}/", {"title": "Y"}, format="json").status_code == 400

    def test_destroy_other_forbidden(self, other_client, admin_user, folder):
        doc = _doc_file(
            admin_user,
            folder,
            owner=admin_user,
            created_by=admin_user,
            visibility=Document.VISIBILITY_OFFICE,
        )
        assert other_client.delete(f"/api/documents/{doc.id}/").status_code == 403
