"""
WebSocket consumer per segnalazione WebRTC videochiamate (FASE 13).
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .auth import get_user_from_scope


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = await self.get_user()
        if not user:
            await self.close(code=4001)
            return
        self.user = user
        self.call_id = self.scope["url_route"]["kwargs"]["call_id"]
        self.call_group = f"call_{self.call_id}"
        await self.channel_layer.group_add(self.call_group, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.call_group,
            {
                "type": "participant_joined",
                "user_id": str(self.user.id),
                "user_name": getattr(self.user, "email", str(self.user)),
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "user"):
            await self.channel_layer.group_send(
                self.call_group,
                {"type": "participant_left", "user_id": str(self.user.id)},
            )
            await self.channel_layer.group_discard(self.call_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        msg_type = data.get("type", "")
        payload = {
            "type": msg_type,
            "from_user_id": str(self.user.id),
            "from_user_name": getattr(self.user, "email", str(self.user)),
            **{k: v for k, v in data.items() if k not in ("type", "target_user_id")},
        }
        await self.channel_layer.group_send(self.call_group, payload)

    async def offer(self, event):
        await self.send_if_not_sender(event)

    async def answer(self, event):
        await self.send_if_not_sender(event)

    async def ice_candidate(self, event):
        await self.send_if_not_sender(event)

    async def call_ended(self, event):
        await self.send(text_data=json.dumps(event))

    async def participant_joined(self, event):
        await self.send(text_data=json.dumps(event))

    async def participant_left(self, event):
        await self.send(text_data=json.dumps(event))

    async def send_if_not_sender(self, event):
        if event.get("from_user_id") != str(self.user.id):
            await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_user(self):
        return get_user_from_scope(self.scope)
