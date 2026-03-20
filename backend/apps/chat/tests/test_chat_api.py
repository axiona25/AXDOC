"""
Test API Chat FASE 13.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.chat.models import ChatRoom, ChatMessage, ChatMembership
from apps.documents.models import Document, Folder

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_a(db):
    return User.objects.create_user(email="chata@test.com", password="test")

@pytest.fixture
def user_b(db):
    return User.objects.create_user(email="chatb@test.com", password="test")


@pytest.mark.django_db
class TestChatAPI:
    def test_create_direct_same_room_twice(self, api_client, user_a, user_b):
        api_client.force_authenticate(user=user_a)
        r1 = api_client.post("/api/chat/rooms/direct/", {"user_id": str(user_b.id)}, format="json")
        assert r1.status_code == status.HTTP_200_OK
        room_id_1 = r1.json()["id"]
        r2 = api_client.post("/api/chat/rooms/direct/", {"user_id": str(user_b.id)}, format="json")
        assert r2.status_code == status.HTTP_200_OK
        assert r2.json()["id"] == room_id_1

    def test_send_message_rest(self, api_client, user_a, user_b):
        room = ChatRoom.get_or_create_direct(user_a, user_b)
        api_client.force_authenticate(user=user_a)
        r = api_client.post(
            f"/api/chat/rooms/{room.id}/messages/",
            {"content": "Ciao!"},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        assert r.json()["content"] == "Ciao!"
        assert ChatMessage.objects.filter(room=room).count() == 1

    def test_messages_list(self, api_client, user_a, user_b):
        room = ChatRoom.get_or_create_direct(user_a, user_b)
        ChatMessage.objects.create(room=room, sender=user_a, content="Test")
        api_client.force_authenticate(user=user_a)
        r = api_client.get(f"/api/chat/rooms/{room.id}/messages/")
        assert r.status_code == 200
        assert len(r.json().get("results", [])) == 1

    def test_document_chat(self, api_client, user_a, user_b):
        folder = Folder.objects.create(name="F")
        doc = Document.objects.create(title="Doc", folder=folder, created_by=user_a)
        api_client.force_authenticate(user=user_a)
        r = api_client.post(f"/api/documents/{doc.id}/chat/")
        assert r.status_code == 200
        assert r.json()["room_type"] == "document"
        assert r.json()["document_id"] == str(doc.id)
