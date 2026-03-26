"""Limite sessioni JWT concorrenti (FASE 32)."""
from django.test import TestCase, override_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.authentication.token_utils import issue_refresh_for_user
from apps.users.models import User


class ConcurrentSessionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sess@test.com",
            password="TestPass123!",
            must_change_password=False,
        )

    def test_login_creates_outstanding_token(self):
        issue_refresh_for_user(self.user)
        self.assertTrue(
            OutstandingToken.objects.filter(user=self.user).exists()
        )

    @override_settings(MAX_CONCURRENT_SESSIONS=3)
    def test_fourth_login_blacklists_oldest_token(self):
        tokens = []
        for _ in range(4):
            r = issue_refresh_for_user(self.user)
            tokens.append(r)
        active = OutstandingToken.objects.filter(user=self.user).exclude(
            id__in=BlacklistedToken.objects.values_list("token_id", flat=True)
        )
        self.assertEqual(active.count(), 3)

    @override_settings(MAX_CONCURRENT_SESSIONS=3)
    def test_blacklisted_refresh_token_rejected(self):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        first = issue_refresh_for_user(self.user)
        first_str = str(first)
        for _ in range(3):
            issue_refresh_for_user(self.user)
        try:
            RefreshToken(first_str).check_blacklist()
            blacklisted = False
        except TokenError:
            blacklisted = True
        self.assertTrue(blacklisted)
