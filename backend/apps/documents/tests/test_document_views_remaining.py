# FASE 34B — Copertura righe residue documents/views.py (≥95%)
import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.documents.models import (
    Document,
    DocumentAttachment,
    DocumentPermission,
    DocumentTemplate,
    DocumentVersion,
    Folder,
)
from apps.documents.views import DocumentViewSet, DocumentTemplateViewSet, _documents_export_queryset
from apps.metadata.models import MetadataField, MetadataStructure
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.workflows.models import WorkflowStep, WorkflowTemplate

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="DocR OU", code="DRU", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="docrem-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="D",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(
        email="docrem-op@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="O",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def approver_user(db, tenant, ou):
    u = User.objects.create_user(
        email="docrem-ap@test.com",
        password="Appr123!",
        role="APPROVER",
        first_name="A",
        last_name="P",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="APPROVER")
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def operator_client(operator_user):
    c = APIClient()
    c.force_authenticate(user=operator_user)
    return c


@pytest.fixture
def approver_client(approver_user):
    c = APIClient()
    c.force_authenticate(user=approver_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="DocR F", tenant=tenant, created_by=admin_user)


@pytest.mark.django_db
class TestDocViewsExportAndListFilters:
    # Copre righe: 51, 60, 66, 149, 164
    def test_export_and_list_query_filters(self, admin_user, folder, admin_client):
        ms = MetadataStructure.objects.create(
            name=f"dm-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
        )
        Document.objects.create(
            title="Filt",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            metadata_structure=ms,
        )
        factory = APIRequestFactory()
        wsgi = factory.get(
            f"/api/documents/export_excel/?folder_id={folder.id}&created_by={admin_user.id}"
            f"&metadata_structure_id={ms.id}&title=Filt"
        )
        force_authenticate(wsgi, user=admin_user)
        request = Request(wsgi)
        view = DocumentViewSet()
        view.request = request
        view.action = "list"
        qs = _documents_export_queryset(view, request)
        assert qs.exists()
        r = admin_client.get(
            "/api/documents/",
            {"folder_id": str(folder.id), "created_by": str(admin_user.id), "metadata_structure_id": str(ms.id)},
        )
        assert r.status_code == 200


