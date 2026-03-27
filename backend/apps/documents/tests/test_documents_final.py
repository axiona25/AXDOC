# FASE 35D.1 — Copertura finale modulo documents (98%+ target)
# Commenti: Copre: <file> righe …
import os
import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.test import RequestFactory
from PIL import Image
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.documents.classification_service import DocumentClassificationService
from apps.documents.folder_views import _visible_folder_ids
from apps.documents.models import (
    Document,
    DocumentAttachment,
    DocumentOUPermission,
    DocumentPermission,
    DocumentTemplate,
    DocumentVersion,
    Folder,
)
from apps.documents.ocr_service import OCRService
from apps.documents.permissions import CanAccessDocument, _documents_queryset_filter
from apps.documents.serializers import DocumentDetailSerializer, DocumentListSerializer, FolderCreateSerializer
from apps.documents.tasks import (
    _compress_image,
    _compress_video,
    _generate_image_thumbnail,
    _generate_video_thumbnail,
    process_document_text_extraction,
)
from apps.documents.views import DocumentViewSet
from apps.metadata.models import MetadataStructure
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.search.models import DocumentIndex
from apps.signatures.models import SignatureRequest

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Default Org", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Fin OU", code="FIN35", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="fin-adm@test.com",
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
        email="fin-op@test.com",
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
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="FinFld", tenant=tenant, created_by=admin_user)


# Copre: classification_service.py 171-203
@pytest.mark.django_db
class TestClassificationExtractMetadataFinal:
    def test_extract_metadata_all_patterns(self):
        text = """
        Oggetto: Pratica 2024/99
        Mittente: Mario Rossi
        Da: Ufficio Tecnico
        Importo € 1.234,56
        500,00 EUR
        P.IVA 12345678901
        Codice fiscale RSSMRA80A01H501Z
        """
        meta = DocumentClassificationService._extract_metadata(text)
        assert meta.get("subject")
        assert meta.get("sender")
        assert meta.get("amount")
        assert meta.get("vat_number") == "12345678901"
        assert meta.get("fiscal_code") == "RSSMRA80A01H501Z"


# Copre: ocr_service.py 64-83, 87-100, 107-117, 121-131
@pytest.mark.django_db
class TestOCRServiceFinal:
    def test_extract_pdf_with_page_mocks(self):
        img = MagicMock()
        with patch("pdf2image.convert_from_path", return_value=[img]), patch(
            "apps.documents.ocr_service.pytesseract.image_to_data",
            return_value={"conf": [90, -1, 0]},
        ), patch("apps.documents.ocr_service.pytesseract.image_to_string", return_value="line"):
            out = OCRService._extract_from_pdf("/tmp/x.pdf", "ita")
        assert out["success"] is True
        assert "line" in out["text"]

    def test_extract_from_image_pil_error(self):
        with patch("apps.documents.ocr_service.Image.open", side_effect=OSError("bad")):
            with pytest.raises(Exception):
                OCRService._extract_from_image("/tmp/x.png", "ita")

    def test_has_selectable_text_subprocess_failure(self):
        with patch("apps.documents.ocr_service.subprocess.run", side_effect=FileNotFoundError):
            assert OCRService.has_selectable_text("/tmp/a.pdf") is False

    def test_has_selectable_text_timeout(self):
        with patch("apps.documents.ocr_service.subprocess.run", side_effect=TimeoutError):
            assert OCRService.has_selectable_text("/tmp/a.pdf") is False

    def test_pdftotext_extract_exception_returns_empty(self):
        with patch("apps.documents.ocr_service.subprocess.run", side_effect=RuntimeError("x")):
            assert OCRService.pdftotext_extract("/tmp/a.pdf") == ""


# Copre: permissions.py 10-17, 62-63, 72-73, 84-93
@pytest.mark.django_db
class TestDocumentsPermissionsFinal:
    def test_queryset_filter_anonymous(self):
        q = _documents_queryset_filter(AnonymousUser())
        assert q == Q(pk__in=[])

    def test_queryset_filter_superuser(self):
        su = User.objects.create_user(
            email="su35@test.com",
            password="x",
            role="ADMIN",
            is_superuser=True,
            first_name="S",
            last_name="U",
        )
        assert _documents_queryset_filter(su) == Q()

    def test_queryset_filter_guest(self, tenant, ou):
        g = User.objects.create_user(
            email="guest35@test.com",
            password="x",
            role="OPERATOR",
            user_type="guest",
            first_name="G",
            last_name="U",
        )
        g.tenant = tenant
        g.save(update_fields=["tenant"])
        q = _documents_queryset_filter(g)
        assert q is not None

    def test_can_access_non_document(self, admin_user):
        perm = CanAccessDocument()
        assert perm.has_object_permission(MagicMock(user=admin_user), MagicMock(), Folder()) is True


# Copre: models.py 56-80, 203-214, 257-258, 341-422
@pytest.mark.django_db
class TestDocumentsModelsFinal:
    def test_folder_path_and_str(self, tenant, admin_user):
        root = Folder.objects.create(name="RootOnly", tenant=tenant, created_by=admin_user)
        assert str(root) == "RootOnly"
        assert root.get_path() == "root"
        parent = Folder.objects.create(name="P", tenant=tenant, created_by=admin_user)
        child = Folder.objects.create(name="C", parent=parent, tenant=tenant, created_by=admin_user)
        assert "root/" in child.get_path()

    def test_document_version_attachment_permission_str(self, tenant, admin_user, ou, folder):
        doc = Document.objects.create(
            title="T1", folder=folder, created_by=admin_user, owner=admin_user, tenant=tenant
        )
        assert str(doc) == "T1"
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f",
            created_by=admin_user,
            is_current=True,
        )
        assert "T1" in str(ver)

        tpl = DocumentTemplate.objects.create(name="TplF", tenant=tenant, created_by=admin_user)
        assert str(tpl) == "TplF"

        att = DocumentAttachment.objects.create(
            document=doc,
            file_name="a.pdf",
            file_size=1,
            file_type="application/pdf",
            uploaded_by=admin_user,
        )
        assert str(att) == "a.pdf"

        op = User.objects.create_user(
            email="perm35@test.com", password="x", role="OPERATOR", first_name="P", last_name="R"
        )
        dp = DocumentPermission.objects.create(document=doc, user=op, can_read=True)
        assert "T1" in str(dp)

        dop = DocumentOUPermission.objects.create(document=doc, organizational_unit=ou, can_read=True)
        assert ou.code in str(dop)

    def test_validate_metadata_no_structure(self, tenant, admin_user):
        doc = Document.objects.create(title="M", created_by=admin_user, owner=admin_user, tenant=tenant)
        assert doc.validate_metadata({}) == []


