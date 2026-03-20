"""
Test API Cartelle (FASE 05).
"""
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.documents.models import Folder, Document

User = get_user_model()


class FolderAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            role="OPERATOR",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_root_folder(self):
        r = self.client.post("/api/folders/", {"name": "Root1"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["name"], "Root1")
        self.assertIsNone(r.data["parent_id"])
        self.assertIn("id", r.data)

    def test_create_subfolder(self):
        root = Folder.objects.create(name="Root", created_by=self.user)
        r = self.client.post(
            "/api/folders/",
            {"name": "Sub", "parent_id": str(root.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["name"], "Sub")
        self.assertEqual(r.data["parent_id"], str(root.id))

    def test_duplicate_name_same_parent_returns_400(self):
        root = Folder.objects.create(name="Root", created_by=self.user)
        Folder.objects.create(name="Esistente", parent=root, created_by=self.user)
        r = self.client.post(
            "/api/folders/",
            {"name": "Esistente", "parent_id": str(root.id)},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.data)

    def test_breadcrumb_three_levels(self):
        root = Folder.objects.create(name="Root", created_by=self.user)
        level1 = Folder.objects.create(name="L1", parent=root, created_by=self.user)
        level2 = Folder.objects.create(name="L2", parent=level1, created_by=self.user)
        r = self.client.get(f"/api/folders/{level2.id}/breadcrumb/")
        self.assertEqual(r.status_code, 200)
        names = [x["name"] for x in r.data]
        self.assertEqual(names, ["Root", "L1"])

    def test_soft_delete_empty_folder_returns_204(self):
        folder = Folder.objects.create(name="Vuota", created_by=self.user)
        r = self.client.delete(f"/api/folders/{folder.id}/")
        self.assertEqual(r.status_code, 204)
        folder.refresh_from_db()
        self.assertTrue(folder.is_deleted)

    def test_soft_delete_folder_with_documents_returns_400(self):
        folder = Folder.objects.create(name="ConDoc", created_by=self.user)
        Document.objects.create(title="Doc", folder=folder, created_by=self.user)
        r = self.client.delete(f"/api/folders/{folder.id}/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("detail", r.data)

    def test_list_root_folders_excludes_soft_deleted(self):
        Folder.objects.create(name="Visibile", created_by=self.user)
        deleted = Folder.objects.create(name="Eliminata", created_by=self.user)
        deleted.is_deleted = True
        deleted.save()
        r = self.client.get("/api/folders/", {"parent_id": ""})
        self.assertEqual(r.status_code, 200)
        names = [x["name"] for x in r.data]
        self.assertIn("Visibile", names)
        self.assertNotIn("Eliminata", names)
