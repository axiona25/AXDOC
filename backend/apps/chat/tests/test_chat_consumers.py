"""Test WebSocket ChatConsumer e CallConsumer (FASE 33B)."""
import asyncio
import uuid

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chat.models import ChatMembership, ChatRoom
from config.asgi import application

User = get_user_model()


def _origin_headers():
    return [(b"origin", b"http://localhost")]


@pytest.mark.django_db(transaction=True)
class TestChatConsumer:
    def test_unauthenticated_closed(self):
        rid = uuid.uuid4()

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/chat/{rid}/",
                headers=_origin_headers(),
            )
            connected, _ = await comm.connect()
            assert connected is False
            await comm.disconnect()

        asyncio.run(run())

    def test_non_member_closed(self):
        u1 = User.objects.create_user(
            email="ch1@test.com", password="x", first_name="A", last_name="B", role="OPERATOR"
        )
        u2 = User.objects.create_user(
            email="ch2@test.com", password="x", first_name="C", last_name="D", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="G", created_by=u1)
        ChatMembership.objects.create(room=room, user=u1)
        token = str(RefreshToken.for_user(u2).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={token}",
                headers=_origin_headers(),
            )
            connected, _ = await comm.connect()
            assert connected is False
            await comm.disconnect()

        asyncio.run(run())

    def test_member_sends_chat_message(self):
        u = User.objects.create_user(
            email="ch3@test.com", password="x", first_name="E", last_name="F", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="R", created_by=u)
        ChatMembership.objects.create(room=room, user=u)
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={token}",
                headers=_origin_headers(),
            )
            connected, _ = await comm.connect()
            assert connected is True
            first = await comm.receive_json_from()
            assert first.get("type") in ("user_joined", "chat_message")
            await comm.send_json_to({"type": "chat_message", "content": "ciao"})
            msg = await comm.receive_json_from()
            assert msg["type"] == "chat_message"
            assert msg["content"] == "ciao"
            await comm.send_json_to({"type": "typing"})
            await comm.disconnect()

        asyncio.run(run())


@pytest.mark.django_db(transaction=True)
class TestCallConsumer:
    def test_offer_received_by_peer(self):
        u1 = User.objects.create_user(
            email="ca1@test.com", password="x", first_name="A", last_name="B", role="OPERATOR"
        )
        u2 = User.objects.create_user(
            email="ca2@test.com", password="x", first_name="C", last_name="D", role="OPERATOR"
        )
        call_id = uuid.uuid4()
        t1 = str(RefreshToken.for_user(u1).access_token)
        t2 = str(RefreshToken.for_user(u2).access_token)

        async def run():
            c1 = WebsocketCommunicator(
                application,
                f"/ws/call/{call_id}/?token={t1}",
                headers=_origin_headers(),
            )
            c2 = WebsocketCommunicator(
                application,
                f"/ws/call/{call_id}/?token={t2}",
                headers=_origin_headers(),
            )
            assert (await c1.connect())[0]
            assert (await c2.connect())[0]
            await c1.send_json_to({"type": "offer", "sdp": "fake-sdp"})
            got = None
            for _ in range(6):
                raw = await asyncio.wait_for(c2.receive_json_from(), timeout=2)
                if raw.get("type") == "offer":
                    got = raw
                    break
            assert got is not None
            assert got.get("sdp") == "fake-sdp"
            await c1.disconnect()
            await c2.disconnect()

        asyncio.run(run())