# Copre: serializers.py 59-66, 106-113, 147-151, 156-171
@pytest.mark.django_db
class TestDocumentsSerializersFinal:
    def test_folder_create_duplicate_name(self, tenant, admin_user, folder):
        Folder.objects.create(name="Dup", parent=folder, tenant=tenant, created_by=admin_user)
        ser = FolderCreateSerializer(data={"name": "dup", "parent_id": str(folder.id)})
        assert ser.is_valid() is False

    def test_document_list_thumbnail_with_request(self, admin_user, tenant, folder):
        doc = Document.objects.create(title="Th", folder=folder, created_by=admin_user, owner=admin_user, tenant=tenant)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.png",
            file_type="image/png",
            created_by=admin_user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
        buf.seek(0)
        ver.thumbnail.save("t.png", SimpleUploadedFile("t.png", buf.read(), content_type="image/png"), save=True)
        factory = APIRequestFactory()
        wsgi_req = factory.get("/api/")
        drf_req = Request(wsgi_req)
        ser = DocumentListSerializer(doc, context={"request": drf_req})
        assert ser.data.get("thumbnail")

    def test_detail_extracted_preview_truncation(self, admin_user, tenant, folder):
        doc = Document.objects.create(
            title="Long",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            extracted_text="x" * 5000,
        )
        ser = DocumentDetailSerializer(doc, context={"request": None})
        assert ser.data["extracted_text_preview"].endswith("…")

    def test_detail_user_perms_via_explicit_permission(self, admin_user, operator_user, tenant, folder):
        doc = Document.objects.create(
            title="PermDoc",
            folder=folder,
            created_by=operator_user,
            owner=operator_user,
            tenant=tenant,
        )
        DocumentPermission.objects.create(
            document=doc, user=admin_user, can_read=True, can_write=True, can_delete=False
        )
        factory = APIRequestFactory()
        req = Request(factory.get("/"))
        req.user = admin_user
        ser = DocumentDetailSerializer(doc, context={"request": req})
        assert ser.data["can_read"] is True
        assert ser.data["can_write"] is True


