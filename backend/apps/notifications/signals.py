from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .push import push_notification_to_user


@receiver(post_save, sender=Notification)
def notification_created_push(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        push_notification_to_user(instance)
    except Exception:
        pass
