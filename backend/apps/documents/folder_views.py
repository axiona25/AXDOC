"""
API Cartelle (FASE 05).
"""
from django.db.models import Q, QuerySet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.organizations.mixins import TenantFilterMixin
from .models import Folder, Document
from .serializers import FolderListSerializer, FolderDetailSerializer, FolderCreateSerializer


def _visible_folder_ids(user, request=None):
    """Folder IDs visibili all'utente: creati da lui o con almeno un documento accessibile."""
    if not user or not user.is_authenticated:
        return set()
    tenant = getattr(request, "tenant", None) if request else None
    superuser = getattr(user, "is_superuser", False)

    def scope(qs):
        if superuser or not tenant or not hasattr(qs.model, "tenant"):
            return qs
        if tenant.slug == "default":
            return qs.filter(Q(tenant=tenant) | Q(tenant__isnull=True))
        return qs.filter(tenant=tenant)

    if getattr(user, "role", None) == "ADMIN":
        return set(scope(Folder.objects.filter(is_deleted=False)).values_list("id", flat=True))
    from apps.organizations.models import OrganizationalUnitMembership
    user_ou_ids = list(
        OrganizationalUnitMembership.objects.filter(user=user).values_list("organizational_unit_id", flat=True)
    )
    doc_filters = Q(is_deleted=False) & (
        Q(created_by=user)
        | Q(user_permissions__user=user, user_permissions__can_read=True)
        | Q(ou_permissions__organizational_unit_id__in=user_ou_ids, ou_permissions__can_read=True)
    )
    folder_ids = set(
        scope(Document.objects.filter(doc_filters)).exclude(folder_id__isnull=True).values_list("folder_id", flat=True)
    )
    created_folder_ids = set(
        scope(Folder.objects.filter(is_deleted=False, created_by=user)).values_list("id", flat=True)
    )
    return folder_ids | created_folder_ids


class FolderViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """CRUD cartelle con gerarchia e breadcrumb."""
    permission_classes = [IsAuthenticated]
    queryset = Folder.objects.filter(is_deleted=False)

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        visible = _visible_folder_ids(self.request.user, self.request)
        if visible is not None and getattr(self.request.user, "role", None) != "ADMIN":
            qs = qs.filter(Q(id__in=visible) | Q(created_by=self.request.user))
        return qs.distinct()

    def get_serializer_class(self):
        if self.action == "list" and self.request.query_params.get("all") == "true":
            return FolderDetailSerializer
        if self.action in ("retrieve", "breadcrumb"):
            return FolderDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return FolderCreateSerializer
        return FolderListSerializer

    def list(self, request, *args, **kwargs):
        parent_id = request.query_params.get("parent_id")
        all_tree = request.query_params.get("all") == "true"
        qs = self.get_queryset()
        if all_tree:
            roots = qs.filter(parent_id__isnull=True).order_by("name")
            return Response(FolderDetailSerializer(roots, many=True).data)
        if parent_id in (None, "", "null"):
            qs = qs.filter(parent_id__isnull=True)
        else:
            qs = qs.filter(parent_id=parent_id)
        qs = qs.order_by("name")
        return Response(FolderListSerializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = FolderDetailSerializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = FolderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fk = {"name": serializer.validated_data["name"], "parent": serializer.validated_data.get("parent_id"), "created_by": request.user}
        t = getattr(request, "tenant", None)
        if t and not getattr(request.user, "is_superuser", False):
            fk["tenant"] = t
        folder = Folder.objects.create(**fk)
        return Response(
            FolderListSerializer(folder).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.created_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        serializer = FolderCreateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance.name = serializer.validated_data["name"]
        instance.parent = serializer.validated_data.get("parent_id")
        instance.save(update_fields=["name", "parent", "updated_at"])
        return Response(FolderListSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.documents.filter(is_deleted=False).exists():
            return Response(
                {"detail": "Impossibile eliminare: la cartella contiene documenti non eliminati."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="breadcrumb")
    def breadcrumb(self, request, pk=None):
        """GET /api/folders/{id}/breadcrumb/ → lista antenati per navigazione."""
        folder = self.get_object()
        ancestors = folder.get_ancestors()
        return Response(FolderListSerializer(ancestors, many=True).data)

    @action(detail=True, methods=["patch"], url_path="metadata")
    def metadata(self, request, pk=None):
        """
        PATCH /api/folders/{id}/metadata/
        Body: { metadata_structure_id: uuid | null, metadata_values: dict }
        Valida e salva metadati sulla cartella.
        """
        folder = self.get_object()
        if folder.created_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        meta_id = request.data.get("metadata_structure_id")
        metadata_values = request.data.get("metadata_values") or {}
        if isinstance(metadata_values, str):
            import json
            try:
                metadata_values = json.loads(metadata_values) if metadata_values.strip() else {}
            except (ValueError, AttributeError):
                metadata_values = {}
        structure = None
        if meta_id:
            from apps.metadata.models import MetadataStructure
            structure = MetadataStructure.objects.filter(
                pk=meta_id, is_active=True
            ).filter(applicable_to__contains="folder").first()
            if not structure:
                return Response(
                    {"metadata_structure_id": "Struttura non trovata o non applicabile alle cartelle."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from apps.metadata.validators import validate_metadata_values
            errors = validate_metadata_values(structure, metadata_values)
            if errors:
                return Response(
                    {"metadata_values": {e["field"]: e["message"] for e in errors}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        folder.metadata_structure = structure
        folder.metadata_values = metadata_values
        folder.save(update_fields=["metadata_structure", "metadata_values", "updated_at"])
        return Response(FolderDetailSerializer(folder).data)

    @action(detail=True, methods=["post"], url_path="request_signature")
    def request_signature(self, request, pk=None):
        """Firma multipla: crea una SignatureRequest per ogni documento APPROVED nella cartella."""
        folder = self.get_object()
        from apps.signatures.serializers import RequestSignatureSerializer
        from apps.signatures.services import SignatureService
        from django.contrib.auth import get_user_model

        ser = RequestSignatureSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        signer_id = ser.validated_data["signer_id"]
        format_type = ser.validated_data["format"]
        reason = ser.validated_data.get("reason", "")
        location = ser.validated_data.get("location", "")

        User = get_user_model()
        signer = User.objects.filter(pk=signer_id).first()
        if not signer:
            return Response({"signer_id": "Utente non trovato."}, status=status.HTTP_400_BAD_REQUEST)

        docs = folder.documents.filter(is_deleted=False, status="APPROVED")
        ids = []
        for doc in docs:
            version = doc.versions.filter(is_current=True).first()
            if not version:
                continue
            sig, _ = SignatureService.request(
                document=doc,
                document_version=version,
                requested_by=request.user,
                signer=signer,
                format_type=format_type,
                reason=reason,
                location=location,
            )
            ids.append(str(sig.id))
        return Response({"signature_requests": ids, "count": len(ids)}, status=status.HTTP_201_CREATED)
