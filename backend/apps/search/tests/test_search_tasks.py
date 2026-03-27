"""Task indicizzazione search: index_document."""
import os
import uuid
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document, DocumentVersion, Folder
from apps.search.models import DocumentIndex
from apps.search.tasks import index_document


@pytest.fixture
def tenant_user_doc(db):
    from django.contrib.auth import get_user_model
    from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant

    User = get_user_model()
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Default", "plan": "enterprise"},
    )
    u = User.objects.create_user(email=f"ix-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
    u.tenant = t
    u.save(update_fields=["tenant"])
    ou = OrganizationalUnit.objects.create(name="IX", code=f"I{uuid.uuid4().hex[:4]}", tenant=t)
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    folder = Folder.objects.create(name="IXF", tenant=t, created_by=u)
    doc = Document.objects.create(title="IX Doc", tenant=t, folder=folder, created_by=u, owner=u)
    return u, doc


@pytest.mark.django_db
class TestSearchTasks:
    def test_index_document_missing_version_returns_early(self):
        index_document(str(uuid.uuid4()))
        assert DocumentIndex.objects.count() == 0

    def test_index_document_no_file_still_creates_index(self, tenant_user_doc):
        _, doc = tenant_user_doc
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="n.bin",
            created_by=doc.created_by,
            is_current=True,
        )
        index_document(str(v.id))
        idx = DocumentIndex.objects.get(document=doc)
        assert idx.content == ""
        assert idx.document_version_id == v.id

    def test_index_document_extracts_when_file_on_disk(self, tenant_user_doc, tmp_path, settings):
        _, doc = tenant_user_doc
        settings.MEDIA_ROOT = str(tmp_path)
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="t.txt",
            file_type="text/plain",
            created_by=doc.created_by,
            is_current=True,
        )
        v.file.save("t.txt", SimpleUploadedFile("t.txt", b"hello index", content_type="text/plain"), save=True)
        with patch("apps.search.tasks.extract_text", return_value="extracted body") as ex:
            index_document(str(v.id))
        ex.assert_called_once()
        idx = DocumentIndex.objects.get(document=doc)
        assert idx.content == "extracted body"
        assert idx.error_message == ""

    def test_index_document_extract_exception_sets_error_message(self, tenant_user_doc, tmp_path, settings):
        _, doc = tenant_user_doc
        settings.MEDIA_ROOT = str(tmp_path)
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.txt",
            file_type="text/plain",
            created_by=doc.created_by,
            is_current=True,
        )
        v.file.save("x.txt", SimpleUploadedFile("x.txt", b"x", content_type="text/plain"), save=True)
        with patch("apps.search.tasks.extract_text", side_effect=ValueError("bad format")):
            index_document(str(v.id))
        idx = DocumentIndex.objects.get(document=doc)
        assert "bad format" in idx.error_message

    def test_index_document_file_path_not_on_disk_skips_extract(self, tenant_user_doc, tmp_path, settings):
        _, doc = tenant_user_doc
        settings.MEDIA_ROOT = str(tmp_path)
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="gone.txt",
            file_type="text/plain",
            created_by=doc.created_by,
            is_current=True,
        )
        v.file.save(
            "gone.txt",
            SimpleUploadedFile("gone.txt", b"x", content_type="text/plain"),
            save=True,
        )
        os.remove(v.file.path)
        with patch("apps.search.tasks.extract_text") as ex:
            index_document(str(v.id))
        ex.assert_not_called()
        idx = DocumentIndex.objects.get(document=doc)
        assert idx.content == ""

    def test_index_document_updates_existing_index(self, tenant_user_doc, tmp_path, settings):
        _, doc = tenant_user_doc
        settings.MEDIA_ROOT = str(tmp_path)
        v1 = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="a.txt",
            file_type="text/plain",
            created_by=doc.created_by,
            is_current=False,
        )
        v1.file.save("a.txt", SimpleUploadedFile("a.txt", b"old", content_type="text/plain"), save=True)
        DocumentIndex.objects.create(document=doc, document_version=v1, content="old")
        v2 = DocumentVersion.objects.create(
            document=doc,
            version_number=2,
            file_name="b.txt",
            file_type="text/plain",
            created_by=doc.created_by,
            is_current=True,
        )
        v2.file.save("b.txt", SimpleUploadedFile("b.txt", b"new", content_type="text/plain"), save=True)
        with patch("apps.search.tasks.extract_text", return_value="new content"):
            index_document(str(v2.id))
        idx = DocumentIndex.objects.get(document=doc)
        assert idx.content == "new content"
        assert idx.document_version_id == v2.id
