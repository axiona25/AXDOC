"""
Middleware controllo licenza: 402 se scaduta.
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import SystemLicense


class LicenseCheckMiddleware(MiddlewareMixin):
    """
    Se licenza scaduta risponde 402.
    Esclude: login, admin/license, public, static, DEBUG=True.
    """
    EXCLUDE_PREFIXES = (
        "/api/auth/login/",
        "/api/admin/license/",
        "/api/public/",
        "/admin/",
        "/static/",
        "/media/",
    )

    def process_request(self, request):
        if getattr(__import__("django.conf", fromlist=["settings"]).settings, "DEBUG", False):
            return None
        path = request.path
        for prefix in self.EXCLUDE_PREFIXES:
            if path.startswith(prefix):
                return None
        lic = SystemLicense.get_current()
        if not lic or not lic.expires_at:
            return None
        from django.utils import timezone
        if lic.expires_at < timezone.now().date():
            return JsonResponse(
                {
                    "error": "license_expired",
                    "expires_at": lic.expires_at.isoformat(),
                },
                status=402,
            )
        return None
