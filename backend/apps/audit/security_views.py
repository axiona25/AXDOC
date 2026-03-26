from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.dashboard.export_service import ExportService
from apps.users.permissions import IsAdminRole
from apps.organizations.mixins import TenantFilterMixin

from .models import SecurityIncident
from .security_serializers import SecurityIncidentSerializer


class SecurityIncidentViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    serializer_class = SecurityIncidentSerializer
    permission_classes = [IsAuthenticated]
    queryset = SecurityIncident.objects.all().select_related("reported_by", "assigned_to")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        role = getattr(self.request.user, "role", None)
        if role == "ADMIN":
            pass
        elif role in ("APPROVER", "REVIEWER"):
            pass
        else:
            return SecurityIncident.objects.none()

        severity = self.request.query_params.get("severity")
        st = self.request.query_params.get("status")
        category = self.request.query_params.get("category")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if severity:
            qs = qs.filter(severity=severity)
        if st:
            qs = qs.filter(status=st)
        if category:
            qs = qs.filter(category=category)
        if date_from:
            qs = qs.filter(detected_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(detected_at__date__lte=date_to)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
        return qs.order_by("-detected_at")

    def get_perform_create_kwargs(self, serializer):
        return {"reported_by": self.request.user}

    def _incident_export_rows(self, request):
        if getattr(request.user, "role", None) != "ADMIN":
            return None
        qs = (
            self.filter_queryset(self.get_queryset())
            .select_related("assigned_to", "reported_by")
            .order_by("-detected_at")[:5000]
        )
        headers = [
            "Severità",
            "Titolo",
            "Categoria",
            "Stato",
            "Rilevato il",
            "Assegnato a",
            "Dati compromessi",
            "Segnalato",
        ]
        rows = []
        for inc in qs:
            assignee = ""
            if inc.assigned_to:
                assignee = inc.assigned_to.get_full_name() or inc.assigned_to.email or ""
            rows.append(
                [
                    inc.get_severity_display(),
                    inc.title,
                    inc.get_category_display(),
                    inc.get_status_display(),
                    inc.detected_at.strftime("%d/%m/%Y %H:%M") if inc.detected_at else "",
                    assignee,
                    "Sì" if inc.data_compromised else "No",
                    "Sì" if inc.reported_to_authority else "No",
                ]
            )
        return headers, rows

    @extend_schema(tags=["Sicurezza"], summary="Export incidenti in Excel")
    @action(detail=False, methods=["get"], url_path="export_excel")
    def export_excel(self, request):
        """GET /api/security-incidents/export_excel/ — stessi filtri della lista."""
        packed = self._incident_export_rows(request)
        if packed is None:
            return Response(status=403)
        headers, rows = packed
        return ExportService.generate_excel(title="Incidenti di Sicurezza", headers=headers, rows=rows)

    @extend_schema(tags=["Sicurezza"], summary="Export incidenti in PDF")
    @action(detail=False, methods=["get"], url_path="export_pdf")
    def export_pdf(self, request):
        packed = self._incident_export_rows(request)
        if packed is None:
            return Response(status=403)
        headers, rows = packed
        return ExportService.generate_pdf(
            title="Incidenti di Sicurezza",
            headers=headers,
            rows=rows,
            orientation="landscape",
        )
