"""
API Condivisione e accesso pubblico (FASE 11).
"""
from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import ShareLink, ShareAccessLog
from .serializers import ShareLinkSerializer, ShareLinkCreateSerializer, PublicShareSerializer
from .services import create_share_link, check_share_password


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _log_access(share_link, request, action_type="view"):
    ShareAccessLog.objects.create(
        share_link=share_link,
        ip_address=_get_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:500],
        action=action_type,
    )
    share_link.access_count += 1
    share_link.last_accessed_at = timezone.now()
    share_link.save(update_fields=["access_count", "last_accessed_at"])


class ShareLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista condivisioni, revoca, my_shared."""
    serializer_class = ShareLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ShareLink.objects.all().select_related("document", "protocol", "shared_by", "recipient_user")
        if getattr(self.request.user, "role", None) != "ADMIN":
            qs = qs.filter(shared_by=self.request.user)
        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        """Revoca condivisione: is_active=False. Se internal rimuove DocumentPermission."""
        share = self.get_object()
        if share.shared_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        share.is_active = False
        share.save(update_fields=["is_active"])
        if share.recipient_type == "internal" and share.recipient_user_id and share.document_id:
            from apps.documents.models import DocumentPermission
            DocumentPermission.objects.filter(document=share.document, user=share.recipient_user).delete()
        return Response(ShareLinkSerializer(share).data)

    @action(detail=False, methods=["get"], url_path="my_shared")
    def my_shared(self, request):
        """Documenti/protocolli che l'utente ha condiviso."""
        qs = ShareLink.objects.filter(shared_by=request.user).select_related("document", "protocol").order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(ShareLinkSerializer(page, many=True).data)
        return Response(ShareLinkSerializer(qs, many=True).data)


class PublicShareView(APIView):
    """Accesso pubblico al link condiviso (senza JWT). GET only."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        share = ShareLink.objects.filter(token=token).select_related("document", "protocol", "shared_by").first()
        if not share:
            return Response({"detail": "Link non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if not share.is_valid():
            return Response({"detail": "Questo link non è più valido."}, status=status.HTTP_410_GONE)
        if share.password_protected:
            return Response({"requires_password": True, "detail": "Inserire la password."}, status=status.HTTP_401_UNAUTHORIZED)
        _log_access(share, request, "view")
        return Response(PublicShareSerializer(share).data)


class PublicShareVerifyPasswordView(APIView):
    """Verifica password per link protetto. POST only."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, token):
        share = ShareLink.objects.filter(token=token).select_related("document", "protocol", "shared_by").first()
        if not share:
            return Response({"detail": "Link non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if not share.is_valid():
            return Response({"detail": "Questo link non è più valido."}, status=status.HTTP_410_GONE)
        password = (request.data.get("password") or "").strip()
        if not check_share_password(share, password):
            return Response({"valid": False, "detail": "Password non corretta."}, status=status.HTTP_401_UNAUTHORIZED)
        _log_access(share, request, "view")
        return Response({"valid": True, "data": PublicShareSerializer(share).data})


class PublicShareDownloadView(APIView):
    """Download documento/protocollo via link pubblico."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        share = ShareLink.objects.filter(token=token).select_related("document", "protocol").first()
        if not share:
            return Response({"detail": "Link non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if not share.is_valid():
            return Response({"detail": "Questo link non è più valido."}, status=status.HTTP_410_GONE)
        if not share.can_download:
            return Response({"detail": "Download non consentito per questa condivisione."}, status=status.HTTP_403_FORBIDDEN)
        if share.password_protected:
            password = request.GET.get("password") or request.headers.get("X-Share-Password") or ""
            if not check_share_password(share, password):
                return Response({"requires_password": True, "detail": "Password richiesta."}, status=status.HTTP_401_UNAUTHORIZED)

        _log_access(share, request, "download")

        if share.document_id:
            doc = share.document
            version = doc.versions.filter(is_current=True).first()
            if not version or not version.file:
                return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)
            try:
                f = version.file.open("rb")
                return FileResponse(f, as_attachment=True, filename=version.file_name or "document")
            except (ValueError, OSError):
                return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)

        if share.protocol_id:
            if share.protocol.document_id and share.protocol.document:
                doc = share.protocol.document
                version = doc.versions.filter(is_current=True).first()
                if version and version.file:
                    try:
                        f = version.file.open("rb")
                        return FileResponse(f, as_attachment=True, filename=version.file_name or "document")
                    except (ValueError, OSError):
                        pass
            return Response({"detail": "Documento protocollo non disponibile per il download."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Risorsa non disponibile."}, status=status.HTTP_404_NOT_FOUND)
