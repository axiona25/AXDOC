"""Push notifiche via channel layer (WebSocket)."""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notification_to_payload(notification):
    return {
        "id": str(notification.id),
        "title": notification.title,
        "message": notification.body,
        "body": notification.body,
        "verb": "",
        "notification_type": notification.notification_type,
        "is_read": notification.is_read,
        "link_url": notification.link_url or "",
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "read_at": notification.read_at.isoformat() if getattr(notification, "read_at", None) else None,
        "metadata": notification.metadata if isinstance(notification.metadata, dict) else {},
    }


def push_notification_to_user(notification):
    """
    Invia la notifica al gruppo WebSocket del destinatario e il conteggio non lette aggiornato.
    Se non connesso o channel layer assente, nessun errore.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    group_name = f"notifications_{notification.recipient_id}"

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "new_notification",
            "notification": notification_to_payload(notification),
        },
    )

    from .models import Notification

    unread_count = Notification.objects.filter(
        recipient_id=notification.recipient_id,
        is_read=False,
    ).count()

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "unread_count_update",
            "count": unread_count,
        },
    )
