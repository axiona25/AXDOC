"""Copertura mirata apps.chat.consumers (WebsocketCommunicator, DB async)."""
import asyncio
import uuid

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chat.models import ChatMembership, ChatMessage, ChatRoom
from config.asgi import application

User = get_user_model()


def _origin_headers():
    return [(b"origin", b"http://localhost")]


@pytest.mark.django_db(transaction=True)
class TestChatConsumerExtended:
    def test_unauthenticated_closed_4001(self):
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

    def test_non_member_closed_4003(self):
        u1 = User.objects.create_user(
            email="chw0a@test.com", password="x", first_name="A", last_name="B", role="OPERATOR"
        )
        u2 = User.objects.create_user(
            email="chw0b@test.com", password="x", first_name="C", last_name="D", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="R0", created_by=u1)
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

    def test_invalid_json_ignored(self):
        u = User.objects.create_user(
            email="chw1@test.com", password="x", first_name="A", last_name="B", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="R1", created_by=u)
        ChatMembership.objects.create(room=room, user=u)
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={token}",
                headers=_origin_headers(),
            )
            assert (await comm.connect())[0]
            await comm.receive_json_from()
            await comm.send_to(text_data="not-valid-json{{{")
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(comm.receive_json_from(), timeout=0.35)
            await comm.disconnect()

        asyncio.run(run())

    def test_empty_chat_message_no_broadcast(self):
        u = User.objects.create_user(
            email="chw2@test.com", password="x", first_name="C", last_name="D", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="R2", created_by=u)
        ChatMembership.objects.create(room=room, user=u)
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={token}",
                headers=_origin_headers(),
            )
            assert (await comm.connect())[0]
            await comm.receive_json_from()
            await comm.send_json_to({"type": "chat_message", "content": ""})
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(comm.receive_json_from(), timeout=0.35)
            await comm.disconnect()

        asyncio.run(run())

    def test_mark_read_updates_membership(self):
        u = User.objects.create_user(
            email="chw3@test.com", password="x", first_name="E", last_name="F", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="R3", created_by=u)
        m = ChatMembership.objects.create(room=room, user=u)
        assert m.last_read_at is None
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={token}",
                headers=_origin_headers(),
            )
            assert (await comm.connect())[0]
            await comm.receive_json_from()
            await comm.send_json_to({"type": "mark_read"})
            await asyncio.sleep(0.15)
            await comm.disconnect()

        asyncio.run(run())
        m.refresh_from_db()
        assert m.last_read_at is not None

    def test_reply_to_without_content_creates_message(self):
        u = User.objects.create_user(
            email="chw4@test.com", password="x", first_name="G", last_name="H", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="R4", created_by=u)
        ChatMembership.objects.create(room=room, user=u)
        root = ChatMessage.objects.create(
            room=room, sender=u, message_type="text", content="root"
        )
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={token}",
                headers=_origin_headers(),
            )
            assert (await comm.connect())[0]
            await comm.receive_json_from()
            await comm.send_json_to({"type": "chat_message", "content": "", "reply_to": str(root.id)})
            msg = await asyncio.wait_for(comm.receive_json_from(), timeout=2)
            assert msg["type"] == "chat_message"
            assert msg.get("reply_to") == str(root.id)
            await comm.disconnect()

        asyncio.run(run())

    def test_typing_reaches_peer_not_self(self):
        u1 = User.objects.create_user(
            email="chw5a@test.com", password="x", first_name="I", last_name="J", role="OPERATOR"
        )
        u2 = User.objects.create_user(
            email="chw5b@test.com", password="x", first_name="K", last_name="L", role="OPERATOR"
        )
        room = ChatRoom.objects.create(room_type="group", name="R5", created_by=u1)
        ChatMembership.objects.create(room=room, user=u1)
        ChatMembership.objects.create(room=room, user=u2)
        t1 = str(RefreshToken.for_user(u1).access_token)
        t2 = str(RefreshToken.for_user(u2).access_token)

        async def run():
            c1 = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={t1}",
                headers=_origin_headers(),
            )
            c2 = WebsocketCommunicator(
                application,
                f"/ws/chat/{room.id}/?token={t2}",
                headers=_origin_headers(),
            )
            assert (await c1.connect())[0]
            assert (await c2.connect())[0]
            await c1.receive_json_from()
            await c1.receive_json_from()
            await c2.receive_json_from()
            await c1.send_json_to({"type": "typing"})
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(c1.receive_json_from(), timeout=0.35)
            ev = await asyncio.wait_for(c2.receive_json_from(), timeout=2)
            assert ev["type"] == "typing"
            assert ev["user_id"] == str(u1.id)
            await c1.disconnect()
            await c2.disconnect()

        asyncio.run(run())


@pytest.mark.django_db(transaction=True)
class TestPresenceConsumerWs:
    def test_presence_unauthenticated_closed(self):
        async def run():
            comm = WebsocketCommunicator(
                application,
                "/ws/presence/",
                headers=_origin_headers(),
            )
            connected, _ = await comm.connect()
            assert connected is False
            await comm.disconnect()

        asyncio.run(run())

    def test_connect_broadcast_online(self):
        u = User.objects.create_user(
            email="pr1@test.com", password="x", first_name="M", last_name="N", role="OPERATOR"
        )
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/presence/?token={token}",
                headers=_origin_headers(),
            )
            assert (await comm.connect())[0]
            msg = await asyncio.wait_for(comm.receive_json_from(), timeout=2)
            assert msg["type"] == "user_online"
            assert msg["user_id"] == str(u.id)
            await comm.disconnect()

        asyncio.run(run())

    def test_second_user_online_notify_first(self):
        u1 = User.objects.create_user(
            email="pr2a@test.com", password="x", first_name="O", last_name="P", role="OPERATOR"
        )
        u2 = User.objects.create_user(
            email="pr2b@test.com", password="x", first_name="Q", last_name="R", role="OPERATOR"
        )
        t1 = str(RefreshToken.for_user(u1).access_token)
        t2 = str(RefreshToken.for_user(u2).access_token)

        async def run():
            c1 = WebsocketCommunicator(
                application,
                f"/ws/presence/?token={t1}",
                headers=_origin_headers(),
            )
            c2 = WebsocketCommunicator(
                application,
                f"/ws/presence/?token={t2}",
                headers=_origin_headers(),
            )
            assert (await c1.connect())[0]
            first = await asyncio.wait_for(c1.receive_json_from(), timeout=2)
            assert first["type"] == "user_online"
            assert (await c2.connect())[0]
            await asyncio.wait_for(c2.receive_json_from(), timeout=2)
            seen_u2 = False
            for _ in range(5):
                m = await asyncio.wait_for(c1.receive_json_from(), timeout=2)
                if m.get("type") == "user_online" and m.get("user_id") == str(u2.id):
                    seen_u2 = True
                    break
            assert seen_u2
            await c2.disconnect()
            off = await asyncio.wait_for(c1.receive_json_from(), timeout=2)
            assert off["type"] == "user_offline"
            assert off["user_id"] == str(u2.id)
            await c1.disconnect()

        asyncio.run(run())
