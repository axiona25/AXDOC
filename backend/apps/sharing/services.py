"""
Servizi condivisione (FASE 11).
"""
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta

from .models import ShareLink
from .emails import send_share_email


def create_share_link(
    request,
    target_type,
    document=None,
    protocol=None,
    recipient_type="external",
    recipient_user=None,
    recipient_email="",
    recipient_name="",
    can_download=True,
    expires_in_days=None,
    max_accesses=None,
    password=None,
):
    """
    Crea ShareLink e gestisce internal (DocumentPermission + notifica) o external (email).
    Ritorna (share_link, error_message). error_message solo in caso di errore invio email.
    """
    expires_at = None
    if expires_in_days:
        expires_at = timezone.now() + timedelta(days=expires_in_days)

    password_protected = bool(password and password.strip())
    access_password = ""
    if password_protected:
        access_password = make_password(password)

    tenant = getattr(request, "tenant", None)
    if not tenant and document and getattr(document, "tenant_id", None):
        from apps.organizations.models import Tenant

        tenant = Tenant.objects.filter(pk=document.tenant_id).first()
    if not tenant and protocol and getattr(protocol, "tenant_id", None):
        from apps.organizations.models import Tenant

        tenant = Tenant.objects.filter(pk=protocol.tenant_id).first()
    share = ShareLink.objects.create(
        target_type=target_type,
        document=document,
        protocol=protocol,
        tenant=tenant,
        shared_by=request.user,
        recipient_type=recipient_type,
        recipient_user=recipient_user,
        recipient_email=(recipient_email or "").strip(),
        recipient_name=(recipient_name or "").strip()[:255],
        can_download=can_download,
        password_protected=password_protected,
        access_password=access_password,
        expires_at=expires_at,
        max_accesses=max_accesses,
    )

    if recipient_type == "internal" and recipient_user and document:
        from apps.documents.models import DocumentPermission
        DocumentPermission.objects.get_or_create(
            document=document,
            user=recipient_user,
            defaults={"can_read": True, "can_write": False, "can_delete": False},
        )
        try:
            from apps.notifications.services import NotificationService
            NotificationService.notify_document_shared(document, recipient_user, request.user)
        except Exception:
            pass
        if hasattr(__import__("apps.authentication.models", fromlist=["AuditLog"]), "AuditLog"):
            from apps.authentication.models import AuditLog
            AuditLog.log(
                request.user,
                "DOCUMENT_SHARED",
                {"document_id": str(document.id), "share_link_id": str(share.id), "recipient_id": str(recipient_user.id)},
                request,
            )
    elif recipient_type == "external":
        try:
            send_share_email(share)
        except Exception as e:
            return share, str(e)
        if hasattr(__import__("apps.authentication.models", fromlist=["AuditLog"]), "AuditLog"):
            from apps.authentication.models import AuditLog
            AuditLog.log(
                request.user,
                "DOCUMENT_SHARED_EXTERNAL",
                {"share_link_id": str(share.id), "recipient_email": share.recipient_email},
                request,
            )

    return share, None


def check_share_password(share_link, password):
    if not share_link.password_protected:
        return True
    return bool(share_link.access_password and check_password(password, share_link.access_password))
