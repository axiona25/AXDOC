"""
Test API Documenti (FASE 05): upload, versioning, download, lock, copy, move, allegati, permessi.
"""
import io
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document, DocumentVersion, DocumentAttachment, DocumentPermission, Folder

User = get_user_model()


class DocumentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            role="OPERATOR",
        )
        self.other = User.objects.create_user(
            email="other@test.com",
            password="Other123!",
            first_name="Other",
            last_name="User",
            role="OPERATOR",
        )
        self.client.force_authenticate(user=self.user)
        self.folder = Folder.objects.create(name="TestFolder", created_by=self.user)

    def test_upload_document_creates_version_one(self):
        f = SimpleUploadedFile("doc.pdf", b"PDF content", content_type="application/pdf")
        r = self.client.post(
            "/api/documents/",
            {"title": "Doc1", "file": f, "folder_id": str(self.folder.id)},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["current_version"], 1)
        doc = Document.objects.get(id=r.data["id"])
        v = doc.versions.get(version_number=1)
        self.assertTrue(v.file)
        self.assertTrue(v.checksum)
        self.assertTrue(v.is_current)

    def test_upload_new_version_increments_and_marks_current(self):
        doc = Document.objects.create(title="D", folder=self.folder, created_by=self.user)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v1.pdf",
            file_size=10,
            checksum="abc",
            created_by=self.user,
            is_current=True,
        )
        doc.current_version = 1
        doc.save()
        f = SimpleUploadedFile("v2.pdf", b"Version 2 content", content_type="application/pdf")
        r = self.client.post(
            f"/api/documents/{doc.id}/upload_version/",
            {"file": f, "change_description": "Updated"},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["version_number"], 2)
        doc.refresh_from_db()
        self.assertEqual(doc.current_version, 2)
        self.assertFalse(doc.versions.get(version_number=1).is_current)
        self.assertTrue(doc.versions.get(version_number=2).is_current)

    def test_download_current_version(self):
        doc = Document.objects.create(title="D", folder=self.folder, created_by=self.user)
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="f.pdf",
            file_size=5,
            created_by=self.user,
            is_current=True,
        )
        v.file.save("f.pdf", SimpleUploadedFile("f.pdf", b"data"), save=True)
        doc.current_version = 1
        doc.save()
        r = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"data")
        try:
            v.file.delete(save=False)
        except Exception:
            pass

    def test_download_specific_version(self):
        doc = Document.objects.create(title="D", folder=self.folder, created_by=self.user)
        v1 = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="v1.pdf",
            file_size=3,
            created_by=self.user,
            is_current=False,
        )
        v1.file.save("v1.pdf", SimpleUploadedFile("v1.pdf", b"v1"), save=True)
        r = self.client.get(f"/api/documents/{doc.id}/download/?version=1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"v1")
        try:
            v1.file.delete(save=False)
        except Exception:
            pass

    def test_lock_prevents_upload_version_by_other_user(self):
        doc = Document.objects.create(title="D", folder=self.folder, created_by=self.user)
        DocumentPermission.objects.create(document=doc, user=self.other, can_read=True, can_write=True)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_size=1,
            created_by=self.user,
            is_current=True,
        )
        doc.current_version = 1
        doc.save()
        self.client.post(f"/api/documents/{doc.id}/lock/")
        self.client.force_authenticate(user=self.other)
        f = SimpleUploadedFile("v2.pdf", b"v2", content_type="application/pdf")
        r = self.client.post(
            f"/api/documents/{doc.id}/upload_version/",
            {"file": f},
            format="multipart",
        )
        self.assertEqual(r.status_code, 409)

    def test_unlock_allows_upload_again(self):
        doc = Document.objects.create(title="D", folder=self.folder, created_by=self.user)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.pdf",
            file_size=1,
            created_by=self.user,
            is_current=True,
        )
        doc.current_version = 1
        doc.save()
        self.client.post(f"/api/documents/{doc.id}/lock/")
        self.client.post(f"/api/documents/{doc.id}/unlock/")
        f = SimpleUploadedFile("v2.pdf", b"v2", content_type="application/pdf")
        r = self.client.post(
            f"/api/documents/{doc.id}/upload_version/",
            {"file": f},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)

    def test_copy_creates_new_document(self):
        doc = Document.objects.create(title="Original", folder=self.folder, created_by=self.user)
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="orig.pdf",
            file_size=4,
            created_by=self.user,
            is_current=True,
        )
        v.file.save("orig.pdf", SimpleUploadedFile("orig.pdf", b"copy"), save=True)
        doc.current_version = 1
        doc.save()
        r = self.client.post(
            f"/api/documents/{doc.id}/copy/",
            {"new_title": "Copia"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.data["id"], str(doc.id))
        self.assertEqual(r.data["title"], "Copia")
        new_doc = Document.objects.get(id=r.data["id"])
        self.assertEqual(new_doc.versions.count(), 1)
        try:
            v.file.delete(save=False)
            new_doc.versions.first().file.delete(save=False)
        except Exception:
            pass

    def test_move_updates_folder(self):
        doc = Document.objects.create(title="D", folder=self.folder, created_by=self.user)
        other_folder = Folder.objects.create(name="Other", created_by=self.user)
        r = self.client.patch(
            f"/api/documents/{doc.id}/move/",
            {"folder_id": str(other_folder.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.folder_id, other_folder.id)

    def test_user_without_permission_cannot_retrieve(self):
        doc = Document.objects.create(title="Private", folder=self.folder, created_by=self.other)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x",
            file_size=0,
            created_by=self.other,
            is_current=True,
        )
        self.client.force_authenticate(user=self.user)
        r = self.client.get(f"/api/documents/{doc.id}/")
        self.assertIn(r.status_code, (403, 404))

    def test_attachments_upload_list_delete(self):
        doc = Document.objects.create(title="D", folder=self.folder, created_by=self.user)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x",
            file_size=0,
            created_by=self.user,
            is_current=True,
        )
        f = SimpleUploadedFile("att.txt", b"attachment", content_type="text/plain")
        r = self.client.post(
            f"/api/documents/{doc.id}/attachments/",
            {"file": f, "description": "Note"},
            format="multipart",
        )
        self.assertEqual(r.status_code, 201)
        att_id = r.data["id"]
        r2 = self.client.get(f"/api/documents/{doc.id}/attachments/")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(r2.data), 1)
        r3 = self.client.delete(f"/api/documents/{doc.id}/attachments/{att_id}/")
        self.assertEqual(r3.status_code, 204)
        self.assertEqual(doc.attachments.count(), 0)