@pytest.mark.django_db
class TestDocViewsBulkAndOperator:
    # Copre righe: 237, 252, 258-259, 263, 278-279
    def test_operator_bulk_and_invalid_status(self, admin_client, operator_client, admin_user, operator_user, folder):
        d_op = Document.objects.create(
            title="OpB",
            tenant=folder.tenant,
            folder=folder,
            created_by=operator_user,
            owner=operator_user,
        )
        d_ad = Document.objects.create(
            title="AdB",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        operator_client.post(
            "/api/documents/bulk_delete/",
            {"document_ids": [str(d_op.id), str(d_ad.id)]},
            format="json",
        )
        d_ad.refresh_from_db()
        assert d_ad.is_deleted is False
        operator_client.post(
            "/api/documents/bulk_move/",
            {"document_ids": [str(d_op.id)], "folder_id": None},
            format="json",
        )
        assert operator_client.post(
            "/api/documents/bulk_status/",
            {"document_ids": [str(d_op.id)], "status": Document.STATUS_DRAFT},
            format="json",
        ).status_code == status.HTTP_403_FORBIDDEN
        assert (
            admin_client.post(
                "/api/documents/bulk_status/",
                {"document_ids": [str(d_ad.id)], "status": "NOT_A_STATUS"},
                format="json",
            ).status_code
            == 400
        )


@pytest.mark.django_db
class TestDocViewsCreateBranches:
    # Copre righe: 297-298, 301-305, 307-310, 316, 364-365, 371-372, 388-389, 394-396, 412
    @patch("apps.documents.tasks.process_uploaded_file.delay")
    def test_create_metadata_and_p7m_and_permissions(self, mock_delay, admin_client, admin_user, folder, operator_user, ou):
        ms = MetadataStructure.objects.create(
            name=f"dc-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
        )
        MetadataField.objects.create(
            structure=ms, name="f1", label="F", field_type="text", is_required=True, order=0
        )
        f_bad = SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf")
        assert (
            admin_client.post(
                "/api/documents/",
                {
                    "file": f_bad,
                    "metadata_structure_id": str(ms.id),
                    "metadata_values": "{}",
                },
                format="multipart",
            ).status_code
            == 400
        )
        f2 = SimpleUploadedFile("b.pdf", b"%PDF", content_type="application/pdf")
        assert (
            admin_client.post(
                "/api/documents/",
                {
                    "file": f2,
                    "metadata_structure_id": str(ms.id),
                    "metadata_values": '{"f1": "ok", "bad": "json"',
                },
                format="multipart",
            ).status_code
            == 400
        )
        f3 = SimpleUploadedFile("c.pdf", b"%PDF", content_type="application/pdf")
        r3 = admin_client.post(
            "/api/documents/",
            {
                "file": f3,
                "visibility": "not_valid",
                "allowed_users": "not-json{",
                "allowed_ous": "also-bad",
            },
            format="multipart",
        )
        assert r3.status_code == 201
        f4 = SimpleUploadedFile("d.pdf", b"%PDF", content_type="application/pdf")
        r4 = admin_client.post(
            "/api/documents/",
            {
                "file": f4,
                "allowed_users": "123",
                "allowed_ous": "456",
            },
            format="multipart",
        )
        assert r4.status_code == 201
        MetadataStructure.objects.create(
            name=f"req-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
        )
        f5 = SimpleUploadedFile("e.pdf", b"%PDF", content_type="application/pdf")
        r5 = admin_client.post(
            "/api/documents/",
            {
                "file": f5,
                "allowed_users": f'["{operator_user.id}"]',
                "allowed_ous": f'["{ou.id}"]',
            },
            format="multipart",
        )
        assert r5.status_code == 201
        with patch("apps.signatures.verification.verify_p7m", side_effect=RuntimeError("x")):
            fp = SimpleUploadedFile("x.p7m", b"x", content_type="application/pkcs7-mime")
            admin_client.post("/api/documents/", {"file": fp}, format="multipart")


@pytest.mark.django_db
class TestDocViewsUpdateDestroy:
    # Copre righe: 423-442, 449-451
    def test_update_destroy_branches(self, admin_client, operator_client, admin_user, operator_user, folder):
        doc = Document.objects.create(
            title="Upd",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            is_protocolled=True,
        )
        assert admin_client.patch(f"/api/documents/{doc.id}/", {"title": "X"}, format="json").status_code == 400
        Document.objects.filter(pk=doc.pk).update(is_protocolled=False)
        DocumentPermission.objects.create(
            document=doc, user=operator_user, can_read=True, can_write=True, can_delete=False
        )
        doc.locked_by = admin_user
        doc.save(update_fields=["locked_by"])
        assert operator_client.patch(f"/api/documents/{doc.id}/", {"title": "Y"}, format="json").status_code == 409
        doc.locked_by = None
        doc.save(update_fields=["locked_by"])
        doc_nop = Document.objects.create(
            title="NoPerm",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        DocumentPermission.objects.create(
            document=doc_nop, user=operator_user, can_read=True, can_write=False, can_delete=False
        )
        assert operator_client.patch(f"/api/documents/{doc_nop.id}/", {"title": "Z"}, format="json").status_code == 403
        ms = MetadataStructure.objects.create(
            name=f"du-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
        )
        MetadataField.objects.create(
            structure=ms, name="k", label="K", field_type="text", is_required=True, order=0
        )
        doc2 = Document.objects.create(
            title="M2",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            metadata_structure=ms,
        )
        assert (
            admin_client.patch(f"/api/documents/{doc2.id}/", {"metadata_values": {}}, format="json").status_code == 400
        )
        doc3 = Document.objects.create(
            title="Del",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        DocumentPermission.objects.create(
            document=doc3, user=operator_user, can_read=True, can_write=False, can_delete=True
        )
        assert operator_client.delete(f"/api/documents/{doc3.id}/").status_code == 204


@pytest.mark.django_db
class TestDocViewsOcrPreviewWorkflow:
    # Copre righe: 532
    def test_run_ocr_no_file(self, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="OCR",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            is_current=True,
            created_by=admin_user,
        )
        assert admin_client.post(f"/api/documents/{doc.id}/run_ocr/").status_code == 400

    # Copre righe: 661-662, 676, 678, 712-727, 751-756, 765-766, 792-797, 806-807, 822-823, 825-832
    def test_preview_branches(self, admin_client, admin_user, folder, tmp_path):
        def _doc_preview(fname, content, ftype):
            doc = Document.objects.create(
                title="Prv",
                tenant=folder.tenant,
                folder=folder,
                created_by=admin_user,
                owner=admin_user,
                current_version=1,
            )
            v = DocumentVersion.objects.create(
                document=doc,
                version_number=1,
                file_name=fname,
                file_type=ftype,
                is_current=True,
                created_by=admin_user,
            )
            v.file.save(fname, SimpleUploadedFile(fname, content, content_type=ftype), save=True)
            return doc

        calls = {"n": 0}

        def _unlink(path, *a, **k):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("x")
            return None

        doc_eml = _doc_preview("m.eml", b"From: a\n\nb", "message/rfc822")
        with patch("apps.documents.views.os.unlink", _unlink):
            with patch("apps.documents.viewer.get_viewer_type", return_value="email"):
                with patch("apps.documents.viewer.parse_eml", return_value={"from": "a"}):
                    assert admin_client.get(f"/api/documents/{doc_eml.id}/preview/").status_code == 200
        doc_html = _doc_preview("h.html", b"<p>x</p>", "text/html")
        with patch("apps.documents.viewer.get_viewer_type", return_value="text"):
            r = admin_client.get(f"/api/documents/{doc_html.id}/preview/")
            assert r.status_code == 200
            assert r.json().get("language") == "xml"
        doc_csv = _doc_preview("d.csv", b"a,b", "text/csv")
        with patch("apps.documents.viewer.get_viewer_type", return_value="text"):
            r2 = admin_client.get(f"/api/documents/{doc_csv.id}/preview/")
            assert r2.json().get("language") == "csv"
        pdf = tmp_path / "conv.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc_off = _doc_preview("w.docx", b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        def _conv(p):
            d = tmp_path / "lo"
            d.mkdir()
            (d / "a.pdf").write_bytes(b"%PDF")
            (d / "b.extra").write_bytes(b"x")
            return str(d / "a.pdf")

        with patch("apps.documents.viewer.convert_office_to_pdf", side_effect=_conv):
            assert admin_client.get(f"/api/documents/{doc_off.id}/preview/").status_code == 200
        doc_bmp = _doc_preview("i.bmp", b"BMP", "image/bmp")
        outp = tmp_path / "out.png"
        outp.write_bytes(b"\x89PNG\r\n\x1a\n")
        with patch("apps.documents.viewer.convert_image_to_web", return_value=(str(outp), "image/png")):
            assert admin_client.get(f"/api/documents/{doc_bmp.id}/preview/").status_code == 200
        with patch("apps.documents.viewer.convert_image_to_web", side_effect=OSError("u")):
            assert admin_client.get(f"/api/documents/{doc_bmp.id}/preview/").status_code == 500
        doc_mov = _doc_preview("v.mov", b"m", "video/quicktime")
        mp4 = tmp_path / "x.mp4"
        mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        with patch("apps.documents.viewer.convert_video_to_mp4", return_value=str(mp4)):
            assert admin_client.get(f"/api/documents/{doc_mov.id}/preview/").status_code == 200
        with patch("apps.documents.viewer.convert_video_to_mp4", side_effect=OSError("v")):
            assert admin_client.get(f"/api/documents/{doc_mov.id}/preview/").status_code == 500
        doc_mp3 = _doc_preview("s.mp3", b"\xff\xfb", "audio/mpeg")
        ver_mp3_pk = doc_mp3.versions.filter(is_current=True).values_list("pk", flat=True).first()
        _real_ff_open = FieldFile.open

        def _open_audio(self, mode="rb"):
            inst = getattr(self, "instance", None)
            if getattr(inst, "pk", None) == ver_mp3_pk:
                raise OSError("e")
            return _real_ff_open(self, mode)

        with patch.object(FieldFile, "open", _open_audio):
            assert admin_client.get(f"/api/documents/{doc_mp3.id}/preview/").status_code == 404
        doc_fb = _doc_preview("z.zz", b"x", "application/octet-stream")
        with patch("apps.documents.viewer.get_viewer_type", return_value="fallback_type"):
            assert admin_client.get(f"/api/documents/{doc_fb.id}/preview/").status_code == 200


@pytest.mark.django_db
class TestDocViewsUploadDownloadCopyMeta:
    # Copre righe: 856-860, 867-868, 916, 969-972, 1006-1017, 1030, 1053, 1059
    @patch("apps.documents.tasks.process_uploaded_file.delay")
    def test_upload_version_protocolled_and_no_file(self, mock_d, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="UV",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            is_protocolled=True,
            current_version=1,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        assert admin_client.post(f"/api/documents/{doc.id}/upload_version/", {}).status_code == 400
        Document.objects.filter(pk=doc.pk).update(is_protocolled=False)
        assert admin_client.post(f"/api/documents/{doc.id}/upload_version/", {}).status_code == 400

    def test_download_version_missing(self, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="DL",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=5,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        assert admin_client.get(f"/api/documents/{doc.id}/download/", {"version": "99"}).status_code == 404

    def test_copy_no_file(self, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="Cp",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        assert admin_client.post(f"/api/documents/{doc.id}/copy/", {}, format="json").status_code == 400

    def test_patch_metadata_branches(self, admin_client, operator_client, admin_user, operator_user, folder):
        doc = Document.objects.create(
            title="MD",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        DocumentPermission.objects.create(
            document=doc, user=operator_user, can_read=True, can_write=True, can_delete=False
        )
        doc.locked_by = admin_user
        doc.save(update_fields=["locked_by"])
        assert (
            operator_client.patch(f"/api/documents/{doc.id}/metadata/", {"metadata_values": {}}, format="json").status_code
            == 409
        )
        doc.locked_by = None
        doc.save(update_fields=["locked_by"])
        doc_np = Document.objects.create(
            title="MD0",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        DocumentPermission.objects.create(
            document=doc_np, user=operator_user, can_read=True, can_write=False, can_delete=False
        )
        assert (
            operator_client.patch(f"/api/documents/{doc_np.id}/metadata/", {"metadata_values": {}}, format="json").status_code
            == 403
        )
        assert (
            admin_client.patch(f"/api/documents/{doc.id}/metadata/", {}, format="json").status_code == 400
        )
        ms = MetadataStructure.objects.create(
            name=f"pm-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
        )
        MetadataField.objects.create(
            structure=ms, name="r", label="R", field_type="text", is_required=True, order=0
        )
        doc2 = Document.objects.create(
            title="MD2",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            metadata_structure=ms,
        )
        assert (
            admin_client.patch(f"/api/documents/{doc2.id}/metadata/", {"metadata_values": {}}, format="json").status_code
            == 400
        )

    def test_protocollo_branches(self, admin_client, operator_client, admin_user, operator_user, ou, folder):
        doc = Document.objects.create(
            title="",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            is_protocolled=True,
        )
        assert (
            admin_client.post(f"/api/documents/{doc.id}/protocollo/", {"organizational_unit_id": str(ou.id)}).status_code
            == 400
        )
        Document.objects.filter(pk=doc.pk).update(is_protocolled=False, title="T")
        assert admin_client.post(f"/api/documents/{doc.id}/protocollo/", {}, format="json").status_code == 400
        ou2 = OrganizationalUnit.objects.create(name="P2", code="P2", tenant=ou.tenant)
        doc_op = Document.objects.create(
            title="Proto",
            tenant=folder.tenant,
            folder=folder,
            created_by=operator_user,
            owner=operator_user,
        )
        assert (
            operator_client.post(
                f"/api/documents/{doc_op.id}/protocollo/",
                {"organizational_unit_id": str(ou2.id), "subject": "S"},
                format="json",
            ).status_code
            == 403
        )
        doc_op2 = Document.objects.create(
            title="",
            tenant=folder.tenant,
            folder=folder,
            created_by=operator_user,
            owner=operator_user,
        )
        assert (
            operator_client.post(
                f"/api/documents/{doc_op2.id}/protocollo/",
                {"organizational_unit_id": str(ou.id), "subject": "  "},
                format="json",
            ).status_code
            == 400
        )


@pytest.mark.django_db
class TestDocViewsWorkflowSignatureConservation:
    # Copre righe: 1098-1114, 1143-1144, 1157-1225
    @patch("apps.notifications.services.NotificationService.notify_workflow_assigned", side_effect=RuntimeError("x"))
    @patch("apps.notifications.services.NotificationService.notify_workflow_completed", side_effect=RuntimeError("x"))
    @patch("apps.notifications.services.NotificationService.notify_workflow_rejected", side_effect=RuntimeError("x"))
    @patch("apps.notifications.services.NotificationService.notify_changes_requested", side_effect=RuntimeError("x"))
    def test_workflow_full(self, mock_nc, mock_nr, mock_nw, mock_na, admin_client, operator_client, admin_user, operator_user, folder, tenant):
        doc = Document.objects.create(
            title="WF",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        assert operator_client.post(f"/api/documents/{doc.id}/start_workflow/", {}).status_code in (403, 404)
        assert admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {}).status_code == 400
        doc_idle = Document.objects.create(
            title="Idle",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        assert (
            admin_client.post(f"/api/documents/{doc_idle.id}/workflow_action/", {"action": "approve"}, format="json").status_code
            == 400
        )
        wt0 = WorkflowTemplate.objects.create(
            tenant=tenant, name="Ept", is_published=True, is_deleted=False, created_by=admin_user
        )
        assert admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt0.id)}).status_code == 400
        wt_bad = WorkflowTemplate.objects.create(
            tenant=tenant, name="Unpub", is_published=False, is_deleted=False, created_by=admin_user
        )
        WorkflowStep.objects.create(
            template=wt_bad,
            name="S",
            order=0,
            action="approve",
            assignee_type="specific_user",
            assignee_user=admin_user,
        )
        assert admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt_bad.id)}).status_code == 400
        wt = WorkflowTemplate.objects.create(
            tenant=tenant, name="WFull", is_published=True, is_deleted=False, created_by=admin_user
        )
        WorkflowStep.objects.create(
            template=wt,
            name="A",
            order=0,
            action="approve",
            assignee_type="specific_user",
            assignee_user=admin_user,
            deadline_days=1,
        )
        WorkflowStep.objects.create(
            template=wt,
            name="B",
            order=1,
            action="approve",
            assignee_type="specific_user",
            assignee_user=operator_user,
        )
        r = admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        assert r.status_code == 201
        assert admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(wt.id)}).status_code == 400
        assert admin_client.post(f"/api/documents/{doc.id}/workflow_action/", {"action": "bad"}, format="json").status_code == 400
        assert (
            admin_client.post(f"/api/documents/{doc.id}/workflow_action/", {"action": "reject"}, format="json").status_code == 400
        )
        doc2 = Document.objects.create(
            title="W2",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        admin_client.post(f"/api/documents/{doc2.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        assert (
            admin_client.post(
                f"/api/documents/{doc2.id}/workflow_action/",
                {"action": "reject", "comment": "no"},
                format="json",
            ).status_code
            == 200
        )
        doc3 = Document.objects.create(
            title="W3",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        admin_client.post(f"/api/documents/{doc3.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        assert (
            admin_client.post(
                f"/api/documents/{doc3.id}/workflow_action/",
                {"action": "request_changes", "comment": "fix"},
                format="json",
            ).status_code
            == 200
        )
        wt1 = WorkflowTemplate.objects.create(
            tenant=tenant, name="WOne", is_published=True, is_deleted=False, created_by=admin_user
        )
        WorkflowStep.objects.create(
            template=wt1,
            name="Only",
            order=0,
            action="approve",
            assignee_type="specific_user",
            assignee_user=admin_user,
        )
        doc4 = Document.objects.create(
            title="W4",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        admin_client.post(f"/api/documents/{doc4.id}/start_workflow/", {"template_id": str(wt1.id)}, format="json")
        assert (
            admin_client.post(
                f"/api/documents/{doc4.id}/workflow_action/",
                {"action": "approve", "comment": ""},
                format="json",
            ).status_code
            == 200
        )
        doc5 = Document.objects.create(
            title="W5",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        admin_client.post(f"/api/documents/{doc5.id}/start_workflow/", {"template_id": str(wt.id)}, format="json")
        DocumentPermission.objects.create(
            document=doc5, user=operator_user, can_read=True, can_write=True, can_delete=False
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc5.id}/workflow_action/",
                {"action": "approve", "comment": ""},
                format="json",
            ).status_code
            == 200
        )
        assert (
            operator_client.post(
                f"/api/documents/{doc5.id}/workflow_action/",
                {"action": "approve", "comment": ""},
                format="json",
            ).status_code
            == 200
        )
        doc6 = Document.objects.create(
            title="W6",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        wt_admin_only = WorkflowTemplate.objects.create(
            tenant=tenant, name="WAdm", is_published=True, is_deleted=False, created_by=admin_user
        )
        WorkflowStep.objects.create(
            template=wt_admin_only,
            name="Adm",
            order=0,
            action="approve",
            assignee_type="specific_user",
            assignee_user=admin_user,
        )
        admin_client.post(f"/api/documents/{doc6.id}/start_workflow/", {"template_id": str(wt_admin_only.id)}, format="json")
        DocumentPermission.objects.create(
            document=doc6, user=operator_user, can_read=True, can_write=True, can_delete=False
        )
        assert (
            operator_client.post(
                f"/api/documents/{doc6.id}/workflow_action/",
                {"action": "approve", "comment": ""},
                format="json",
            ).status_code
            == 403
        )

    # Copre righe: 1242-1280, 1309-1342, 1388, 1440, 1456, 1476, 1486-1491
    @patch("apps.signatures.services.SignatureService.request")
    def test_request_signature_and_conservation_and_share(
        self, mock_req, admin_client, operator_client, approver_client, admin_user, operator_user, approver_user, folder
    ):
        mock_req.return_value = (MagicMock(id=uuid.uuid4()), "otp")
        doc = Document.objects.create(
            title="RS",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        assert (
            operator_client.post(
                f"/api/documents/{doc.id}/request_signature/",
                {"signer_id": str(admin_user.id), "format": "pades_invisible"},
                format="json",
            ).status_code
            in (403, 404)
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc.id}/request_signature/",
                {"signer_id": str(admin_user.id), "format": "pades_invisible"},
                format="json",
            ).status_code
            == 400
        )
        Document.objects.filter(pk=doc.pk).update(status=Document.STATUS_APPROVED, current_version=1)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc.id}/request_signature/",
                {"signer_id": str(admin_user.id), "format": "pades_invisible"},
                format="json",
            ).status_code
            == 201
        )
        ms = MetadataStructure.objects.create(
            name=f"sig-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
            signature_enabled=False,
        )
        doc_ms = Document.objects.create(
            title="MS",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms,
        )
        DocumentVersion.objects.create(
            document=doc_ms,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc_ms.id}/request_signature/",
                {"signer_id": str(admin_user.id)},
                format="json",
            ).status_code
            == 400
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc.id}/request_signature/",
                {"signer_id": str(uuid.uuid4()), "format": "pades_invisible"},
                format="json",
            ).status_code
            == 400
        )
        ms_allow = MetadataStructure.objects.create(
            name=f"sigal-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
            signature_enabled=True,
        )
        ms_allow.allowed_signers.add(operator_user)
        doc_allow = Document.objects.create(
            title="Allow",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms_allow,
        )
        DocumentVersion.objects.create(
            document=doc_allow,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc_allow.id}/request_signature/",
                {"signer_id": str(admin_user.id)},
                format="json",
            ).status_code
            == 400
        )
        doc_nov = Document.objects.create(
            title="NoVer",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc_nov.id}/request_signature/",
                {"signer_id": str(admin_user.id)},
                format="json",
            ).status_code
            == 400
        )
        from apps.signatures.models import ConservationRequest, SignatureRequest

        doc_c = Document.objects.create(
            title="Cons",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
        )
        v_c = DocumentVersion.objects.create(
            document=doc_c,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v_c.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        SignatureRequest.objects.create(
            document=doc_c,
            document_version=v_c,
            requested_by=admin_user,
            signer=admin_user,
            format="pades_invisible",
            status="completed",
        )
        ms_c = MetadataStructure.objects.create(
            name=f"con-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
            conservation_enabled=True,
            conservation_document_type="Tipo",
            conservation_class="2",
        )
        Document.objects.filter(pk=doc_c.pk).update(metadata_structure=ms_c)
        doc_c.refresh_from_db()
        DocumentPermission.objects.create(
            document=doc_c, user=approver_user, can_read=True, can_write=True, can_delete=False
        )
        DocumentPermission.objects.create(
            document=doc_c, user=operator_user, can_read=True, can_write=False, can_delete=False
        )
        with patch("apps.signatures.services.ConservationService.submit") as mock_sub:
            mock_sub.return_value = MagicMock(id=uuid.uuid4(), status="sent")
            assert (
                approver_client.post(
                    f"/api/documents/{doc_c.id}/send_to_conservation/",
                    {"document_type": "x", "document_date": timezone.now().date().isoformat()},
                    format="json",
                ).status_code
                == 201
            )
        assert (
            operator_client.post(
                f"/api/documents/{doc_c.id}/send_to_conservation/",
                {"document_type": "x", "document_date": timezone.now().date().isoformat()},
                format="json",
            ).status_code
            == 403
        )
        doc_nc = Document.objects.create(
            title="NC",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_DRAFT,
        )
        v_nc = DocumentVersion.objects.create(
            document=doc_nc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v_nc.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        SignatureRequest.objects.create(
            document=doc_nc,
            document_version=v_nc,
            requested_by=admin_user,
            signer=admin_user,
            format="pades_invisible",
            status="completed",
        )
        Document.objects.filter(pk=doc_nc.pk).update(metadata_structure=ms_c)
        DocumentPermission.objects.create(
            document=doc_nc, user=approver_user, can_read=True, can_write=True, can_delete=False
        )
        assert (
            approver_client.post(
                f"/api/documents/{doc_nc.id}/send_to_conservation/",
                {"document_date": timezone.now().date().isoformat()},
                format="json",
            ).status_code
            == 400
        )
        ms_nocon = MetadataStructure.objects.create(
            name=f"nco-{uuid.uuid4().hex[:6]}",
            tenant=folder.tenant,
            created_by=admin_user,
            applicable_to=["document"],
            is_active=True,
            conservation_enabled=False,
        )
        doc_nocon = Document.objects.create(
            title="NoCon",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms_nocon,
        )
        v_nocon = DocumentVersion.objects.create(
            document=doc_nocon,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v_nocon.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        SignatureRequest.objects.create(
            document=doc_nocon,
            document_version=v_nocon,
            requested_by=admin_user,
            signer=admin_user,
            format="pades_invisible",
            status="completed",
        )
        DocumentPermission.objects.create(
            document=doc_nocon, user=approver_user, can_read=True, can_write=True, can_delete=False
        )
        assert (
            approver_client.post(
                f"/api/documents/{doc_nocon.id}/send_to_conservation/",
                {"document_date": timezone.now().date().isoformat()},
                format="json",
            ).status_code
            == 400
        )
        doc_nosig = Document.objects.create(
            title="NoSig",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms_c,
        )
        DocumentVersion.objects.create(
            document=doc_nosig,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        DocumentPermission.objects.create(
            document=doc_nosig, user=approver_user, can_read=True, can_write=True, can_delete=False
        )
        assert (
            approver_client.post(
                f"/api/documents/{doc_nosig.id}/send_to_conservation/",
                {"document_date": timezone.now().date().isoformat()},
                format="json",
            ).status_code
            == 400
        )
        doc_dup = Document.objects.create(
            title="Dup",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms_c,
        )
        v_dup = DocumentVersion.objects.create(
            document=doc_dup,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v_dup.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        SignatureRequest.objects.create(
            document=doc_dup,
            document_version=v_dup,
            requested_by=admin_user,
            signer=admin_user,
            format="pades_invisible",
            status="completed",
        )
        ConservationRequest.objects.create(
            document=doc_dup,
            document_version=v_dup,
            requested_by=admin_user,
            document_type="Tipo",
            document_date=timezone.now().date(),
            status="sent",
        )
        DocumentPermission.objects.create(
            document=doc_dup, user=approver_user, can_read=True, can_write=True, can_delete=False
        )
        assert (
            approver_client.post(
                f"/api/documents/{doc_dup.id}/send_to_conservation/",
                {"document_date": timezone.now().date().isoformat()},
                format="json",
            ).status_code
            == 400
        )
        assert (
            admin_client.post(
                f"/api/documents/{doc.id}/share/",
                {"recipient_type": "internal", "recipient_user_id": str(uuid.uuid4())},
                format="json",
            ).status_code
            == 400
        )
        f_bad = Folder.objects.create(name="Bad", tenant=folder.tenant, created_by=admin_user, is_deleted=True)
        assert (
            admin_client.patch(f"/api/documents/{doc.id}/move/", {"folder_id": str(f_bad.id)}, format="json").status_code
            == 400
        )
        assert admin_client.post(f"/api/documents/{doc.id}/attachments/", {}, format="multipart").status_code == 400
        att = SimpleUploadedFile("t.txt", b"x", content_type="text/plain")
        r_att = admin_client.post(f"/api/documents/{doc.id}/attachments/", {"file": att}, format="multipart")
        assert r_att.status_code == 201
        aid = r_att.json()["id"]
        assert admin_client.delete(f"/api/documents/{doc.id}/attachments/{aid}/").status_code == 204
        assert admin_client.delete(f"/api/documents/{doc.id}/attachments/{uuid.uuid4()}/").status_code == 404
        doc_att = Document.objects.create(
            title="ADL",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        aobj = DocumentAttachment.objects.create(
            document=doc_att,
            file_name="x.txt",
            file_size=1,
            file_type="text/plain",
            uploaded_by=admin_user,
        )
        aobj.file.save("x.txt", SimpleUploadedFile("x.txt", b"y", content_type="text/plain"), save=True)
        aobj_pk = aobj.pk
        _real_att_open = FieldFile.open

        def _open_att(self, mode="rb"):
            inst = getattr(self, "instance", None)
            if getattr(inst, "pk", None) == aobj_pk:
                raise OSError("e")
            return _real_att_open(self, mode)

        with patch.object(FieldFile, "open", _open_att):
            assert admin_client.get(f"/api/documents/{doc_att.id}/attachments/{aobj.id}/download/").status_code == 404


@pytest.mark.django_db
class TestDocViewsEncryptDecryptTemplate:
    # Copre righe: 1507, 1513, 1519-1520, 1526-1527, 1550-1551
    def test_encrypt_branches(self, admin_client, admin_user, folder):
        doc = Document.objects.create(
            title="Enc",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        assert admin_client.post(f"/api/documents/{doc.id}/encrypt/", {"password": "short"}, format="json").status_code == 400
        DocumentVersion.objects.filter(pk=v.pk).delete()
        assert admin_client.post(f"/api/documents/{doc.id}/encrypt/", {"password": "abcdefgh"}, format="json").status_code == 400
        v2 = DocumentVersion.objects.create(
            document=doc,
            version_number=2,
            file_name="b.pdf",
            is_current=True,
            created_by=admin_user,
        )
        v2.file.save("b.pdf", SimpleUploadedFile("b.pdf", b"%PDF", content_type="application/pdf"), save=True)
        doc.current_version = 2
        doc.save(update_fields=["current_version"])
        with patch.object(FieldFile, "path", property(fget=lambda self: (_ for _ in ()).throw(ValueError("np")))):
            assert (
                admin_client.post(f"/api/documents/{doc.id}/encrypt/", {"password": "abcdefgh"}, format="json").status_code == 400
            )
        with patch("apps.documents.views.DocumentEncryption.encrypt_file", side_effect=RuntimeError("enc")):
            assert (
                admin_client.post(f"/api/documents/{doc.id}/encrypt/", {"password": "abcdefgh"}, format="json").status_code == 500
            )
        fd, enc_path = tempfile.mkstemp(suffix=".enc")
        os.write(fd, b"cipher")
        os.close(fd)
        with patch("apps.documents.views.DocumentEncryption.encrypt_file", return_value=(enc_path, "salt")):
            with patch("apps.documents.views.os.remove", side_effect=OSError("x")):
                assert (
                    admin_client.post(f"/api/documents/{doc.id}/encrypt/", {"password": "abcdefgh"}, format="json").status_code
                    == 200
                )
        if os.path.isfile(enc_path):
            os.unlink(enc_path)

    # Copre righe: 1570, 1576-1577, 1583-1589, 1596, 1636-1638, 1643
    def test_decrypt_and_template(self, admin_client, operator_client, admin_user, folder):
        from cryptography.exceptions import InvalidTag

        doc_plain = Document.objects.create(
            title="Plain",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        DocumentVersion.objects.create(
            document=doc_plain,
            version_number=1,
            file_name="a.pdf",
            is_current=True,
            created_by=admin_user,
        )
        assert (
            admin_client.post(f"/api/documents/{doc_plain.id}/decrypt_download/", {"password": "abcdefgh"}, format="json").status_code
            == 400
        )
        doc = Document.objects.create(
            title="X.enc",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            current_version=1,
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="e.enc",
            is_current=True,
            is_encrypted=True,
            created_by=admin_user,
        )
        v.file.save("e.enc", SimpleUploadedFile("e.enc", b"x", content_type="application/octet-stream"), save=True)
        with patch.object(FieldFile, "path", property(fget=lambda self: (_ for _ in ()).throw(ValueError("np")))):
            assert (
                admin_client.post(f"/api/documents/{doc.id}/decrypt_download/", {"password": "abcdefgh"}, format="json").status_code
                == 400
            )
        with patch("apps.documents.views.DocumentEncryption.decrypt_file", side_effect=InvalidTag()):
            assert (
                admin_client.post(f"/api/documents/{doc.id}/decrypt_download/", {"password": "wrongpwd1"}, format="json").status_code
                == 400
            )
        with patch("apps.documents.views.DocumentEncryption.decrypt_file", side_effect=RuntimeError("dec")):
            assert (
                admin_client.post(f"/api/documents/{doc.id}/decrypt_download/", {"password": "abcdefgh"}, format="json").status_code
                == 400
            )
        with patch("apps.documents.views.DocumentEncryption.decrypt_file", return_value=b"plain"):
            r = admin_client.post(f"/api/documents/{doc.id}/decrypt_download/", {"password": "abcdefgh"}, format="json")
            assert r.status_code == 200
            assert "X" in r.get("Content-Disposition", "")
        assert (
            operator_client.post(f"/api/document-templates/", {"name": "N", "is_active": True}, format="json").status_code == 403
        )
        tpl = DocumentTemplate.objects.create(name=f"T-{uuid.uuid4().hex[:6]}", is_active=True, created_by=admin_user)
        assert operator_client.patch(f"/api/document-templates/{tpl.id}/", {"name": "Y"}, format="json").status_code == 403
        assert operator_client.delete(f"/api/document-templates/{tpl.id}/").status_code == 403
        assert admin_client.patch(f"/api/document-templates/{tpl.id}/", {"name": "Z"}, format="json").status_code == 200
        tpl2 = DocumentTemplate.objects.create(name=f"T2-{uuid.uuid4().hex[:6]}", is_active=True, created_by=admin_user)
        assert admin_client.delete(f"/api/document-templates/{tpl2.id}/").status_code == 204
