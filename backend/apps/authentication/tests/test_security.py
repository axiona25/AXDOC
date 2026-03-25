"""Test header di sicurezza e rate limit login (FASE 28)."""
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from config.middleware import SecurityHeadersMiddleware


class SecurityHeadersMiddlewareTests(TestCase):
    def test_security_headers_present_when_debug_off(self):
        factory = RequestFactory()

        def get_response(_request):
            return HttpResponse()

        mw = SecurityHeadersMiddleware(get_response)
        with override_settings(DEBUG=False):
            request = factory.get("/api/")
            response = mw(request)
        self.assertIn("Content-Security-Policy", response)
        self.assertIn("Permissions-Policy", response)

    def test_no_csp_when_debug_on(self):
        factory = RequestFactory()

        def get_response(_request):
            return HttpResponse()

        mw = SecurityHeadersMiddleware(get_response)
        with override_settings(DEBUG=True):
            request = factory.get("/api/")
            response = mw(request)
        self.assertNotIn("Content-Security-Policy", response)
