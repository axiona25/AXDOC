"""
WebSocket consumers per chat e presenza (FASE 13).
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .auth import get_user_from_scope
from .models import ChatRoom, ChatMessage, ChatMembership, UserPresence


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = await self.get_user()
        if not user:
            await self.close(code=4001)
            return
        self.user = user
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        in_room = await self.user_in_room(self.user.id, self.room_id)
        if not in_room:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.set_online(self.user.id, self.room_id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_joined",
                "user_id": str(self.user.id),
                "user_name": getattr(self.user, "email", str(self.user)),
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "user"):
            await self.set_offline(self.user.id)
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        action = data.get("type")
        if action == "chat_message":
            msg = await self.save_message(
                self.user.id,
                self.room_id,
                data.get("content", ""),
                data.get("reply_to"),
            )
            if msg:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message_id": str(msg.id),
                        "content": msg.content,
                        "sender_id": str(self.user.id),
                        "sender_name": getattr(self.user, "email", str(self.user)),
                        "sent_at": msg.sent_at.isoformat(),
                        "reply_to": data.get("reply_to"),
                    },
                )
        elif action == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing",
                    "user_id": str(self.user.id),
                    "user_name": getattr(self.user, "email", str(self.user)),
                },
            )
        elif action == "mark_read":
            await self.update_last_read(self.user.id, self.room_id)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "chat_message", **event}))

    async def typing(self, event):
        if event.get("user_id") != str(self.user.id):
            await self.send(text_data=json.dumps({"type": "typing", **event}))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({"type": "user_joined", **event}))

    @database_sync_to_async
    def get_user(self):
        return get_user_from_scope(self.scope)

    @database_sync_to_async
    def user_in_room(self, user_id, room_id):
        return ChatMembership.objects.filter(room_id=room_id, user_id=user_id).exists()

    @database_sync_to_async
    def save_message(self, user_id, room_id, content, reply_to):
        if not content and not reply_to:
            return None
        msg = ChatMessage.objects.create(
            room_id=room_id,
            sender_id=user_id,
            message_type="text",
            content=content or "",
            reply_to_id=reply_to,
        )
        return msg

    @database_sync_to_async
    def set_online(self, user_id, room_id):
        pres, _ = UserPresence.objects.get_or_create(user_id=user_id, defaults={"is_online": True})
        pres.is_online = True
        pres.current_room_id = room_id
        pres.last_seen = timezone.now()
        pres.save(update_fields=["is_online", "current_room_id", "last_seen"])

    @database_sync_to_async
    def set_offline(self, user_id):
        UserPresence.objects.filter(user_id=user_id).update(is_online=False, current_room_id=None)

    @database_sync_to_async
    def update_last_read(self, user_id, room_id):
        now = timezone.now()
        ChatMembership.objects.filter(room_id=room_id, user_id=user_id).update(last_read_at=now)


class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = await self.get_user()
        if not user:
            await self.close()
            return
        self.user = user
        await self.channel_layer.group_add("presence", self.channel_name)
        await self.accept()
        await self.set_online(self.user.id)
        await self.channel_layer.group_send(
            "presence",
            {"type": "user_online", "user_id": str(self.user.id)},
        )

    async def disconnect(self, close_code):
        if hasattr(self, "user"):
            await self.set_offline(self.user.id)
            await self.channel_layer.group_send(
                "presence",
                {"type": "user_offline", "user_id": str(self.user.id)},
            )
            await self.channel_layer.group_discard("presence", self.channel_name)

    async def user_online(self, event):
        await self.send(text_data=json.dumps(event))

    async def user_offline(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_user(self):
        return get_user_from_scope(self.scope)

    @database_sync_to_async
    def set_online(self, user_id):
        pres, _ = UserPresence.objects.get_or_create(user_id=user_id, defaults={"is_online": True})
        pres.is_online = True
        pres.last_seen = timezone.now()
        pres.save(update_fields=["is_online", "last_seen"])

    @database_sync_to_async
    def set_offline(self, user_id):
        UserPresence.objects.filter(user_id=user_id).update(is_online=False, current_room_id=None)
