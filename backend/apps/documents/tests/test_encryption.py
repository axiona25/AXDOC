"""
Test cifratura documenti on-demand (FASE 04).
"""
import tempfile
import os
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.models import Document, DocumentVersion
from apps.documents.encryption import DocumentEncryption

User = get_user_model()


class DocumentEncryptionTest(TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"Hello secret content")
            path = f.name
        try:
            enc_path, salt_b64 = DocumentEncryption.encrypt_file(path, "MyPass123!")
            self.assertTrue(os.path.exists(enc_path))
            plain = DocumentEncryption.decrypt_file(enc_path, "MyPass123!")
            self.assertEqual(plain, b"Hello secret content")
            os.remove(enc_path)
        finally:
            os.remove(path)

    def test_decrypt_wrong_password_raises(self):
        from cryptography.exceptions import InvalidTag
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"data")
            path = f.name
        try:
            enc_path, _ = DocumentEncryption.encrypt_file(path, "RightPass")
            with self.assertRaises(InvalidTag):
                DocumentEncryption.decrypt_file(enc_path, "WrongPass")
            os.remove(enc_path)
        finally:
            os.remove(path)


class DocumentEncryptAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@doc.com",
            password="Admin123!",
            first_name="Admin",
            last_name="Doc",
            role="ADMIN",
        )
        self.client.force_authenticate(user=self.admin)
        self.doc = Document.objects.create(title="Test Doc", created_by=self.admin)
        self.version = DocumentVersion.objects.create(
            document=self.doc,
            version_number=1,
            is_encrypted=False,
        )
        self.version.file.save("test.txt", SimpleUploadedFile("test.txt", b"content"), save=True)

    def tearDown(self):
        if self.version and self.version.file:
            try:
                os.unlink(self.version.file.path)
            except (OSError, ValueError):
                pass

    def test_encrypt_creates_new_version(self):
        response = self.client.post(
            f"/api/documents/{self.doc.id}/encrypt/",
            {"password": "SecurePass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_version", response.data)
        self.assertEqual(response.data["new_version"], 2)
        new_ver = DocumentVersion.objects.get(document=self.doc, version_number=2)
        self.assertTrue(new_ver.is_encrypted)
        self.assertTrue(new_ver.encryption_salt)
