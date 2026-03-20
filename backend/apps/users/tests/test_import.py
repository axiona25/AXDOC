"""
Test import utenti da CSV/Excel (RF-017).
"""
import csv
import io
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.users.importers import UserImporter, IMPORT_COLUMNS
from apps.organizations.models import OrganizationalUnit

User = get_user_model()


class UserImporterTest(TestCase):
    def setUp(self):
        self.importer = UserImporter()

    def test_get_template_csv_has_headers(self):
        csv_content = UserImporter.get_template_csv()
        reader = csv.DictReader(io.StringIO(csv_content))
        self.assertIn("email", (reader.fieldnames or []))
        self.assertIn("first_name", (reader.fieldnames or []))
        self.assertIn("role", (reader.fieldnames or []))

    def test_validate_row_valid(self):
        row = {
            "email": "new@test.com",
            "first_name": "Mario",
            "last_name": "Rossi",
            "role": "OPERATOR",
        }
        errors = self.importer.validate_row(row, 1)
        self.assertEqual(errors, [])

    def test_validate_row_missing_required(self):
        row = {"email": "x@test.com", "first_name": "", "last_name": "X", "role": "OPERATOR"}
        errors = self.importer.validate_row(row, 1)
        self.assertTrue(any("first_name" in e or "obbligatorio" in e for e in errors))

    def test_validate_row_duplicate_email(self):
        User.objects.create_user(
            email="existing@test.com",
            password="x",
            first_name="E",
            last_name="X",
        )
        row = {
            "email": "existing@test.com",
            "first_name": "M",
            "last_name": "R",
            "role": "OPERATOR",
        }
        errors = self.importer.validate_row(row, 1)
        self.assertTrue(any("esistente" in e for e in errors))

    def test_parse_csv(self):
        content = "email,first_name,last_name,role\nm@test.com,Mario,Rossi,OPERATOR"
        rows = self.importer.parse_file(io.BytesIO(content.encode("utf-8")), "csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("email"), "m@test.com")

    def test_import_users_creates_and_skips(self):
        User.objects.create_user(email="skip@test.com", password="x", first_name="S", last_name="K")
        rows = [
            {
                "email": "new1@test.com",
                "first_name": "N1",
                "last_name": "U1",
                "role": "OPERATOR",
            },
            {
                "email": "skip@test.com",
                "first_name": "S",
                "last_name": "K",
                "role": "OPERATOR",
            },
        ]
        report = self.importer.import_users(rows, send_invite=False)
        self.assertEqual(report["created"], 1)
        self.assertEqual(report["skipped"], 1)
        self.assertTrue(User.objects.filter(email="new1@test.com").exists())


class ImportAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@import.com",
            password="Admin123!",
            first_name="Admin",
            last_name="Import",
            role="ADMIN",
        )
        self.client.force_authenticate(user=self.admin)

    def test_template_csv_download(self):
        response = self.client.get("/api/users/import/template/?file_format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.get("Content-Disposition", ""))
        self.assertIn(b"email", response.content)

    def test_template_xlsx_download(self):
        response = self.client.get("/api/users/import/template/?file_format=xlsx")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.get("Content-Disposition", ""))

    def test_preview_without_file_400(self):
        response = self.client.post("/api/users/import/preview/")
        self.assertEqual(response.status_code, 400)

    def test_preview_csv_valid(self):
        csv_content = "email,first_name,last_name,role\npreview@test.com,P,Review,OPERATOR"
        response = self.client.post(
            "/api/users/import/preview/",
            {"file": __import__("django.core.files.uploadedfile", fromlist=["x"]).SimpleUploadedFile("users.csv", csv_content.encode("utf-8"), content_type="text/csv")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_rows"], 1)
        self.assertEqual(response.data["valid_rows"], 1)

    def test_import_requires_admin(self):
        other = User.objects.create_user(email="other@test.com", password="x", first_name="O", last_name="X", role="OPERATOR")
        self.client.force_authenticate(user=other)
        response = self.client.get("/api/users/import/template/?file_format=csv")
        self.assertEqual(response.status_code, 403)
