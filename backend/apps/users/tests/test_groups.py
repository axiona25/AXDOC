"""
Test gruppi utenti (RF-016).
"""
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.users.models import UserGroup, UserGroupMembership

User = get_user_model()


class UserGroupAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@groups.com",
            password="Admin123!",
            first_name="Admin",
            last_name="Groups",
            role="ADMIN",
        )
        self.client.force_authenticate(user=self.admin)

    def test_create_group(self):
        response = self.client.post(
            "/api/groups/",
            {"name": "Legale", "description": "Ufficio legale"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Legale")
        self.assertTrue(UserGroup.objects.filter(name="Legale").exists())

    def test_list_groups(self):
        UserGroup.objects.create(name="G1", is_active=True)
        response = self.client.get("/api/groups/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data.get("results", response.data)), 1)

    def test_add_members(self):
        group = UserGroup.objects.create(name="Team A", is_active=True)
        u1 = User.objects.create_user(email="u1@test.com", password="x", first_name="U", last_name="1")
        response = self.client.post(
            f"/api/groups/{group.id}/add_members/",
            {"user_ids": [str(u1.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["added"], 1)
        self.assertTrue(UserGroupMembership.objects.filter(group=group, user=u1).exists())

    def test_remove_member(self):
        group = UserGroup.objects.create(name="Team B", is_active=True)
        u2 = User.objects.create_user(email="u2@test.com", password="x", first_name="U", last_name="2")
        UserGroupMembership.objects.create(group=group, user=u2, added_by=self.admin)
        response = self.client.delete(f"/api/groups/{group.id}/remove_member/{u2.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(UserGroupMembership.objects.filter(group=group, user=u2).exists())
