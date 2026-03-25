"""Test push notifiche e signal (FASE 23)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.notifications.models import Notification
from apps.notifications.push import push_notification_to_user

User = get_user_model()


@pytest.mark.django_db
class TestPushNotification:
    def test_push_sends_notification_and_unread_count(self, user_factory):
        user = user_factory(email="push1@test.com")
        Notification.objects.create(
            recipient=user,
            notification_type="system",
            title="Old",
            body="B",
            is_read=False,
        )
        n = Notification.objects.create(
            recipient=user,
            notification_type="system",
            title="Hi",
            body="Body",
            is_read=False,
        )

        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        with patch("apps.notifications.push.get_channel_layer", return_value=mock_layer):
            push_notification_to_user(n)

        assert mock_layer.group_send.call_count == 2
        calls = mock_layer.group_send.call_args_list
        assert calls[0][0][0] == f"notifications_{user.id}"
        assert calls[0][0][1]["type"] == "new_notification"
        assert calls[0][0][1]["notification"]["id"] == str(n.id)
        assert calls[0][0][1]["notification"]["title"] == "Hi"
        assert calls[1][0][0] == f"notifications_{user.id}"
        assert calls[1][0][1]["type"] == "unread_count_update"
        assert calls[1][0][1]["count"] == 2

    def test_push_graceful_if_no_channel_layer(self, user_factory):
        user = user_factory(email="push2@test.com")
        n = Notification.objects.create(
            recipient=user,
            notification_type="system",
            title="Hi",
            body="Body",
        )
        with patch("apps.notifications.push.get_channel_layer", return_value=None):
            push_notification_to_user(n)

    def test_signal_fires_on_notification_create(self, user_factory):
        user = user_factory(email="push3@test.com")
        with patch("apps.notifications.signals.push_notification_to_user") as mock_push:
            n = Notification.objects.create(
                recipient=user,
                notification_type="system",
                title="S",
                body="B",
            )
            mock_push.assert_called_once()
            assert mock_push.call_args[0][0].id == n.id
