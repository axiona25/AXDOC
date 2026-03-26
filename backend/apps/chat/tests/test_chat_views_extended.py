"""Test estesi ChatRoomViewSet e endpoint correlati (FASE 33D)."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import ChatMessage, ChatMembership, ChatRoom
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
    return OrganizationalUnit.objects.create(name="Chat OU", code="CHOU", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="chat-ext-admin@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="C",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def peer_user(db, tenant, ou):
    u = User.objects.create_user(
        email="chat-ext-peer@test.com",
        password="Peer123456!",
        role="OPERATOR",
        first_name="P",
        last_name="E",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def chat_room_direct(db, admin_user, peer_user):
    return ChatRoom.get_or_create_direct(admin_user, peer_user)


@pytest.mark.django_db
class TestChatViewsExtended:
    def test_list_rooms(self, admin_client, chat_room_direct):
        r = admin_client.get("/api/chat/rooms/")
        assert r.status_code == 200
        data = r.json()
        assert "results" in data or isinstance(data, list)

    def test_create_direct_chat(self, admin_client, peer_user):
        r = admin_client.post(
            "/api/chat/rooms/direct/",
            {"user_id": str(peer_user.id)},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        assert "id" in r.json()

    def test_create_direct_missing_user_id(self, admin_client):
        r = admin_client.post("/api/chat/rooms/direct/", {}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_direct_with_self(self, admin_client, admin_user):
        r = admin_client.post(
            "/api/chat/rooms/direct/",
            {"user_id": str(admin_user.id)},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_group_missing_name(self, admin_client, peer_user):
        r = admin_client.post(
            "/api/chat/rooms/",
            {"name": "", "member_ids": [str(peer_user.id)]},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_messages_list(self, admin_client, chat_room_direct, admin_user):
        ChatMessage.objects.create(room=chat_room_direct, sender=admin_user, content="Hi")
        r = admin_client.get(f"/api/chat/rooms/{chat_room_direct.id}/messages/")
        assert r.status_code == 200
        assert len(r.json().get("results", [])) >= 1

    def test_send_message(self, admin_client, chat_room_direct):
        r = admin_client.post(
            f"/api/chat/rooms/{chat_room_direct.id}/messages/",
            {"content": "Hello extended"},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_mark_read(self, admin_client, chat_room_direct):
        r = admin_client.post(f"/api/chat/rooms/{chat_room_direct.id}/mark_read/")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_members_list(self, admin_client, chat_room_direct):
        r = admin_client.get(f"/api/chat/rooms/{chat_room_direct.id}/members/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_upload_file_to_chat(self, admin_client, chat_room_direct):
        from django.core.files.uploadedfile import SimpleUploadedFile

        f = SimpleUploadedFile("chat-ext.txt", b"chat file", content_type="text/plain")
        r = admin_client.post(
            f"/api/chat/rooms/{chat_room_direct.id}/upload/",
            {"file": f},
            format="multipart",
        )
        assert r.status_code == status.HTTP_201_CREATED

    def test_unread_count(self, admin_client, chat_room_direct, admin_user):
        ChatMessage.objects.create(room=chat_room_direct, sender=admin_user, content="unread")
        r = admin_client.get("/api/chat/rooms/unread_count/")
        assert r.status_code == 200
        assert "count" in r.json()

    def test_create_group_room(self, admin_client, peer_user):
        r = admin_client.post(
            "/api/chat/rooms/",
            {"name": "Team", "member_ids": [str(peer_user.id)]},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json().get("room_type") == "group"

    def test_delete_own_message(self, admin_client, chat_room_direct, admin_user):
        m = ChatMessage.objects.create(room=chat_room_direct, sender=admin_user, content="del me")
        r = admin_client.delete(f"/api/chat/messages/{m.id}/")
        assert r.status_code == status.HTTP_204_NO_CONTENT
        m.refresh_from_db()
        assert m.is_deleted is True

    @patch("apps.notifications.services.NotificationService.send")
    def test_call_initiate(self, mock_send, admin_client, peer_user):
        r = admin_client.post(
            "/api/chat/calls/initiate/",
            {"target_user_id": str(peer_user.id)},
            format="json",
        )
        assert r.status_code == 200
        body = r.json()
        assert "call_id" in body and "ws_url" in body

    def test_call_end(self, admin_client):
        import uuid

        cid = uuid.uuid4()
        r = admin_client.post(f"/api/chat/calls/{cid}/end/")
        assert r.status_code == 200

    def test_ice_servers(self, admin_client):
        r = admin_client.get("/api/chat/ice_servers/")
        assert r.status_code == 200
        assert "ice_servers" in r.json()

    def test_non_member_cannot_access_messages(self, db, tenant, ou, chat_room_direct, admin_user, peer_user):
        other = User.objects.create_user(
            email="chat-ext-other@test.com",
            password="Pass123!",
            role="OPERATOR",
            first_name="O",
            last_name="T",
        )
        other.tenant = tenant
        other.save(update_fields=["tenant"])
        OrganizationalUnitMembership.objects.create(user=other, organizational_unit=ou, role="OPERATOR")
        c = APIClient()
        c.force_authenticate(user=other)
        r = c.post(
            f"/api/chat/rooms/{chat_room_direct.id}/messages/",
            {"content": "Hi"},
            format="json",
        )
        assert r.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
