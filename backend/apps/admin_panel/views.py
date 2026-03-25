"""
API pannello admin: licenza, system info, backup (FASE 15).
"""
import os
import subprocess
from django.db import connection
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.users.permissions import IsAdminRole
from .models import SystemLicense, SystemSettings


class LicenseView(APIView):
    """GET /api/admin/license/ — configurazione licenza + statistiche (solo ADMIN)."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        lic = SystemLicense.get_current()
        if not lic:
            return Response({
                "license": None,
                "stats": {
                    "active_users": 0,
                    "total_users": 0,
                    "storage_used_gb": 0.0,
                    "storage_limit_gb": None,
                    "documents_count": 0,
                    "expires_in_days": None,
                    "is_expired": False,
                },
            })

        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from django.db.models import Sum
        User = get_user_model()
        today = timezone.now().date()
        active_users = User.objects.filter(is_deleted=False, is_active=True).count()
        total_users = User.objects.filter(is_deleted=False).count()
        storage_used_gb = 0.0
        documents_count = 0
        try:
            from apps.documents.models import DocumentVersion
            documents_count = DocumentVersion.objects.count()
        except Exception:
            pass

        expires_in_days = None
        is_expired = False
        if lic.expires_at:
            delta = lic.expires_at - today
            expires_in_days = delta.days
            is_expired = expires_in_days < 0

        return Response({
            "license": {
                "organization_name": lic.organization_name,
                "activated_at": lic.activated_at.isoformat() if lic.activated_at else None,
                "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                "max_users": lic.max_users,
                "max_storage_gb": lic.max_storage_gb,
                "features_enabled": lic.features_enabled or {},
            },
            "stats": {
                "active_users": active_users,
                "total_users": total_users,
                "storage_used_gb": storage_used_gb,
                "storage_limit_gb": lic.max_storage_gb,
                "documents_count": documents_count,
                "expires_in_days": expires_in_days,
                "is_expired": is_expired,
            },
        })


class SettingsView(APIView):
    """GET/PATCH /api/admin/settings/ — impostazioni di sistema (solo ADMIN). FASE 17."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        obj = SystemSettings.get_settings()
        return Response({
            "email": obj.email,
            "organization": obj.organization,
            "protocol": obj.protocol,
            "security": obj.security,
            "storage": obj.storage,
            "ldap": obj.ldap,
            "conservation": obj.conservation,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        })

    def patch(self, request):
        obj = SystemSettings.get_settings()
        allowed = {"email", "organization", "protocol", "security", "storage", "ldap", "conservation"}
        data = {k: v for k, v in request.data.items() if k in allowed and isinstance(v, dict)}
        for key, value in data.items():
            setattr(obj, key, value)
        obj.save()
        return Response({
            "email": obj.email,
            "organization": obj.organization,
            "protocol": obj.protocol,
            "security": obj.security,
            "storage": obj.storage,
            "ldap": obj.ldap,
            "conservation": obj.conservation,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        })


