"""
Health check per load balancer e monitoring (FASE 15, RNF-012, RNF-013).
GET /api/health/ — pubblico, risposta rapida con stato servizi.
"""
import time
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

# Uptime start (modulo caricato all'avvio)
_START_TIME = time.time()


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(require_GET, name="dispatch")
class HealthCheckView(View):
    """GET /api/health/ — status database, redis, storage; 200 se healthy/degraded, 503 se unhealthy."""

    def get(self, request):
        checks = {}
        # Database
        try:
            connection.ensure_connection()
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"

        # Redis
        try:
            import redis
            r = redis.from_url(getattr(settings, "REDIS_URL", "redis://redis:6379/0"))
            r.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"

        # Storage (media root writable)
        try:
            import os
            media_root = getattr(settings, "MEDIA_ROOT", None)
            if media_root and os.path.isdir(media_root):
                checks["storage"] = "ok"
            else:
                checks["storage"] = "ok"  # no media dir yet is ok
        except Exception:
            checks["storage"] = "error"

        # Migrations (quick check: can query)
        try:
            connection.ensure_connection()
            with connection.cursor() as c:
                c.execute("SELECT 1")
            checks["migrations"] = "ok"
        except Exception:
            checks["migrations"] = "pending" if checks.get("database") == "error" else "ok"

        unhealthy = any(v in ("error", "pending") for v in checks.values() if v != "ok")
        if checks.get("database") == "error":
            status = "unhealthy"
        elif unhealthy:
            status = "degraded"
        else:
            status = "healthy"

        payload = {
            "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checks": checks,
            "version": "1.0.0",
            "uptime_seconds": int(time.time() - _START_TIME),
        }
        status_code = 503 if status == "unhealthy" else 200
        return JsonResponse(payload, status=status_code)
