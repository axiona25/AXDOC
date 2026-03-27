"""Rami views chat: 405, validazioni messaggi, upload, unread, chiamate."""
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import ChatMessage, ChatRoom
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Ch100", code=f"C{uuid.uuid4().hex[:5]}", tenant=tenant)


@pytest.fixture
def admin_peer(db, tenant, ou):
    admin = User.objects.create_user(
        email=f"ch-a-{uuid.uuid4().hex[:8]}@t.com",
        password="Test123!",
        role="ADMIN",
    )
    admin.tenant = tenant
    admin.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
    peer = User.objects.create_user(
        email=f"ch-p-{uuid.uuid4().hex[:8]}@t.com",
        password="Test123!",
        role="OPERATOR",
    )
    peer.tenant = tenant
    peer.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=peer, organizational_unit=ou, role="OPERATOR")
    return admin, peer


@pytest.fixture
def admin_client(admin_peer):
    admin, _ = admin_peer
    c = APIClient()
    c.force_authenticate(user=admin)
    return c, admin


@pytest.fixture
def direct_room(admin_peer):
    admin, peer = admin_peer
    return ChatRoom.get_or_create_direct(admin, peer)


@pytest.mark.django_db
class TestChatViewsCoverage:
    def test_room_update_partial_destroy_not_allowed(self, admin_client, direct_room):
        client, _ = admin_client
        rid = str(direct_room.id)
        assert client.put(f"/api/chat/rooms/{rid}/", {}).status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert client.patch(f"/api/chat/rooms/{rid}/", {}).status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert client.delete(f"/api/chat/rooms/{rid}/").status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_direct_user_not_found(self, admin_client):
        client, _ = admin_client
        r = client.post(
            "/api/chat/rooms/direct/",
            {"user_id": str(uuid.uuid4())},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_group_member_ids_must_be_list(self, admin_client):
        client, _ = admin_client
        r = client.post(
            "/api/chat/rooms/",
            {"name": "G", "member_ids": "not-a-list"},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_post_message_requires_content_or_file(self, admin_client, direct_room):
        client, _ = admin_client
        r = client.post(
            f"/api/chat/rooms/{direct_room.id}/messages/",
            {"content": "  "},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_post_message_with_image(self, admin_client, direct_room):
        client, _ = admin_client
        img = SimpleUploadedFile("x.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        r = client.post(
            f"/api/chat/rooms/{direct_room.id}/messages/",
            {"content": "", "image": img},
            format="multipart",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json().get("message_type") == "image"

    def test_post_message_with_file_attachment(self, admin_client, direct_room):
        client, _ = admin_client
        f = SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain")
        r = client.post(
            f"/api/chat/rooms/{direct_room.id}/messages/",
            {"content": "vedi", "file": f},
            format="multipart",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json().get("message_type") == "file"

    def test_upload_accepts_file_upload_field(self, admin_client, direct_room):
        client, _ = admin_client
        f = SimpleUploadedFile("u.txt", b"u", content_type="text/plain")
        r = client.post(
            f"/api/chat/rooms/{direct_room.id}/upload/",
            {"file_upload": f},
            format="multipart",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_upload_requires_file(self, admin_client, direct_room):
        client, _ = admin_client
        r = client.post(f"/api/chat/rooms/{direct_room.id}/upload/", {}, format="multipart")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_image_branch(self, admin_client, direct_room):
        client, _ = admin_client
        img = SimpleUploadedFile("z.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        r = client.post(
            f"/api/chat/rooms/{direct_room.id}/upload/",
            {"file": img},
            format="multipart",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json().get("message_type") == "image"

    def test_unread_count_respects_last_read_at(self, admin_client, direct_room):
        client, admin = admin_client
        client.post(f"/api/chat/rooms/{direct_room.id}/mark_read/")
        ChatMessage.objects.create(room=direct_room, sender=admin, content="after read")
        r = client.get("/api/chat/rooms/unread_count/")
        assert r.status_code == 200
        assert r.json().get("count", 0) >= 1

    def test_call_initiate_missing_target(self, admin_client):
        client, _ = admin_client
        r = client.post("/api/chat/calls/initiate/", {}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_call_initiate_target_not_found(self, admin_client):
        client, _ = admin_client
        r = client.post(
            "/api/chat/calls/initiate/",
            {"target_user_id": str(uuid.uuid4())},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_message_not_found(self, admin_client):
        client, _ = admin_client
        r = client.delete(f"/api/chat/messages/{uuid.uuid4()}/")
        assert r.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.notifications.services.NotificationService.send", side_effect=RuntimeError("x"))
    def test_call_initiate_survives_notification_error(self, _mock_send, admin_client, admin_peer):
        client, _ = admin_client
        _, peer = admin_peer
        r = client.post(
            "/api/chat/calls/initiate/",
            {"target_user_id": str(peer.id)},
            format="json",
        )
        assert r.status_code == 200
        assert "call_id" in r.json()

    @patch("apps.authentication.models.AuditLog.log", side_effect=RuntimeError("x"))
    def test_call_end_survives_audit_error(self, _mock_log, admin_client):
        client, _ = admin_client
        import uuid as u

        cid = u.uuid4()
        r = client.post(f"/api/chat/calls/{cid}/end/")
        assert r.status_code == 200
