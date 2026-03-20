"""
Test SSO init endpoint (RF-008). Senza credenziali configurate ritorna 503.
"""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class SSOInitTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="", SOCIAL_AUTH_MICROSOFT_GRAPH_KEY="")
    def test_sso_google_disabled_returns_503(self):
        response = self.client.get("/api/auth/sso/google/")
        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.data)

    @override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="", SOCIAL_AUTH_MICROSOFT_GRAPH_KEY="")
    def test_sso_microsoft_disabled_returns_503(self):
        response = self.client.get("/api/auth/sso/microsoft/")
        self.assertEqual(response.status_code, 503)

    def test_sso_invalid_provider_returns_404(self):
        response = self.client.get("/api/auth/sso/invalid/")
        self.assertEqual(response.status_code, 404)