# Copre: folder_views.py 17-18, 62-77, 144-149, 161-167, 105-106
@pytest.mark.django_db
class TestFolderViewsFinal:
    def test_visible_folder_ids_anonymous(self):
        assert _visible_folder_ids(AnonymousUser(), None) == set()

    def test_visible_folder_ids_no_request_triggers_scope_early_return(self, admin_user):
        _visible_folder_ids(admin_user, None)

    def test_list_all_tree(self, admin_client, admin_user, tenant):
        Folder.objects.create(name="RootA", tenant=tenant, created_by=admin_user)
        r = admin_client.get("/api/folders/", {"all": "true"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_metadata_patch_bad_json_string(self, admin_client, admin_user, tenant):
        f = Folder.objects.create(name="MetaF", tenant=tenant, created_by=admin_user)
        r = admin_client.patch(
            f"/api/folders/{f.id}/metadata/",
            {"metadata_structure_id": None, "metadata_values": "not-json"},
            format="json",
        )
        assert r.status_code == 200

    def test_metadata_unknown_structure(self, admin_client, admin_user, tenant):
        f = Folder.objects.create(name="MetaF2", tenant=tenant, created_by=admin_user)
        r = admin_client.patch(
            f"/api/folders/{f.id}/metadata/",
            {"metadata_structure_id": str(uuid.uuid4()), "metadata_values": {}},
            format="json",
        )
        assert r.status_code == 400

    def test_update_folder_forbidden_non_owner(self, operator_client, admin_user, operator_user, tenant):
        f = Folder.objects.create(name="Own", tenant=tenant, created_by=admin_user)
        Document.objects.create(
            title="Link",
            folder=f,
            created_by=operator_user,
            owner=operator_user,
            tenant=tenant,
            visibility=Document.VISIBILITY_PERSONAL,
        )
        r = operator_client.patch(f"/api/folders/{f.id}/", {"name": "Hacked"}, format="json")
        assert r.status_code == 403


# Copre: tasks.py 167-195, 205-206, 246-255, 289-293, update_or_create index
@pytest.mark.django_db
class TestTasksFinalCoverage:
    def test_compress_large_png_to_jpg(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user = User.objects.create_user(email="cmp35@test.com", password="x", role="OPERATOR", first_name="C", last_name="M")
        folder = Folder.objects.create(name="C", created_by=user)
        doc = Document.objects.create(title="C", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="huge.png",
            file_type="image/png",
            file_size=5 * 1024 * 1024,
            created_by=user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGBA", (3000, 3000), color=(255, 0, 0, 128)).save(buf, format="PNG")
        buf.seek(0)
        ver.file.save("huge.png", SimpleUploadedFile("huge.png", buf.read(), content_type="image/png"), save=True)
        ver.refresh_from_db()
        _compress_image(ver)

    def test_compress_webp_output(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user = User.objects.create_user(email="w35@test.com", password="x", role="OPERATOR", first_name="W", last_name="B")
        folder = Folder.objects.create(name="W", created_by=user)
        doc = Document.objects.create(title="W", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="b.webp",
            file_type="image/webp",
            file_size=5 * 1024 * 1024,
            created_by=user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGB", (2500, 2500), color="blue").save(buf, format="PNG")
        buf.seek(0)
        ver.file.save("b.webp", SimpleUploadedFile("b.webp", buf.read(), content_type="image/webp"), save=True)
        ver.refresh_from_db()
        _compress_image(ver)

    def test_thumbnail_rgba_convert(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user = User.objects.create_user(email="th35@test.com", password="x", role="OPERATOR", first_name="T", last_name="H")
        folder = Folder.objects.create(name="T", created_by=user)
        doc = Document.objects.create(title="T", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="rgba.png",
            file_type="image/png",
            file_size=4000,
            created_by=user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGBA", (200, 200), color=(1, 2, 3, 200)).save(buf, format="PNG")
        buf.seek(0)
        ver.file.save("rgba.png", SimpleUploadedFile("rgba.png", buf.read(), content_type="image/png"), save=True)
        ver.refresh_from_db()
        _generate_image_thumbnail(ver)

    def test_video_compress_not_smaller_skip(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user = User.objects.create_user(email="vskip@test.com", password="x", role="OPERATOR", first_name="V", last_name="S")
        folder = Folder.objects.create(name="VS", created_by=user)
        doc = Document.objects.create(title="V", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v.mp4",
            file_type="video/mp4",
            file_size=50,
            created_by=user,
            is_current=True,
        )
        ver.file.save("v.mp4", SimpleUploadedFile("v.mp4", b"x" * 100, content_type="video/mp4"), save=True)
        ver.refresh_from_db()
        with patch("apps.documents.tasks.subprocess.run", return_value=MagicMock(returncode=0)), patch(
            "apps.documents.tasks.os.path.exists", return_value=True
        ), patch("apps.documents.tasks.os.path.getsize", return_value=10000):
            _compress_video(ver)

    def test_video_thumbnail_success(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user = User.objects.create_user(email="vth@test.com", password="x", role="OPERATOR", first_name="V", last_name="T")
        folder = Folder.objects.create(name="VT", created_by=user)
        doc = Document.objects.create(title="VT", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="vv.mp4",
            file_type="video/mp4",
            file_size=200,
            created_by=user,
            is_current=True,
        )
        ver.file.save("vv.mp4", SimpleUploadedFile("vv.mp4", b"v" * 80, content_type="video/mp4"), save=True)
        ver.refresh_from_db()
        thumb_bytes = b"\xff\xd8\xff\xe0jpg"

        def exists_side(p):
            s = str(p)
            return s.endswith("_thumb.jpg") or s.endswith(".mp4")

        with patch("apps.documents.tasks.subprocess.run", return_value=MagicMock(returncode=0)), patch(
            "apps.documents.tasks.os.path.exists", side_effect=exists_side
        ), patch("builtins.open", create=True) as m_open:
            m_open.return_value.__enter__.return_value.read.return_value = thumb_bytes
            _generate_video_thumbnail(ver)
        ver.refresh_from_db()

    def test_text_extraction_updates_existing_index(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user = User.objects.create_user(email="ix35@test.com", password="x", role="OPERATOR", first_name="I", last_name="X")
        folder = Folder.objects.create(name="IX", created_by=user)
        doc = Document.objects.create(title="Ix", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_type="application/pdf",
            created_by=user,
            is_current=True,
        )
        ver.file.save("x.pdf", SimpleUploadedFile("x.pdf", b"%PDF", content_type="application/pdf"), save=True)
        DocumentIndex.objects.create(document=doc, document_version=ver, content="old", extraction_method="x")
        with patch("apps.documents.ocr_service.OCRService.has_selectable_text", return_value=True), patch(
            "apps.documents.ocr_service.OCRService.pdftotext_extract", return_value="new text " * 8
        ):
            process_document_text_extraction(str(ver.id))
            process_document_text_extraction(str(ver.id))
        idx = DocumentIndex.objects.get(document=doc)
        assert "new text" in idx.content


# Copre: views.py (filtri lista, bulk, serializer default, preview unlink, copy, workflow, conservation, template)
@pytest.mark.django_db
class TestDocumentViewsFinal:
    def test_list_visibility_filter(self, admin_client, admin_user, tenant, folder):
        Document.objects.create(
            title="Vis",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            visibility=Document.VISIBILITY_PERSONAL,
        )
        r = admin_client.get("/api/documents/", {"visibility": "personal"})
        assert r.status_code == 200

    def test_bulk_move_invalid_ids(self, admin_client):
        r = admin_client.post("/api/documents/bulk_move/", {"document_ids": [], "folder_id": None}, format="json")
        assert r.status_code == 400

    def test_bulk_status_invalid_ids(self, admin_client):
        r = admin_client.post(
            "/api/documents/bulk_status/",
            {"document_ids": "bad", "status": Document.STATUS_ARCHIVED},
            format="json",
        )
        assert r.status_code == 400

    def test_get_serializer_class_default_list_serializer(self, admin_user):
        view = DocumentViewSet()
        view.action = "lock"
        view.request = MagicMock()
        from apps.documents.serializers import DocumentListSerializer

        assert view.get_serializer_class() == DocumentListSerializer

    def test_preview_eml_unlink_swallowed(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        doc = Document.objects.create(
            title="Eml",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="m.eml",
            file_type="message/rfc822",
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("m.eml", SimpleUploadedFile("m.eml", b"From: a\n\nhi", content_type="message/rfc822"), save=True)
        with patch("apps.documents.views.os.unlink", side_effect=OSError("nope")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200

    def test_copy_with_target_folder(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        target = Folder.objects.create(name="Tgt", tenant=tenant, created_by=admin_user)
        doc = Document.objects.create(
            title="Src",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.txt",
            file_type="text/plain",
            file_size=3,
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("a.txt", SimpleUploadedFile("a.txt", b"abc", content_type="text/plain"), save=True)
        r = admin_client.post(
            f"/api/documents/{doc.id}/copy/",
            {"folder_id": str(target.id)},
            format="json",
        )
        assert r.status_code == 201

    def test_start_workflow_rejected_when_already_active(self, admin_client, admin_user, tenant, folder):
        from apps.workflows.models import WorkflowInstance, WorkflowStep, WorkflowTemplate

        doc = Document.objects.create(
            title="WF",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_IN_REVIEW,
        )
        tpl = WorkflowTemplate.objects.create(name="T35", is_published=True, created_by=admin_user)
        step = WorkflowStep.objects.create(template=tpl, name="S1", order=1)
        WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=admin_user,
            status="active",
            current_step_order=step.order,
        )
        r = admin_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(tpl.id)}, format="json")
        assert r.status_code == 400

    def test_send_to_conservation_success_patched(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        ms = MetadataStructure.objects.create(
            name=f"fin-cons-{uuid.uuid4().hex[:8]}",
            conservation_enabled=True,
            conservation_class="2",
            conservation_document_type="TipoA",
        )
        doc = Document.objects.create(
            title="Cons2",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            file_type="application/pdf",
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        SignatureRequest.objects.create(
            document=doc,
            document_version=ver,
            requested_by=admin_user,
            signer=admin_user,
            format="pades_invisible",
            status="completed",
        )
        with patch("apps.signatures.services.ConservationService.submit") as m:
            m.return_value = MagicMock(id=uuid.uuid4(), status="sent")
            r = admin_client.post(
                f"/api/documents/{doc.id}/send_to_conservation/",
                {"document_type": "Doc", "document_date": "2024-06-01"},
                format="json",
            )
        assert r.status_code == 201

    def test_attachment_download_missing_file(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        doc = Document.objects.create(
            title="Att",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        att = DocumentAttachment.objects.create(
            document=doc,
            file_name="x.bin",
            file_size=0,
            file_type="application/octet-stream",
            uploaded_by=admin_user,
        )
        r = admin_client.get(f"/api/documents/{doc.id}/attachments/{att.id}/download/")
        assert r.status_code == 404

    def test_template_partial_forbidden_operator(self, operator_client, admin_user, tenant):
        tpl = DocumentTemplate.objects.create(name="Tpl35u", tenant=tenant, created_by=admin_user)
        r = operator_client.patch(f"/api/document-templates/{tpl.id}/", {"name": "No"}, format="json")
        assert r.status_code == 403

    def test_template_put_update_forbidden_operator(self, operator_client, admin_user, tenant):
        tpl = DocumentTemplate.objects.create(name="PutTpl", tenant=tenant, created_by=admin_user)
        r = operator_client.put(
            f"/api/document-templates/{tpl.id}/",
            {"name": "N", "description": "", "default_status": "DRAFT"},
            format="json",
        )
        assert r.status_code == 403

    def test_start_workflow_forbidden_non_writer(self, operator_client, admin_user, operator_user, tenant, folder):
        from apps.workflows.models import WorkflowTemplate, WorkflowStep

        doc = Document.objects.create(
            title="NoWf",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        DocumentPermission.objects.create(
            document=doc, user=operator_user, can_read=True, can_write=False, can_delete=False
        )
        tpl = WorkflowTemplate.objects.create(name="TNo", is_published=True, created_by=admin_user)
        WorkflowStep.objects.create(template=tpl, name="S", order=1)
        r = operator_client.post(f"/api/documents/{doc.id}/start_workflow/", {"template_id": str(tpl.id)}, format="json")
        assert r.status_code == 403

    def test_workflow_action_no_current_step(self, admin_client, admin_user, tenant, folder):
        from apps.workflows.models import WorkflowInstance, WorkflowStep, WorkflowTemplate

        doc = Document.objects.create(
            title="NoStep",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        tpl = WorkflowTemplate.objects.create(name="TSt", is_published=True, created_by=admin_user)
        WorkflowStep.objects.create(template=tpl, name="S", order=1)
        WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=admin_user,
            status="active",
            current_step_order=99,
        )
        r = admin_client.post(
            f"/api/documents/{doc.id}/workflow_action/",
            {"action": "approve"},
            format="json",
        )
        assert r.status_code == 400

    def test_request_signature_forbidden_read_only(self, operator_client, admin_user, operator_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        ms = MetadataStructure.objects.create(
            name=f"sig-ro-{uuid.uuid4().hex[:6]}",
            signature_enabled=True,
        )
        doc = Document.objects.create(
            title="SigRO",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms,
        )
        DocumentPermission.objects.create(
            document=doc, user=operator_user, can_read=True, can_write=False, can_delete=False
        )
        signer = User.objects.create_user(email="sro@test.com", password="x", role="OPERATOR", first_name="S", last_name="R")
        r = operator_client.post(
            f"/api/documents/{doc.id}/request_signature/",
            {"signer_id": str(signer.id), "format": "pades_invisible"},
            format="json",
        )
        assert r.status_code == 403

    def test_request_signature_signer_not_allowed(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        allowed = User.objects.create_user(email="allow1@test.com", password="x", role="OPERATOR", first_name="A", last_name="L")
        other = User.objects.create_user(email="other1@test.com", password="x", role="OPERATOR", first_name="O", last_name="T")
        ms = MetadataStructure.objects.create(
            name=f"sig-al-{uuid.uuid4().hex[:6]}",
            signature_enabled=True,
        )
        ms.allowed_signers.add(allowed)
        doc = Document.objects.create(
            title="SigAl",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            file_type="application/pdf",
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        with patch("apps.signatures.services.SignatureService.request") as m:
            m.return_value = (MagicMock(id=uuid.uuid4()), "")
            r = admin_client.post(
                f"/api/documents/{doc.id}/request_signature/",
                {"signer_id": str(other.id), "format": "pades_invisible"},
                format="json",
            )
        assert r.status_code == 400
        m.assert_not_called()

    def test_request_signature_no_current_version(self, admin_client, admin_user, tenant, folder):
        ms = MetadataStructure.objects.create(
            name=f"sig-nv-{uuid.uuid4().hex[:6]}",
            signature_enabled=True,
        )
        doc = Document.objects.create(
            title="SigNV",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms,
            current_version=1,
        )
        r = admin_client.post(
            f"/api/documents/{doc.id}/request_signature/",
            {"signer_id": str(admin_user.id), "format": "pades_invisible"},
            format="json",
        )
        assert r.status_code == 400

    def test_send_conservation_no_version(self, admin_client, admin_user, tenant, folder):
        ms = MetadataStructure.objects.create(
            name=f"cons-nv-{uuid.uuid4().hex[:6]}",
            conservation_enabled=True,
        )
        doc = Document.objects.create(
            title="CNV",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
            metadata_structure=ms,
            current_version=1,
        )
        from apps.signatures.models import SignatureRequest

        SignatureRequest.objects.create(
            document=doc,
            document_version=None,
            requested_by=admin_user,
            signer=admin_user,
            format="pades_invisible",
            status="completed",
        )
        r = admin_client.post(
            f"/api/documents/{doc.id}/send_to_conservation/",
            {"document_type": "D", "document_date": "2024-01-01"},
            format="json",
        )
        assert r.status_code == 400

    def test_request_signature_rejected_not_approved(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        signer = User.objects.create_user(email="sigx@test.com", password="x", role="OPERATOR", first_name="S", last_name="I")
        doc = Document.objects.create(
            title="DraftSig",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_DRAFT,
        )
        r = admin_client.post(
            f"/api/documents/{doc.id}/request_signature/",
            {"signer_id": str(signer.id), "format": "pades_invisible"},
            format="json",
        )
        assert r.status_code == 400

    def test_retrieve_document_detail(self, admin_client, admin_user, tenant, folder):
        doc = Document.objects.create(
            title="Ret",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        r = admin_client.get(f"/api/documents/{doc.id}/")
        assert r.status_code == 200

    def test_partial_update_document_ok(self, admin_client, admin_user, tenant, folder):
        doc = Document.objects.create(
            title="Up",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        r = admin_client.patch(f"/api/documents/{doc.id}/", {"title": "Up2"}, format="json")
        assert r.status_code == 200

    def test_preview_office_cleanup_except_branches(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        doc = Document.objects.create(
            title="Off",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.docx",
            file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("f.docx", SimpleUploadedFile("f.docx", b"doc", content_type="application/octet-stream"), save=True)

        def conv(p):
            d = tmp_path / "out"
            d.mkdir(exist_ok=True)
            pdf = d / "f.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            return str(pdf)

        with patch("apps.documents.viewer.convert_office_to_pdf", side_effect=conv), patch(
            "apps.documents.views.os.unlink", side_effect=OSError("x")
        ), patch("apps.documents.views.os.rmdir", side_effect=OSError("y")), patch(
            "apps.documents.views.os.listdir", return_value=["f.pdf"]
        ):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200


# Copre: views.py get_serializer_class 137-143
@pytest.mark.django_db
class TestDocumentViewSetSerializerRouting:
    def test_get_serializer_class_by_action(self):
        v = DocumentViewSet()
        v.request = MagicMock()
        v.action = "list"
        from apps.documents.serializers import DocumentCreateSerializer, DocumentDetailSerializer, DocumentListSerializer

        assert v.get_serializer_class() == DocumentListSerializer
        v.action = "retrieve"
        assert v.get_serializer_class() == DocumentDetailSerializer
        v.action = "create"
        assert v.get_serializer_class() == DocumentCreateSerializer
        v.action = "partial_update"
        assert v.get_serializer_class() == DocumentCreateSerializer


# Copre: folder_views.py scope tenant, get_serializer_class, metadata validation, request_signature
@pytest.mark.django_db
class TestFolderViewsExtraFinal:
    def test_visible_folder_ids_with_default_tenant_request(self, admin_user, tenant):
        factory = APIRequestFactory()
        req = factory.get("/")
        req.tenant = tenant
        _visible_folder_ids(admin_user, req)

    def test_visible_folder_ids_other_tenant_slug_filters(self, admin_user, tenant):
        t2, _ = Tenant.objects.get_or_create(
            slug="acme35", defaults={"name": "Acme", "plan": "enterprise"}
        )
        Folder.objects.create(name="T2F", tenant=t2, created_by=admin_user)
        factory = APIRequestFactory()
        req = factory.get("/")
        req.tenant = t2
        _visible_folder_ids(admin_user, req)

    def test_folder_list_uses_list_serializer(self, admin_client, admin_user, tenant):
        Folder.objects.create(name="Lst", tenant=tenant, created_by=admin_user)
        r = admin_client.get("/api/folders/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_folder_viewset_serializer_classes(self):
        from apps.documents.folder_views import FolderViewSet
        from apps.documents.serializers import FolderCreateSerializer, FolderDetailSerializer

        view = FolderViewSet()
        qp = MagicMock()
        qp.get = lambda k, default=None: "true" if k == "all" else default
        view.request = MagicMock(query_params=qp)
        view.action = "list"
        assert view.get_serializer_class() == FolderDetailSerializer
        view.request.query_params.get = lambda k, default=None: default
        view.action = "retrieve"
        assert view.get_serializer_class() == FolderDetailSerializer
        view.action = "create"
        assert view.get_serializer_class() == FolderCreateSerializer
        view.action = "destroy"
        from apps.documents.serializers import FolderListSerializer

        assert view.get_serializer_class() == FolderListSerializer

    def test_folder_metadata_validation_errors(self, admin_client, admin_user, tenant):
        from apps.metadata.models import MetadataStructure

        ms = MetadataStructure.objects.create(
            name=f"fld-meta-{uuid.uuid4().hex[:6]}",
            applicable_to=["folder"],
            is_active=True,
        )
        f = Folder.objects.create(name="MF", tenant=tenant, created_by=admin_user)
        with patch(
            "apps.metadata.validators.validate_metadata_values",
            return_value=[{"field": "x", "message": "bad"}],
        ):
            r = admin_client.patch(
                f"/api/folders/{f.id}/metadata/",
                {"metadata_structure_id": str(ms.id), "metadata_values": {"x": 1}},
                format="json",
            )
        assert r.status_code == 400

    def test_folder_request_signature(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        signer = User.objects.create_user(
            email="signer35@test.com", password="x", role="OPERATOR", first_name="S", last_name="G"
        )
        doc = Document.objects.create(
            title="App",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.pdf",
            file_type="application/pdf",
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("a.pdf", SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf"), save=True)
        doc2 = Document.objects.create(
            title="App2",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
        )
        ver2 = DocumentVersion.objects.create(
            document=doc2,
            version_number=1,
            file_name="b.pdf",
            file_type="application/pdf",
            created_by=admin_user,
            is_current=True,
        )
        ver2.file.save("b.pdf", SimpleUploadedFile("b.pdf", b"%PDF2", content_type="application/pdf"), save=True)
        Document.objects.create(
            title="NoVer",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            status=Document.STATUS_APPROVED,
        )
        with patch("apps.signatures.services.SignatureService.request") as m:
            m.return_value = (MagicMock(id=uuid.uuid4()), "")
            r = admin_client.post(
                f"/api/folders/{folder.id}/request_signature/",
                {"signer_id": str(signer.id), "format": "pades_invisible"},
                format="json",
            )
        assert r.status_code == 201
        assert m.call_count == 2

    def test_template_delete_forbidden_operator(self, operator_client, admin_user, tenant):
        tpl = DocumentTemplate.objects.create(name="DelTpl", tenant=tenant, created_by=admin_user)
        r = operator_client.delete(f"/api/document-templates/{tpl.id}/")
        assert r.status_code == 403


@pytest.mark.django_db
class TestDocumentPreviewConversionErrors:
    def test_preview_image_convert_fails(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        from apps.documents.viewer import NEEDS_IMAGE_CONVERSION

        doc = Document.objects.create(
            title="Tif",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        mime = next(iter(NEEDS_IMAGE_CONVERSION))
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.tif",
            file_type=mime,
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("x.tif", SimpleUploadedFile("x.tif", b"img", content_type=mime), save=True)
        with patch("apps.documents.viewer.convert_image_to_web", side_effect=RuntimeError("conv")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 500

    def test_preview_image_success_cleanup_oserror(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        from apps.documents.viewer import NEEDS_IMAGE_CONVERSION

        doc = Document.objects.create(
            title="ImgOk",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        mime = next(iter(NEEDS_IMAGE_CONVERSION))
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="h.heic",
            file_type=mime,
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("h.heic", SimpleUploadedFile("h.heic", b"bin", content_type=mime), save=True)
        out_j = tmp_path / "conv.jpg"
        out_j.write_bytes(b"\xff\xd8\xff\xe0" + b"x" * 30)

        def conv(_p):
            return str(out_j), "image/jpeg"

        with patch("apps.documents.viewer.convert_image_to_web", side_effect=conv), patch(
            "apps.documents.views.os.unlink", side_effect=OSError("u")
        ), patch("apps.documents.views.os.rmdir", side_effect=OSError("r")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200

    def test_preview_video_success_cleanup_oserror(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        from apps.documents.viewer import NEEDS_VIDEO_CONVERSION

        doc = Document.objects.create(
            title="VidOk",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        mime = next(iter(NEEDS_VIDEO_CONVERSION))
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v.wmv",
            file_type=mime,
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("v.wmv", SimpleUploadedFile("v.wmv", b"wmv", content_type=mime), save=True)
        out_mp4 = tmp_path / "out.mp4"
        out_mp4.write_bytes(b"mp4data" * 10)

        def cv(_p):
            return str(out_mp4)

        with patch("apps.documents.viewer.convert_video_to_mp4", side_effect=cv), patch(
            "apps.documents.views.os.unlink", side_effect=OSError("u")
        ), patch("apps.documents.views.os.rmdir", side_effect=OSError("r")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 200

    def test_preview_native_stream_open_fails(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        doc = Document.objects.create(
            title="Png",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="n.png",
            file_type="image/png",
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("n.png", SimpleUploadedFile("n.png", b"\x89PNG", content_type="image/png"), save=True)
        with patch("django.db.models.fields.files.FieldFile.open", side_effect=OSError("no")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 404

    def test_preview_video_convert_fails(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        from apps.documents.viewer import NEEDS_VIDEO_CONVERSION

        doc = Document.objects.create(
            title="Mov",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        mime = next(iter(NEEDS_VIDEO_CONVERSION))
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.mov",
            file_type=mime,
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("x.mov", SimpleUploadedFile("x.mov", b"mv", content_type=mime), save=True)
        with patch("apps.documents.viewer.convert_video_to_mp4", side_effect=RuntimeError("ffmpeg")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 500

    def test_preview_generic_file_response_os_error(self, admin_client, admin_user, tenant, folder, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        doc = Document.objects.create(
            title="Aud",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.mp3",
            file_type="audio/mpeg",
            created_by=admin_user,
            is_current=True,
        )
        ver.file.save("a.mp3", SimpleUploadedFile("a.mp3", b"id3", content_type="audio/mpeg"), save=True)
        with patch("django.core.files.storage.FileSystemStorage.open", side_effect=OSError("e")):
            r = admin_client.get(f"/api/documents/{doc.id}/preview/")
        assert r.status_code == 404


# Copre: ocr_service 106, 128 | models validate_metadata | permissions CanAccessDocument | serializers
@pytest.mark.django_db
class TestDocumentsFinalMisc:
    def test_has_selectable_text_non_pdf(self):
        assert OCRService.has_selectable_text("/tmp/x.txt") is False

    def test_pdftotext_extract_ok(self):
        with patch("apps.documents.ocr_service.subprocess.run") as run:
            run.return_value = MagicMock(stdout="hello world " * 10)
            t = OCRService.pdftotext_extract("/tmp/a.pdf")
        assert len(t) > 5

    def test_folder_validate_metadata_with_structure(self, tenant, admin_user):
        from apps.metadata.models import MetadataStructure

        ms = MetadataStructure.objects.create(name=f"vmf-{uuid.uuid4().hex[:6]}")
        f = Folder.objects.create(name="V", tenant=tenant, created_by=admin_user, metadata_structure=ms)
        with patch("apps.metadata.validators.validate_metadata_values", return_value=[]) as vm:
            assert f.validate_metadata({}) == []
            vm.assert_called_once()

    def test_folder_validate_metadata_returns_empty_without_structure(self, tenant, admin_user):
        f = Folder.objects.create(name="NS", tenant=tenant, created_by=admin_user, metadata_structure=None)
        assert f.validate_metadata({"a": 1}) == []

    def test_document_validate_metadata_with_structure(self, tenant, admin_user):
        from apps.metadata.models import MetadataStructure

        ms = MetadataStructure.objects.create(name=f"vmd-{uuid.uuid4().hex[:6]}")
        doc = Document.objects.create(
            title="V", created_by=admin_user, owner=admin_user, tenant=tenant, metadata_structure=ms
        )
        with patch("apps.metadata.validators.validate_metadata_values", return_value=[{"field": "a", "message": "e"}]):
            assert len(doc.validate_metadata({})) == 1

    def test_can_access_anonymous_denied(self, folder, admin_user):
        from django.contrib.auth.models import AnonymousUser

        perm = CanAccessDocument()
        req = MagicMock()
        req.user = AnonymousUser()
        d = Document.objects.create(title="An", folder=folder, created_by=admin_user, owner=admin_user)
        assert perm.has_object_permission(req, MagicMock(), d) is False

    def test_can_access_superuser_allowed(self, tenant, admin_user, folder):
        su = User.objects.create_user(
            email="suacc@test.com", password="x", role="ADMIN", is_superuser=True, first_name="S", last_name="U"
        )
        doc = Document.objects.create(
            title="SU", folder=folder, created_by=admin_user, owner=admin_user, tenant=tenant
        )
        perm = CanAccessDocument()
        req = MagicMock()
        req.user = su
        assert perm.has_object_permission(req, MagicMock(), doc) is True

    def test_can_access_ou_permission_row(self, tenant, admin_user, operator_user, ou, folder):
        doc = Document.objects.create(
            title="OU2",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            visibility=Document.VISIBILITY_PERSONAL,
        )
        DocumentOUPermission.objects.create(document=doc, organizational_unit=ou, can_read=True, can_write=False)
        OrganizationalUnitMembership.objects.get_or_create(
            user=operator_user, organizational_unit=ou, defaults={"role": "OPERATOR"}
        )
        perm = CanAccessDocument()
        req = MagicMock()
        req.user = operator_user
        assert perm.has_object_permission(req, MagicMock(), doc) is True

    def test_can_access_guest_explicit_permission(self, tenant, admin_user, folder):
        guest = User.objects.create_user(
            email="gacc@test.com", password="x", role="OPERATOR", user_type="guest", first_name="G", last_name="A"
        )
        doc = Document.objects.create(
            title="G",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        DocumentPermission.objects.create(document=doc, user=guest, can_read=True)
        perm = CanAccessDocument()
        req = MagicMock()
        req.user = guest
        assert perm.has_object_permission(req, MagicMock(), doc) is True

    def test_can_access_shared_visibility(self, tenant, admin_user, operator_user, folder):
        doc = Document.objects.create(
            title="Sh",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            visibility=Document.VISIBILITY_SHARED,
        )
        perm = CanAccessDocument()
        req = MagicMock()
        req.user = operator_user
        assert perm.has_object_permission(req, MagicMock(), doc) is True

    def test_can_access_fully_denied(self, tenant, folder):
        alice = User.objects.create_user(
            email="alice35@test.com", password="x", role="OPERATOR", first_name="A", last_name="L"
        )
        bob = User.objects.create_user(
            email="bob35@test.com", password="x", role="OPERATOR", first_name="B", last_name="O"
        )
        doc = Document.objects.create(
            title="Priv",
            folder=folder,
            created_by=alice,
            owner=alice,
            tenant=tenant,
            visibility=Document.VISIBILITY_PERSONAL,
        )
        perm = CanAccessDocument()
        req = MagicMock()
        req.user = bob
        assert perm.has_object_permission(req, MagicMock(), doc) is False

    def test_can_access_office_peer(self, tenant, admin_user, operator_user, ou, folder):
        doc = Document.objects.create(
            title="Off",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
            visibility=Document.VISIBILITY_OFFICE,
        )
        perm = CanAccessDocument()
        OrganizationalUnitMembership.objects.get_or_create(
            user=admin_user, organizational_unit=ou, defaults={"role": "OPERATOR"}
        )
        OrganizationalUnitMembership.objects.get_or_create(
            user=operator_user, organizational_unit=ou, defaults={"role": "OPERATOR"}
        )
        req = MagicMock()
        req.user = operator_user
        assert perm.has_object_permission(req, MagicMock(), doc) is True

    def test_folder_create_empty_name(self):
        ser = FolderCreateSerializer(data={"name": "", "parent_id": None})
        assert ser.is_valid() is False
        ser2 = FolderCreateSerializer(data={"name": "   ", "parent_id": None})
        assert ser2.is_valid() is False
        ser3 = FolderCreateSerializer(data={"parent_id": None})
        assert ser3.is_valid() is False

    def test_folder_create_validate_raises_directly(self):
        ser = FolderCreateSerializer()
        with pytest.raises(serializers.ValidationError):
            ser.validate({"name": "  ", "parent_id": None})

    def test_detail_user_permission_can_write(self, admin_user, operator_user, tenant, folder):
        doc = Document.objects.create(
            title="W",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        DocumentPermission.objects.create(
            document=doc, user=operator_user, can_read=True, can_write=True, can_delete=False
        )
        factory = APIRequestFactory()
        req = Request(factory.get("/"))
        req.user = operator_user
        ser = DocumentDetailSerializer(doc, context={"request": req})
        assert ser.data["can_write"] is True

    def test_document_list_thumbnail_no_request(self, admin_user, tenant, folder):
        doc = Document.objects.create(title="NR", folder=folder, created_by=admin_user, owner=admin_user, tenant=tenant)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.png",
            file_type="image/png",
            created_by=admin_user,
            is_current=True,
        )
        buf = BytesIO()
        Image.new("RGB", (5, 5), color="red").save(buf, format="PNG")
        buf.seek(0)
        ver.thumbnail.save("t.png", SimpleUploadedFile("t.png", buf.read(), content_type="image/png"), save=True)
        ser = DocumentListSerializer(doc, context={})
        assert ser.data.get("thumbnail")


# Copre: serializers DocumentDetailSerializer OU perm + deny; tasks.py video save
@pytest.mark.django_db
class TestSerializersOUAndTasksVideo:
    def test_detail_serializer_ou_permission_read(self, admin_user, operator_user, tenant, ou, folder):
        doc = Document.objects.create(
            title="OU",
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
            tenant=tenant,
        )
        DocumentOUPermission.objects.create(
            document=doc, organizational_unit=ou, can_read=True, can_write=False
        )
        OrganizationalUnitMembership.objects.get_or_create(
            user=operator_user, organizational_unit=ou, defaults={"role": "OPERATOR"}
        )
        factory = APIRequestFactory()
        req = Request(factory.get("/"))
        req.user = operator_user
        ser = DocumentDetailSerializer(doc, context={"request": req})
        assert ser.data["can_read"] is True
        assert ser.data["can_write"] is False

    def test_detail_serializer_no_permission(self, tenant, admin_user, operator_user, folder):
        other = User.objects.create_user(
            email="oth35@test.com", password="x", role="OPERATOR", first_name="O", last_name="T"
        )
        doc = Document.objects.create(
            title="NP",
            folder=folder,
            created_by=other,
            owner=other,
            tenant=tenant,
            visibility=Document.VISIBILITY_PERSONAL,
        )
        factory = APIRequestFactory()
        req = Request(factory.get("/"))
        req.user = operator_user
        ser = DocumentDetailSerializer(doc, context={"request": req})
        assert ser.data["can_read"] is False

    def test_compress_video_replaces_when_smaller(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        user = User.objects.create_user(email="vsm@test.com", password="x", role="OPERATOR", first_name="V", last_name="M")
        folder = Folder.objects.create(name="VSM", created_by=user)
        doc = Document.objects.create(title="V", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v.mp4",
            file_type="video/mp4",
            file_size=50000,
            created_by=user,
            is_current=True,
        )
        ver.file.save("v.mp4", SimpleUploadedFile("v.mp4", b"x" * 2000, content_type="video/mp4"), save=True)
        ver.refresh_from_db()

        def fake_run(cmd, capture_output=True, timeout=None, **kwargs):
            out_path = cmd[-1]
            with open(out_path, "wb") as f:
                f.write(b"sm")
            return MagicMock(returncode=0)

        with patch("apps.documents.tasks.subprocess.run", side_effect=fake_run), patch(
            "apps.documents.tasks.os.path.exists", return_value=True
        ), patch("apps.documents.tasks.os.path.getsize", return_value=100):
            _compress_video(ver)
        ver.refresh_from_db()
        assert ver.file_size == 100

    def test_generate_video_thumbnail_writes_thumb(self, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        from django.utils import timezone as dj_tz

        now = dj_tz.now()
        os.makedirs(
            os.path.join(settings.MEDIA_ROOT, "thumbnails", str(now.year), f"{now.month:02d}"),
            exist_ok=True,
        )
        user = User.objects.create_user(email="vth2@test.com", password="x", role="OPERATOR", first_name="V", last_name="H")
        folder = Folder.objects.create(name="VTH2", created_by=user)
        doc = Document.objects.create(title="V", folder=folder, created_by=user, owner=user)
        ver = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="clip.mp4",
            file_type="video/mp4",
            file_size=300,
            created_by=user,
            is_current=True,
        )
        ver.file.save("clip.mp4", SimpleUploadedFile("clip.mp4", b"v" * 120, content_type="video/mp4"), save=True)
        ver.refresh_from_db()

        def fake_run(cmd, capture_output=True, timeout=None, **kwargs):
            thumb = cmd[-1]
            with open(thumb, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 20)
            return MagicMock(returncode=0)

        with patch("apps.documents.tasks.subprocess.run", side_effect=fake_run), patch(
            "apps.documents.tasks.os.path.exists", return_value=True
        ):
            _generate_video_thumbnail(ver)
        ver.refresh_from_db()
        assert ver.thumbnail
