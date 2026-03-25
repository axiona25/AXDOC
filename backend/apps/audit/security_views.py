from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

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
