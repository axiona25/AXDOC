"""Test WebSocket NotificationConsumer (FASE 23)."""
import asyncio

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.models import Notification
from config.asgi import application

User = get_user_model()


def _origin_headers():
    return [(b"origin", b"http://localhost")]


@pytest.mark.django_db(transaction=True)
class TestNotificationConsumer:
    def test_unauthenticated_connection_rejected(self):
        async def run():
            comm = WebsocketCommunicator(
                application,
                "/ws/notifications/",
                headers=_origin_headers(),
            )
            connected, _ = await comm.connect()
            assert connected is False
            await comm.disconnect()

        asyncio.run(run())

    def test_authenticated_receives_unread_count_on_connect(self):
        user = User.objects.create_user(
            email="ws_u1@test.com",
            password="x",
            first_name="A",
            last_name="B",
        )
        Notification.objects.create(
            recipient=user,
            notification_type="system",
            title="T",
            body="B",
            is_read=False,
        )
        token = str(RefreshToken.for_user(user).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={token}",
                headers=_origin_headers(),
            )
            connected, _ = await comm.connect()
            assert connected is True
            msg = await comm.receive_json_from()
            assert msg["type"] == "unread_count"
            assert msg["count"] == 1
            await comm.disconnect()

        asyncio.run(run())

    def test_mark_read_via_websocket(self):
        user = User.objects.create_user(
            email="ws_u2@test.com",
            password="x",
            first_name="A",
            last_name="B",
        )
        n = Notification.objects.create(
            recipient=user,
            notification_type="system",
            title="T",
            body="B",
            is_read=False,
        )
        token = str(RefreshToken.for_user(user).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={token}",
                headers=_origin_headers(),
            )
            await comm.connect()
            await comm.receive_json_from()
            await comm.send_json_to(
                {"type": "mark_read", "notification_id": str(n.id)}
            )
            msg = await comm.receive_json_from()
            assert msg["type"] == "unread_count"
            assert msg["count"] == 0
            await comm.disconnect()

        asyncio.run(run())
        n.refresh_from_db()
        assert n.is_read is True

    def test_mark_all_read_via_websocket(self):
        user = User.objects.create_user(
            email="ws_u3@test.com",
            password="x",
            first_name="A",
            last_name="B",
        )
        Notification.objects.create(
            recipient=user,
            notification_type="system",
            title="T1",
            body="B",
            is_read=False,
        )
        Notification.objects.create(
            recipient=user,
            notification_type="system",
            title="T2",
            body="B",
            is_read=False,
        )
        token = str(RefreshToken.for_user(user).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={token}",
                headers=_origin_headers(),
            )
            await comm.connect()
            await comm.receive_json_from()
            await comm.send_json_to({"type": "mark_all_read"})
            msg = await comm.receive_json_from()
            assert msg["type"] == "unread_count"
            assert msg["count"] == 0
            await comm.disconnect()

        asyncio.run(run())
        assert Notification.objects.filter(recipient=user, is_read=False).count() == 0
