"""
Middleware multi-tenant: header X-Tenant-ID, claim JWT access, subdomain, default.
"""
import threading

import jwt
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.settings import api_settings as jwt_settings

_thread_local = threading.local()


def get_current_tenant():
    return getattr(_thread_local, "tenant", None)


def set_current_tenant(tenant):
    _thread_local.tenant = tenant


def _decode_access_tenant_id(request):
    auth = request.META.get("HTTP_AUTHORIZATION") or ""
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    raw = parts[1]
    try:
        payload = jwt.decode(
            raw,
            jwt_settings.SIGNING_KEY,
            algorithms=[jwt_settings.ALGORITHM],
            options={"verify_aud": False},
        )
    except Exception:
        return None
    tid = payload.get("tenant_id")
    return str(tid) if tid else None


class TenantMiddleware(MiddlewareMixin):
    """
    Ordine: X-Tenant-ID → tenant_id nel JWT access → subdomain → tenant slug default.
    """

    def process_request(self, request):
        from .models import Tenant

        tenant = None
        tenant_id = request.META.get("HTTP_X_TENANT_ID")
        if tenant_id:
            try:
                tenant = Tenant.objects.filter(id=tenant_id, is_active=True).first()
            except Exception:
                tenant = None

        if not tenant:
            jwt_tid = _decode_access_tenant_id(request)
            if jwt_tid:
                tenant = Tenant.objects.filter(id=jwt_tid, is_active=True).first()

        if not tenant and hasattr(request, "user") and request.user.is_authenticated:
            user_tid = getattr(request.user, "tenant_id", None)
            if user_tid:
                tenant = Tenant.objects.filter(id=user_tid, is_active=True).first()

        if not tenant:
            host = request.get_host().split(":")[0]
            parts = host.split(".")
            if len(parts) > 2:
                slug = parts[0]
                if slug and slug.lower() not in ("www", "api", "localhost"):
                    tenant = Tenant.objects.filter(slug=slug, is_active=True).first()

        if not tenant:
            tenant = Tenant.objects.filter(slug="default", is_active=True).first()

        set_current_tenant(tenant)
        request.tenant = tenant

    def process_response(self, request, response):
        set_current_tenant(None)
        return response