class SettingsTestEmailView(APIView):
    """POST /api/admin/settings/test_email/ — invia email di test (solo ADMIN). FASE 17."""
    permission_classes = [IsAdminRole]

    def post(self, request):
        to_email = request.data.get("to") or request.user.email
        if not to_email:
            return Response({"detail": "Indirizzo email mancante."}, status=400)
        try:
            from django.core.mail import send_mail
            send_mail(
                subject="[AXDOC] Test email",
                message="Questo è un messaggio di test dalle impostazioni di sistema AXDOC.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@axdoc.local"),
                recipient_list=[to_email],
                fail_silently=False,
            )
            return Response({"status": "ok", "detail": f"Email inviata a {to_email}."})
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class SettingsTestLdapView(APIView):
    """POST /api/admin/settings/test_ldap/ — testa connessione LDAP (solo ADMIN). FASE 17."""
    permission_classes = [IsAdminRole]

    def post(self, request):
        obj = SystemSettings.get_settings()
        ldap_config = obj.ldap or {}
        uri = ldap_config.get("server_uri") or getattr(settings, "AUTH_LDAP_SERVER_URI", "")
        bind_dn = ldap_config.get("bind_dn") or getattr(settings, "AUTH_LDAP_BIND_DN", "")
        password = ldap_config.get("password") or getattr(settings, "AUTH_LDAP_BIND_PASSWORD", "")
        if not uri:
            return Response({"detail": "URI server LDAP non configurato."}, status=400)
        try:
            import ldap
            conn = ldap.initialize(uri)
            conn.simple_bind_s(bind_dn or "", password or "")
            conn.unbind_s()
            return Response({"status": "ok", "detail": "Connessione LDAP riuscita."})
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class SystemInfoView(APIView):
    """GET /api/admin/system_info/ — versioni e stato connessioni (solo ADMIN)."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        import sys
        database_size_mb = 0.0
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT SUM(data_length + index_length) / 1024 / 1024 FROM information_schema.TABLES WHERE table_schema = DATABASE()"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    database_size_mb = round(float(row[0]), 2)
        except Exception:
            pass

        redis_connected = False
        try:
            import redis
            r = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
            r.ping()
            redis_connected = True
        except Exception:
            pass

        ldap_connected = False
        if getattr(settings, "LDAP_ENABLED", False):
            try:
                import ldap
                conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
                conn.simple_bind_s(
                    getattr(settings, "AUTH_LDAP_BIND_DN", ""),
                    getattr(settings, "AUTH_LDAP_BIND_PASSWORD", ""),
                )
                conn.unbind_s()
                ldap_connected = True
            except Exception:
                pass

        return Response({
            "django_version": "4.2",
            "python_version": sys.version.split()[0],
            "database_size_mb": database_size_mb,
            "redis_connected": redis_connected,
            "ldap_connected": ldap_connected,
            "signature_provider": getattr(settings, "SIGNATURE_PROVIDER", "mock"),
            "conservation_provider": getattr(settings, "CONSERVATION_PROVIDER", "mock"),
        })


def _list_backup_files(backup_dir, pattern, backup_type, limit=10):
    """Lista file di backup con info."""
    if not backup_dir or not os.path.isdir(backup_dir):
        return []
    out = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        if pattern not in f:
            continue
        fp = os.path.join(backup_dir, f)
        if not os.path.isfile(fp):
            continue
        try:
            size = os.path.getsize(fp)
            mtime = os.path.getmtime(fp)
            from datetime import datetime
            out.append({
                "filename": f,
                "size_bytes": size,
                "date": datetime.fromtimestamp(mtime).isoformat(),
                "type": backup_type,
            })
        except OSError:
            out.append({"filename": f, "type": backup_type, "error": "inaccessible"})
    return out[:limit]


class BackupListView(APIView):
    """GET /api/admin/backups/ — lista backup (solo ADMIN)."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        opts = getattr(settings, "DBBACKUP_STORAGE_OPTIONS", {})
        backup_dir = opts.get("location", "/backups/db")
        base = os.path.dirname(backup_dir.rstrip("/")) if backup_dir else "/backups"
        media_dir = os.path.join(base, "media")
        db_list = _list_backup_files(backup_dir, ".dump", "db", 20)
        media_list = _list_backup_files(media_dir, ".tar.gz", "media", 20)
        return Response({
            "db": db_list,
            "media": media_list,
        })


class BackupRunView(APIView):
    """POST /api/admin/backups/run/ — avvia backup manuale (solo ADMIN)."""
    permission_classes = [IsAdminRole]

    def post(self, request):
        try:
            from django.core.management import call_command
            from io import StringIO
            out = StringIO()
            call_command("dbbackup", compress=True, noinput=True, stdout=out)
            db_msg = out.getvalue()
        except Exception as e:
            return Response(
                {"status": "error", "detail": str(e)},
                status=500,
            )
        backup_dir = getattr(settings, "DBBACKUP_STORAGE_OPTIONS", {}).get("location", "/backups/db")
        db_files = _list_backup_files(backup_dir, ".dump", "db", 1)
        return Response({
            "status": "completed",
            "db_file": db_files[0]["filename"] if db_files else None,
            "message": "Backup database completato.",
        })
