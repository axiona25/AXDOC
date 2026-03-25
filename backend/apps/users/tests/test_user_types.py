"""
Test user_type (internal/guest), IsInternalUser, create_manual, change_type. FASE 17.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.documents.models import Document, DocumentPermission
from apps.protocols.models import Protocol


class UserTypePermissionTest(TestCase):
    """Test che gli ospiti non accedono a protocolli, fascicoli, metadata, UO, list users."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
            user_type="internal",
        )
        self.admin.is_staff = True
        self.admin.save()
        self.guest = User.objects.create_user(
            email="guest@test.com",
            password="Guest123!",
            first_name="Guest",
            last_name="User",
            role="OPERATOR",
            user_type="guest",
        )
        self.guest.must_change_password = False
        self.guest.save()

    def test_guest_cannot_list_protocols(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.get("/api/protocols/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_cannot_list_dossiers(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.get("/api/dossiers/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_cannot_list_metadata_structures(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.get("/api/metadata/structures/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_cannot_list_organizational_units(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.get("/api/organizations/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_cannot_list_users(self):
        self.client.force_authenticate(user=self.guest)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_internal_can_list_protocols(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/protocols/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_manual_creates_user_with_user_type(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/users/create_manual/",
            {
                "email": "manual@test.com",
                "first_name": "Manual",
                "last_name": "User",
                "user_type": "guest",
                "send_welcome_email": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["user_type"], "guest")
        self.assertEqual(response.data["user"]["role"], "OPERATOR")
        user = User.objects.get(email="manual@test.com")
        self.assertTrue(user.is_guest)

    def test_change_type_updates_user_type(self):
        self.client.force_authenticate(user=self.admin)
        internal_user = User.objects.create_user(
            email="tochange@test.com",
            password="Change123!",
            first_name="To",
            last_name="Change",
            user_type="internal",
            role="OPERATOR",
        )
        response = self.client.post(
            f"/api/users/{internal_user.id}/change_type/",
            {"user_type": "guest"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        internal_user.refresh_from_db()
        self.assertEqual(internal_user.user_type, "guest")
        self.assertEqual(internal_user.role, "OPERATOR")

    def test_guest_sees_only_documents_with_explicit_permission(self):
        """L'ospite vede in list solo documenti per cui ha DocumentPermission can_read."""
        from apps.documents.permissions import _documents_queryset_filter

        creator = User.objects.create_user(
            email="creator@test.com",
            password="Creator123!",
            first_name="Creator",
            last_name="User",
            user_type="internal",
        )
        doc_shared = Document.objects.create(
            title="Shared with guest",
            created_by=creator,
            is_deleted=False,
        )
        doc_not_shared = Document.objects.create(
            title="Not shared",
            created_by=creator,
            is_deleted=False,
        )
        DocumentPermission.objects.create(document=doc_shared, user=self.guest, can_read=True)
        qs_filter = _documents_queryset_filter(self.guest)
        visible = Document.objects.filter(is_deleted=False).filter(qs_filter).distinct()
        self.assertIn(doc_shared, visible)
        self.assertNotIn(doc_not_shared, visible)
