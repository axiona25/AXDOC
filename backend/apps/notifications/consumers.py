"""
WebSocket consumer: notifiche push real-time (FASE 23).
Autenticazione JWT via query ?token= (stesso schema della chat).
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from apps.chat.auth import get_user_from_scope


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    /ws/notifications/?token=<jwt>

    Gruppo per utente: notifications_<user_id>

    OUT: new_notification, unread_count
    IN: mark_read, mark_all_read
    """

    async def connect(self):
        user = await self._get_user()
        if not user:
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        count = await self.get_unread_count()
        await self.send_json({"type": "unread_count", "count": count})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get("type", "")
        if msg_type == "mark_read":
            nid = content.get("notification_id")
            if nid:
                await self.do_mark_read(str(nid))
                count = await self.get_unread_count()
                await self.send_json({"type": "unread_count", "count": count})
        elif msg_type == "mark_all_read":
            await self.do_mark_all_read()
            count = await self.get_unread_count()
            await self.send_json({"type": "unread_count", "count": count})

    async def new_notification(self, event):
        await self.send_json({
            "type": "new_notification",
            "notification": event["notification"],
        })

    async def unread_count_update(self, event):
        await self.send_json({
            "type": "unread_count",
            "count": event["count"],
        })

    @database_sync_to_async
    def _get_user(self):
        u = get_user_from_scope(self.scope)
        if not u or not getattr(u, "is_active", True):
            return None
        return u

    @database_sync_to_async
    def get_unread_count(self):
        from .models import Notification

        return Notification.objects.filter(recipient=self.user, is_read=False).count()

    @database_sync_to_async
    def do_mark_read(self, notification_id):
        from .models import Notification

        Notification.objects.filter(
            id=notification_id,
            recipient=self.user,
            is_read=False,
        ).update(is_read=True)

    @database_sync_to_async
    def do_mark_all_read(self):
        from .models import Notification

        Notification.objects.filter(recipient=self.user, is_read=False).update(is_read=True)
