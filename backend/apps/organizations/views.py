"""
ViewSet Unità Organizzative (RF-021..RF-027).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.users.permissions import IsAdminRole
from apps.users.guest_permissions import IsInternalUser
from .mixins import TenantFilterMixin
from .models import Tenant, OrganizationalUnit, OrganizationalUnitMembership
from .serializers import (
    TenantSerializer,
    OrganizationalUnitSerializer,
    OrganizationalUnitDetailSerializer,
    OrganizationalUnitCreateSerializer,
    OrganizationalUnitMembershipSerializer,
    AddMemberSerializer,
)
from .utils import export_members_csv


@extend_schema_view(
    list=extend_schema(tags=["Organizzazioni"], summary="Lista tenant"),
    retrieve=extend_schema(tags=["Organizzazioni"], summary="Dettaglio tenant"),
)
class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista tenant (superuser: tutti; altri: solo il proprio). GET .../current/ — tenant attivo."""

    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Tenant.objects.filter(is_active=True).order_by("name")
        t = getattr(self.request, "tenant", None)
        if t:
            return Tenant.objects.filter(id=t.id)
        return Tenant.objects.none()

    @extend_schema(tags=["Organizzazioni"], summary="Tenant corrente (contesto richiesta)")
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return Response({"detail": "Nessun tenant."}, status=404)
        return Response(TenantSerializer(tenant).data)


@extend_schema_view(
    list=extend_schema(tags=["Organizzazioni"], summary="Lista unità organizzative"),
    create=extend_schema(tags=["Organizzazioni"], summary="Crea unità organizzativa"),
    retrieve=extend_schema(tags=["Organizzazioni"], summary="Dettaglio UO"),
    update=extend_schema(tags=["Organizzazioni"], summary="Aggiorna UO"),
    partial_update=extend_schema(tags=["Organizzazioni"], summary="Aggiorna parziale UO"),
    destroy=extend_schema(tags=["Organizzazioni"], summary="Disattiva UO"),
)
class OrganizationalUnitViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """CRUD UO. list/retrieve: autenticati; create/update/destroy: solo ADMIN. Solo utenti interni (FASE 17)."""

    permission_classes = [IsAuthenticated, IsInternalUser]
    queryset = OrganizationalUnit.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("mine") == "true":
            from apps.organizations.models import OrganizationalUnitMembership
            ou_ids = OrganizationalUnitMembership.objects.filter(
                user=self.request.user, is_active=True
            ).values_list("organizational_unit_id", flat=True)
            qs = qs.filter(id__in=ou_ids)
        if self.request.query_params.get("is_active") is not None:
            qs = qs.filter(is_active=self.request.query_params.get("is_active").lower() == "true")
        parent = self.request.query_params.get("parent")
        if parent is not None:
            if parent == "null" or parent == "":
                qs = qs.filter(parent__isnull=True)
            else:
                qs = qs.filter(parent_id=parent)
        code = self.request.query_params.get("code")
        if code:
            qs = qs.filter(code__icontains=code)
        name = self.request.query_params.get("name")
        if name:
            qs = qs.filter(name__icontains=name)
        return qs.order_by("code")

    def get_serializer_class(self):
        if self.action == "list":
            return OrganizationalUnitSerializer
        if self.action in ("retrieve", "members"):
            return OrganizationalUnitDetailSerializer
        if self.action == "create":
            return OrganizationalUnitCreateSerializer
        if self.action in ("update", "partial_update"):
            return OrganizationalUnitCreateSerializer
        return OrganizationalUnitSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "add_member", "remove_member"):
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated(), IsInternalUser()]

    def get_perform_create_kwargs(self, serializer):
        return {"created_by": self.request.user}

    def perform_destroy(self, instance):
        """Soft delete: is_active=False. Solo se senza documenti (FASE 05)."""
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """GET /api/organizations/tree/ — struttura ad albero (solo root)."""
        roots = self.get_queryset().filter(parent__isnull=True, is_active=True)
        data = OrganizationalUnitSerializer(roots, many=True).data
        return Response(data)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """GET /api/organizations/{id}/members/ — lista membri. Query opzionale: ?role=REVIEWER (case-insensitive)."""
        ou = self.get_object()
        qs = ou.memberships.filter(is_active=True).select_related("user")
        role_param = request.query_params.get("role")
        if role_param and role_param.strip():
            qs = qs.filter(role__iexact=role_param.strip())
        serializer = OrganizationalUnitMembershipSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add_member")
    def add_member(self, request, pk=None):
        """POST /api/organizations/{id}/add_member/ — aggiunge utente con ruolo."""
        ou = self.get_object()
        ser = AddMemberSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(pk=ser.validated_data["user_id"], is_deleted=False)
        except User.DoesNotExist:
            return Response({"detail": "Utente non trovato."}, status=status.HTTP_404_NOT_FOUND)
        _, created = OrganizationalUnitMembership.objects.get_or_create(
            user=user,
            organizational_unit=ou,
            defaults={"role": ser.validated_data["role"]},
        )
        if not created:
            return Response(
                {"detail": "Utente già membro di questa UO."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            OrganizationalUnitMembershipSerializer(
                OrganizationalUnitMembership.objects.get(user=user, organizational_unit=ou)
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"], url_path="remove_member/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        """DELETE /api/organizations/{id}/remove_member/{user_id}/."""
        ou = self.get_object()
        membership = ou.memberships.filter(user_id=user_id).first()
        if not membership:
            return Response(
                {"detail": "Membro non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """GET /api/organizations/{id}/export/ — CSV membri (RF-026)."""
        ou = self.get_object()
        buffer = export_members_csv(ou.id)
        if buffer is None:
            return Response({"detail": "UO non trovata."}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="uo-{ou.code}-membri.csv"'
        return response
