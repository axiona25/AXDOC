"""
API Audit Log (FASE 12, RNF-007). Usa il modello AuditLog in authentication.
"""
import json

from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.authentication.models import AuditLog
from apps.documents.models import Document
from apps.documents.permissions import _documents_queryset_filter
from apps.dashboard.export_service import ExportService
from .serializers import AuditLogSerializer


def _filter_audit_logs_by_tenant(qs, request):
    user = request.user
    if getattr(user, "is_superuser", False):
        return qs
    t = getattr(request, "tenant", None)
    if not t:
        return qs
    if getattr(t, "slug", None) == "default":
        return qs.filter(Q(tenant=t) | Q(tenant__isnull=True))
    return qs.filter(tenant=t)


class AuditLogViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_id = request.query_params.get("user_id")
        action = request.query_params.get("action")
        target_type = request.query_params.get("target_type")
        target_id = request.query_params.get("target_id")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(50, max(1, int(request.query_params.get("page_size", 50))))

        if getattr(user, "role", None) == "ADMIN":
            qs = AuditLog.objects.all().select_related("user").order_by("-timestamp")
            qs = _filter_audit_logs_by_tenant(qs, request)
        else:
            doc_ids = list(
                Document.objects.filter(is_deleted=False).filter(
                    _documents_queryset_filter(user)
                ).values_list("id", flat=True)
            )
            qs = AuditLog.objects.filter(
                Q(user=user) | Q(detail__document_id__in=[str(d) for d in doc_ids])
            ).select_related("user").order_by("-timestamp")

        if user_id:
            qs = qs.filter(user_id=user_id)
        if action:
            qs = qs.filter(action=action)
        if target_id:
            qs = qs.filter(detail__document_id=target_id)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        total = qs.count()
        start = (page - 1) * page_size
        page_qs = qs[start : start + page_size]
        return Response({
            "results": AuditLogSerializer(page_qs, many=True).data,
            "count": total,
        })


def _audit_export_queryset(request):
    user = request.user
    user_id = request.query_params.get("user_id")
    action = request.query_params.get("action")
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if getattr(user, "role", None) != "ADMIN":
        return AuditLog.objects.none()

    qs = AuditLog.objects.all().select_related("user").order_by("-timestamp")
    qs = _filter_audit_logs_by_tenant(qs, request)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if action:
        qs = qs.filter(action=action)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)
    return qs


class AuditExportExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "role", None) != "ADMIN":
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = _audit_export_queryset(request)[:10000]
        headers = ["Data/Ora", "Utente", "Azione", "Dettaglio", "IP"]
        rows = []
        for a in qs:
            detail_s = ""
            if a.detail:
                try:
                    detail_s = json.dumps(a.detail, ensure_ascii=False)[:200]
                except (TypeError, ValueError):
                    detail_s = str(a.detail)[:200]
            rows.append(
                [
                    a.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                    a.user.email if a.user_id else "Sistema",
                    a.action,
                    detail_s,
                    str(a.ip_address or ""),
                ]
            )
        return ExportService.generate_excel(
            title="Audit Log",
            headers=headers,
            rows=rows,
            column_widths=[20, 28, 22, 50, 16],
        )


class AuditExportPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "role", None) != "ADMIN":
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = _audit_export_queryset(request)[:10000]
        headers = ["Data/Ora", "Utente", "Azione", "Dettaglio", "IP"]
        rows = []
        for a in qs:
            detail_s = ""
            if a.detail:
                try:
                    detail_s = json.dumps(a.detail, ensure_ascii=False)[:120]
                except (TypeError, ValueError):
                    detail_s = str(a.detail)[:120]
            rows.append(
                [
                    a.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                    (a.user.email if a.user_id else "Sistema")[:28],
                    a.action[:18],
                    detail_s,
                    str(a.ip_address or "")[:16],
                ]
            )
        return ExportService.generate_pdf(
            title="Audit Log",
            headers=headers,
            rows=rows,
            orientation="landscape",
            column_widths=[30, 32, 22, 70, 22],
        )


class DocumentActivityView(APIView):
    """Attività relative a un documento (tab Attività in DocumentDetailPanel)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        from apps.documents.permissions import CanAccessDocument
        doc = Document.objects.filter(is_deleted=False, id=doc_id).first()
        if not doc:
            return Response({"detail": "Documento non trovato."}, status=404)
        if not CanAccessDocument().has_object_permission(request, None, doc):
            return Response({"detail": "Non autorizzato."}, status=403)
        qs = AuditLog.objects.filter(detail__document_id=str(doc_id)).select_related("user").order_by("-timestamp")[:100]
        return Response(AuditLogSerializer(qs, many=True).data)
