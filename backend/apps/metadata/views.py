"""
API strutture metadati (RF-040..RF-047).
"""
from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.guest_permissions import IsInternalUser
from apps.organizations.mixins import TenantFilterMixin
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import MetadataStructure, MetadataField
from .serializers import (
    MetadataStructureListSerializer,
    MetadataStructureDetailSerializer,
    MetadataStructureCreateSerializer,
)
from .validators import validate_metadata_values
from apps.users.permissions import IsAdminRole


@extend_schema_view(
    list=extend_schema(tags=["Metadati"], summary="Lista strutture metadati"),
    create=extend_schema(tags=["Metadati"], summary="Crea struttura metadati"),
    retrieve=extend_schema(tags=["Metadati"], summary="Dettaglio struttura"),
    update=extend_schema(tags=["Metadati"], summary="Aggiorna struttura"),
    partial_update=extend_schema(tags=["Metadati"], summary="Aggiorna parziale struttura"),
    destroy=extend_schema(tags=["Metadati"], summary="Elimina struttura"),
)
class MetadataStructureViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """CRUD strutture metadati. List/retrieve per utenti autenticati; create/update/destroy solo ADMIN. Solo utenti interni (FASE 17)."""
    queryset = MetadataStructure.objects.all()
    permission_classes = [IsAuthenticated, IsInternalUser]

    def get_queryset(self):
        qs = super().get_queryset().order_by("name")
        applicable_to = self.request.query_params.get("applicable_to")
        if applicable_to and applicable_to.strip():
            qs = qs.filter(applicable_to__contains=[applicable_to.strip()])
        usable_by_me = self.request.query_params.get("usable_by_me") == "true"
        if usable_by_me and self.request.user:
            from apps.organizations.models import OrganizationalUnitMembership
            user_ou_ids = list(
                OrganizationalUnitMembership.objects.filter(user=self.request.user).values_list(
                    "organizational_unit_id", flat=True
                )
            )
            qs = qs.annotate(ou_count=Count("allowed_organizational_units")).filter(
                Q(ou_count=0) | Q(allowed_organizational_units__organizational_unit_id__in=user_ou_ids)
            ).distinct()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def get_serializer_class(self):
        if self.action in ("list",):
            return MetadataStructureListSerializer
        if self.action in ("retrieve", "documents"):
            return MetadataStructureDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return MetadataStructureCreateSerializer
        return MetadataStructureListSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated(), IsInternalUser()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            MetadataStructureDetailSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.documents.filter(is_deleted=False).exists():
            fields_data = request.data.get("fields")
            if fields_data is not None:
                for fd in fields_data:
                    fid = fd.get("id")
                    if fid:
                        existing = instance.fields.filter(id=fid).first()
                        if existing and fd.get("field_type") != existing.field_type:
                            return Response(
                                {"detail": "Non è possibile cambiare il tipo di un campo se esistono documenti associati."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(MetadataStructureDetailSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.documents.filter(is_deleted=False).exists():
            return Response(
                {"detail": "Impossibile eliminare: esistono documenti associati a questa struttura."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        """Lista documenti con questa struttura."""
        structure = self.get_object()
        from apps.documents.serializers import DocumentListSerializer
        docs = structure.documents.filter(is_deleted=False)
        return Response(DocumentListSerializer(docs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate(self, request, pk=None):
        """Valida valori metadati. Body: {"values": {...}}. Risposta: {"valid": bool, "errors": [...]}."""
        structure = self.get_object()
        values = request.data.get("values") or {}
        errors = validate_metadata_values(structure, values)
        return Response({"valid": len(errors) == 0, "errors": errors})
