from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User


class UserViewSetTest(TestCase):
    """Test API utenti."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.admin.is_staff = True
        self.admin.save()
        self.operator = User.objects.create_user(
            email="op@test.com",
            password="Op123!",
            first_name="Operator",
            last_name="User",
            role="OPERATOR",
        )
        self.operator.must_change_password = False
        self.operator.save()

    def test_list_anonymous_401(self):
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_operator_403(self):
        self.client.force_authenticate(user=self.operator)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_admin_200(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_create_admin_201(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/users/",
            {
                "email": "new@test.com",
                "first_name": "New",
                "last_name": "User",
                "role": "OPERATOR",
                "phone": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@test.com").exists())

    def test_me_returns_current_user(self):
        self.client.force_authenticate(user=self.operator)
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "op@test.com")

    def test_patch_self_200(self):
        self.client.force_authenticate(user=self.operator)
        response = self.client.patch(
            f"/api/users/{self.operator.id}/",
            {"first_name": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.first_name, "Updated")

    def test_patch_other_as_operator_403(self):
        self.client.force_authenticate(user=self.operator)
        response = self.client.patch(
            f"/api/users/{self.admin.id}/",
            {"first_name": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
