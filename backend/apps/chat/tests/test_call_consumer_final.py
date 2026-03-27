# FASE 35E.1 — Copertura: chat/call_consumer.py
import asyncio
import json
import uuid

import pytest
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application

from django.contrib.auth import get_user_model

User = get_user_model()


def _origin_headers():
    return [(b"origin", b"http://localhost")]


@pytest.mark.django_db(transaction=True)
class TestCallConsumerFinal:
    def test_connect_without_token_closes(self):
        cid = uuid.uuid4()

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/call/{cid}/",
                headers=_origin_headers(),
            )
            connected, _ = await comm.connect()
            assert connected is False
            await comm.disconnect()

        asyncio.run(run())

    def test_connect_send_offer_disconnect(self):
        u = User.objects.create_user(
            email="ccf@test.com",
            password="TestPass123!",
            first_name="C",
            last_name="F",
        )
        cid = uuid.uuid4()
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/call/{cid}/?token={token}",
                headers=_origin_headers(),
            )
            assert (await comm.connect())[0]
            await comm.send_json_to({"type": "offer", "sdp": "fake"})
            try:
                await asyncio.wait_for(comm.receive_json_from(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            await comm.disconnect()

        asyncio.run(run())

    def test_two_participants_offer_answer_ice_call_ended(self):
        ua = User.objects.create_user(
            email="ccf-a@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="A",
        )
        ub = User.objects.create_user(
            email="ccf-b@test.com",
            password="TestPass123!",
            first_name="B",
            last_name="B",
        )
        cid = uuid.uuid4()
        ta = str(RefreshToken.for_user(ua).access_token)
        tb = str(RefreshToken.for_user(ub).access_token)

        async def run():
            c1 = WebsocketCommunicator(
                application,
                f"/ws/call/{cid}/?token={ta}",
                headers=_origin_headers(),
            )
            c2 = WebsocketCommunicator(
                application,
                f"/ws/call/{cid}/?token={tb}",
                headers=_origin_headers(),
            )
            assert (await c1.connect())[0]
            assert (await c2.connect())[0]
            await c2.send_json_to({"type": "offer", "sdp": "o"})
            m1 = None
            for _ in range(40):
                msg = await c1.receive_json_from()
                if msg.get("type") == "offer":
                    m1 = msg
                    break
            assert m1 and m1.get("type") == "offer"
            await c1.send_json_to({"type": "answer", "sdp": "a"})
            m2 = None
            for _ in range(40):
                msg = await c2.receive_json_from()
                if msg.get("type") == "answer":
                    m2 = msg
                    break
            assert m2 and m2.get("type") == "answer"
            await c2.send_json_to({"type": "ice_candidate", "c": "x"})
            m3 = None
            for _ in range(40):
                msg = await c1.receive_json_from()
                if msg.get("type") == "ice_candidate":
                    m3 = msg
                    break
            assert m3 and m3.get("type") == "ice_candidate"
            await c2.send_json_to({"type": "call_ended"})
            m4 = None
            for _ in range(40):
                msg = await c1.receive_json_from()
                if msg.get("type") == "call_ended":
                    m4 = msg
                    break
            assert m4 and m4.get("type") == "call_ended"
            await c1.disconnect()
            await c2.disconnect()

        asyncio.run(run())

    def test_receive_invalid_json_noop(self):
        u = User.objects.create_user(
            email="ccf2@test.com",
            password="TestPass123!",
            first_name="C",
            last_name="F",
        )
        cid = uuid.uuid4()
        token = str(RefreshToken.for_user(u).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/call/{cid}/?token={token}",
                headers=_origin_headers(),
            )
            assert (await comm.connect())[0]
            await comm.send_to(text_data="not-json")
            await comm.disconnect()

        asyncio.run(run())
