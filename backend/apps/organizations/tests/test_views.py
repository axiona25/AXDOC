"""Test API UO."""
from io import StringIO
import csv
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership

User = get_user_model()


class OrganizationalUnitViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin1!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.admin.is_staff = True
        self.admin.save()
        self.operator = User.objects.create_user(
            email="op@test.com",
            password="Op1!",
            first_name="Op",
            last_name="User",
            role="OPERATOR",
        )
        self.ou = OrganizationalUnit.objects.create(name="IT", code="IT")
        OrganizationalUnitMembership.objects.create(
            user=self.operator, organizational_unit=self.ou, role="OPERATOR"
        )

    def test_list_anonymous_401(self):
        response = self.client.get("/api/organizations/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_admin_200(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/organizations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_admin_201(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/organizations/",
            {"name": "HR", "code": "HR", "description": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(OrganizationalUnit.objects.filter(code="HR").exists())

    def test_create_duplicate_code_400(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/organizations/",
            {"name": "IT2", "code": "IT", "description": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tree_returns_roots(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/organizations/tree/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_mine_filter(self):
        self.client.force_authenticate(user=self.operator)
        response = self.client.get("/api/organizations/?mine=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", response.data)), 1)

    def test_add_member(self):
        new_user = User.objects.create_user(
            email="new@test.com", password="New1!", first_name="New", last_name="User"
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/organizations/{self.ou.id}/add_member/",
            {"user_id": str(new_user.id), "role": "REVIEWER"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            OrganizationalUnitMembership.objects.filter(
                user=new_user, organizational_unit=self.ou
            ).exists()
        )

    def test_export_csv(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"/api/organizations/{self.ou.id}/export/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0], ["Email", "Nome", "Ruolo UO", "Data ingresso"])
