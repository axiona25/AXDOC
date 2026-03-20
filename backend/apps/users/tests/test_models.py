import uuid
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User


class UserModelTest(TestCase):
    """Test modello User."""

    def test_create_user_uuid(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.assertIsInstance(user.id, uuid.UUID)

    def test_email_unique(self):
        User.objects.create_user(
            email="unique@example.com",
            password="pass",
            first_name="A",
            last_name="B",
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="unique@example.com",
                password="pass2",
                first_name="C",
                last_name="D",
            )

    def test_is_locked_future(self):
        user = User.objects.create_user(
            email="lock@example.com",
            password="pass",
            first_name="Lock",
            last_name="User",
        )
        user.locked_until = timezone.now() + timedelta(minutes=10)
        user.save()
        self.assertTrue(user.is_locked())

    def test_is_locked_past(self):
        user = User.objects.create_user(
            email="unlock@example.com",
            password="pass",
            first_name="Unlock",
            last_name="User",
        )
        user.locked_until = timezone.now() - timedelta(minutes=1)
        user.save()
        self.assertFalse(user.is_locked())

    def test_get_full_name(self):
        user = User.objects.create_user(
            email="name@example.com",
            password="pass",
            first_name="Mario",
            last_name="Rossi",
        )
        self.assertEqual(user.get_full_name(), "Mario Rossi")

    def test_soft_delete_not_in_queryset(self):
        user = User.objects.create_user(
            email="del@example.com",
            password="pass",
            first_name="Del",
            last_name="User",
        )
        user.is_deleted = True
        user.save()
        self.assertNotIn(user, User.objects.filter(is_deleted=False))
