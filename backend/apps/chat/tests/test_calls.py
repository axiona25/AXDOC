"""Test API chiamate video (FASE 13)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_a(db):
    return User.objects.create_user(email="calla@test.com", password="test")


@pytest.fixture
def user_b(db):
    return User.objects.create_user(email="callb@test.com", password="test")


@pytest.mark.django_db
class TestCallAPI:
    def test_initiate_call_returns_call_id_and_ws_url(self, api_client, user_a, user_b):
        api_client.force_authenticate(user=user_a)
        r = api_client.post(
            "/api/chat/calls/initiate/",
            {"target_user_id": str(user_b.id)},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert "call_id" in data
        assert "ws_url" in data
        assert "ws/call/" in data["ws_url"]

    def test_ice_servers_returns_list(self, api_client, user_a):
        api_client.force_authenticate(user=user_a)
        r = api_client.get("/api/chat/ice_servers/")
        assert r.status_code == 200
        assert "ice_servers" in r.json()
        assert isinstance(r.json()["ice_servers"], list)

    def test_end_call_returns_ok(self, api_client, user_a):
        import uuid
        call_id = uuid.uuid4()
        api_client.force_authenticate(user=user_a)
        r = api_client.post(f"/api/chat/calls/{call_id}/end/")
        assert r.status_code == 200
        assert r.json().get("ok") is True
