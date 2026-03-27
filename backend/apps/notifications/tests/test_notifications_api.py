"""
Test API notifiche FASE 12.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import Notification
from apps.notifications.views import NotificationViewSet

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_a(db):
    return User.objects.create_user(email="user_a@test.com", password="test")


@pytest.fixture
def user_b(db):
    return User.objects.create_user(email="user_b@test.com", password="test")


@pytest.mark.django_db
class TestNotificationAPI:
    def test_list_only_own(self, api_client, user_a, user_b):
        Notification.objects.create(recipient=user_a, notification_type="system", title="T1", body="B1")
        Notification.objects.create(recipient=user_b, notification_type="system", title="T2", body="B2")
        api_client.force_authenticate(user=user_a)
        r = api_client.get("/api/notifications/")
        assert r.status_code == 200
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        assert len(results) == 1
        assert results[0]["title"] == "T1"

    def test_unread_filter(self, api_client, user_a):
        Notification.objects.create(recipient=user_a, notification_type="system", title="T1", body="B1", is_read=False)
        Notification.objects.create(recipient=user_a, notification_type="system", title="T2", body="B2", is_read=True)
        api_client.force_authenticate(user=user_a)
        r = api_client.get("/api/notifications/?unread=true")
        assert r.status_code == 200
        results = r.json().get("results", r.json())
        assert len(results) == 1
        assert results[0]["title"] == "T1"

    def test_mark_read_single(self, api_client, user_a):
        n = Notification.objects.create(recipient=user_a, notification_type="system", title="T1", body="B1", is_read=False)
        api_client.force_authenticate(user=user_a)
        r = api_client.post("/api/notifications/mark_read/", {"ids": [str(n.id)]}, format="json")
        assert r.status_code == 200
        assert r.json().get("marked") == 1
        n.refresh_from_db()
        assert n.is_read is True

    def test_mark_read_all(self, api_client, user_a):
        Notification.objects.create(recipient=user_a, notification_type="system", title="T1", body="B1", is_read=False)
        Notification.objects.create(recipient=user_a, notification_type="system", title="T2", body="B2", is_read=False)
        api_client.force_authenticate(user=user_a)
        r = api_client.post("/api/notifications/mark_read/", {"all": True}, format="json")
        assert r.status_code == 200
        assert r.json().get("marked") == 2

    def test_unread_count(self, api_client, user_a):
        Notification.objects.create(recipient=user_a, notification_type="system", title="T1", body="B1", is_read=False)
        Notification.objects.create(recipient=user_a, notification_type="system", title="T2", body="B2", is_read=True)
        api_client.force_authenticate(user=user_a)
        r = api_client.get("/api/notifications/unread_count/")
        assert r.status_code == 200
        assert r.json()["count"] == 1

    def test_retrieve_marks_read(self, api_client, user_a):
        n = Notification.objects.create(recipient=user_a, notification_type="system", title="T1", body="B1", is_read=False)
        api_client.force_authenticate(user=user_a)
        api_client.get(f"/api/notifications/{n.id}/")
        n.refresh_from_db()
        assert n.is_read is True

    def test_read_filter_and_poll(self, api_client, user_a):
        Notification.objects.create(recipient=user_a, notification_type="system", title="R1", body="B", is_read=False)
        Notification.objects.create(recipient=user_a, notification_type="system", title="R2", body="B", is_read=True)
        api_client.force_authenticate(user=user_a)
        r = api_client.get("/api/notifications/", {"read": "true"})
        assert r.status_code == 200
        rows = r.json().get("results", r.json())
        assert len(rows) == 1
        assert rows[0]["title"] == "R2"

        r2 = api_client.get("/api/notifications/poll/")
        assert r2.status_code == 200
        assert r2.json().get("unread_count") == 1

    def test_list_paginated_response(self, api_client, user_a):
        n = Notification.objects.create(
            recipient=user_a, notification_type="system", title="Pag1", body="B", is_read=True
        )
        api_client.force_authenticate(user=user_a)
        with patch.object(NotificationViewSet, "paginate_queryset", return_value=[n]):
            with patch.object(
                NotificationViewSet,
                "get_paginated_response",
                side_effect=lambda data: Response({"paginated": True, "results": data}),
            ):
                r = api_client.get("/api/notifications/")
        assert r.status_code == 200
        body = r.json()
        assert body.get("paginated") is True
        assert len(body.get("results", [])) >= 1

    def test_mark_read_empty_ids_returns_zero(self, api_client, user_a):
        api_client.force_authenticate(user=user_a)
        r = api_client.post("/api/notifications/mark_read/", {"ids": []}, format="json")
        assert r.status_code == 200
        assert r.json().get("marked") == 0
