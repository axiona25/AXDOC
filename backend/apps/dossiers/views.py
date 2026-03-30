"""
API Fascicoli: CRUD, archiviazione, documenti e protocolli (RF-064..RF-069, FASE 22).
"""
import hashlib
from django.db.models import Count, Q
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.guest_permissions import IsInternalUser
from apps.organizations.mixins import TenantFilterMixin
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import (
    Dossier,
    DossierDocument,
    DossierProtocol,
    DossierPermission,
    DossierOUPermission,
    DossierFolder,
    DossierEmail,
    DossierFile,
)
from .serializers import (
    DossierListSerializer,
    DossierDetailSerializer,
    DossierCreateSerializer,
    DossierDocumentEntrySerializer,
    DossierProtocolEntrySerializer,
    DossierFolderSerializer,
    DossierEmailSerializer,
    DossierFileSerializer,
)
from apps.documents.models import Document, Folder
from apps.protocols.models import Protocol
from apps.organizations.models import OrganizationalUnitMembership
from apps.users.permissions import get_user_ou_ids
from apps.dashboard.export_service import ExportService


def _dossier_export_queryset(view, request):
    qs = view.get_queryset().annotate(_doc_count=Count("dossier_documents", distinct=True))
    responsible_id = request.query_params.get("responsible_id")
    ou_id = request.query_params.get("ou_id")
    status_param = request.query_params.get("status")
    if responsible_id:
        qs = qs.filter(responsible_id=responsible_id)
    if ou_id:
        qs = qs.filter(organizational_unit_id=ou_id)
    if status_param in ("open", "closed", "archived"):
        qs = qs.filter(status=status_param)
    search = (request.query_params.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(identifier__icontains=search)
            | Q(description__icontains=search)
        )
    return qs.order_by("-updated_at")


def _user_can_access_dossier(user, dossier):
    if getattr(user, "role", None) == "ADMIN":
        return True
    if dossier.responsible_id == user.id:
        return True
    if dossier.created_by_id == user.id:
        return True
    ou_ids = set(
        OrganizationalUnitMembership.objects.filter(user=user, is_active=True).values_list(
            "organizational_unit_id", flat=True
        )
    )
    if dossier.organizational_unit_id and dossier.organizational_unit_id in ou_ids:
        return True
    if DossierPermission.objects.filter(dossier=dossier, user=user, can_read=True).exists():
        return True
    if DossierOUPermission.objects.filter(
        dossier=dossier, organizational_unit_id__in=ou_ids, can_read=True
    ).exists():
        return True
    return False


def _user_can_write_dossier(user, dossier):
    if getattr(user, "role", None) == "ADMIN":
        return True
    if dossier.responsible_id == user.id:
        return True
    return DossierPermission.objects.filter(dossier=dossier, user=user, can_write=True).exists()


@extend_schema_view(
    list=extend_schema(tags=["Fascicoli"], summary="Lista fascicoli"),
    create=extend_schema(tags=["Fascicoli"], summary="Crea fascicolo"),
    retrieve=extend_schema(tags=["Fascicoli"], summary="Dettaglio fascicolo"),
    update=extend_schema(tags=["Fascicoli"], summary="Aggiorna fascicolo"),
    partial_update=extend_schema(tags=["Fascicoli"], summary="Aggiorna parziale fascicolo"),
    destroy=extend_schema(tags=["Fascicoli"], summary="Elimina fascicolo"),
)
class DossierViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    Fascicoli: list (filter=mine/all, status=archived), retrieve, create, update, destroy.
    Azioni: archive, add_document, remove_document, add_protocol, remove_protocol, documents, protocols.
    Solo utenti interni (FASE 17).
    """
    permission_classes = [IsAuthenticated, IsInternalUser]
    queryset = Dossier.objects.filter(is_deleted=False)

    def get_queryset(self):
        qs = super().get_queryset().select_related("responsible", "created_by")
        if not self.request.user.is_authenticated:
            return qs.none()
        filter_param = self.request.query_params.get("filter", "").lower()
        status_param = self.request.query_params.get("status", "").lower()
        if status_param == "archived":
            qs = qs.filter(status="archived")
        else:
            qs = qs.exclude(status="archived")
        if filter_param == "all":
            if getattr(self.request.user, "role", None) != "ADMIN":
                qs = qs.none()
        elif filter_param == "mine" or not filter_param:
            if getattr(self.request.user, "role", None) != "ADMIN":
                user = self.request.user
                user_ou_ids = get_user_ou_ids(user)
                qs = qs.filter(
                    Q(responsible=user)
                    | Q(created_by=user)
                    | Q(user_permissions__user=user, user_permissions__can_read=True)
                    | Q(ou_permissions__organizational_unit_id__in=user_ou_ids, ou_permissions__can_read=True)
                    | Q(organizational_unit_id__in=user_ou_ids)
                ).distinct()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(identifier__icontains=search)
                | Q(description__icontains=search)
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DossierListSerializer
        if self.action == "retrieve":
            return DossierDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return DossierCreateSerializer
        return DossierListSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        responsible_id = request.query_params.get("responsible_id")
        if responsible_id:
            qs = qs.filter(responsible_id=responsible_id)
        ou_id = request.query_params.get("ou_id")
        if ou_id:
            qs = qs.filter(organizational_unit_id=ou_id)
        qs = qs.order_by("-updated_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="export_excel")
    def export_excel(self, request):
        qs = _dossier_export_queryset(self, request).select_related("responsible", "organizational_unit")[:5000]
        headers = ["Codice", "Titolo", "Responsabile", "UO", "Stato", "Data Creazione", "Documenti"]
        rows = []
        for d in qs:
            resp_name = ""
            if d.responsible_id:
                u = d.responsible
                resp_name = u.get_full_name() or u.email or ""
            rows.append(
                [
                    d.identifier or str(d.id)[:8],
                    d.title,
                    resp_name,
                    d.organizational_unit.name if d.organizational_unit_id else "",
                    d.get_status_display(),
                    d.created_at.strftime("%d/%m/%Y") if d.created_at else "",
                    d._doc_count,
                ]
            )
        return ExportService.generate_excel(
            title="Report Fascicoli",
            headers=headers,
            rows=rows,
            column_widths=[16, 36, 22, 18, 12, 14, 10],
        )

    @action(detail=False, methods=["get"], url_path="export_pdf")
    def export_pdf(self, request):
        qs = _dossier_export_queryset(self, request).select_related("responsible", "organizational_unit")[:5000]
        headers = ["Codice", "Titolo", "Resp.", "UO", "Stato", "Creazione", "Doc."]
        rows = []
        for d in qs:
            resp_name = ""
            if d.responsible_id:
                u = d.responsible
                resp_name = (u.get_full_name() or u.email or "")[:24]
            rows.append(
                [
                    (d.identifier or str(d.id)[:8])[:14],
                    (d.title or "")[:50],
                    resp_name,
                    (d.organizational_unit.name if d.organizational_unit_id else "")[:16],
                    d.get_status_display(),
                    d.created_at.strftime("%d/%m/%Y") if d.created_at else "",
                    d._doc_count,
                ]
            )
        return ExportService.generate_pdf(
            title="Report Fascicoli",
            headers=headers,
            rows=rows,
            orientation="landscape",
            column_widths=[22, 52, 28, 24, 16, 20, 12],
        )

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        instance = Dossier.objects.filter(pk=pk, is_deleted=False).first()
        if not instance:
            return Response({"detail": "Non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if not _user_can_access_dossier(request.user, instance):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        serializer = DossierDetailSerializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        role = getattr(request.user, "role", None)
        if role not in ("ADMIN", "APPROVER"):
            return Response(
                {"detail": "Solo ADMIN o APPROVER possono creare fascicoli."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DossierCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        responsible = serializer.validated_data.get("responsible")
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
            ).filter(applicable_to__contains="dossier").first()
            if structure:
                from apps.metadata.validators import validate_metadata_values
                errors = validate_metadata_values(structure, metadata_values)
                if errors:
                    return Response(
                        {"metadata_values": {e["field"]: e["message"] for e in errors}},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        identifier = (serializer.validated_data.get("identifier") or "").strip()
        dossier = Dossier(
            title=serializer.validated_data["title"],
            identifier=identifier or "",
            description=serializer.validated_data.get("description", ""),
            responsible=responsible,
            created_by=request.user,
            metadata_structure=structure,
            metadata_values=metadata_values,
            organizational_unit=serializer.validated_data.get("organizational_unit"),
            classification_code=serializer.validated_data.get("classification_code", ""),
            classification_label=serializer.validated_data.get("classification_label", ""),
            retention_years=serializer.validated_data.get("retention_years", 10),
            retention_basis=serializer.validated_data.get("retention_basis", ""),
        )
        dossier.save()
        for uid in serializer.validated_data.get("allowed_users", []) or []:
            DossierPermission.objects.get_or_create(
                dossier=dossier, user_id=uid, defaults={"can_read": True, "can_write": False}
            )
        for ouid in serializer.validated_data.get("allowed_ous", []) or []:
            DossierOUPermission.objects.get_or_create(
                dossier=dossier, organizational_unit_id=ouid, defaults={"can_read": True}
            )
        return Response(
            DossierDetailSerializer(dossier).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not _user_can_write_dossier(request.user, instance):
            return Response({"detail": "Non autorizzato a modificare."}, status=status.HTTP_403_FORBIDDEN)
        serializer = DossierCreateSerializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        for attr in ("title", "identifier", "description", "responsible", "organizational_unit",
                     "classification_code", "classification_label", "retention_years", "retention_basis"):
            if attr in serializer.validated_data:
                setattr(instance, attr, serializer.validated_data[attr])
        meta_id = request.data.get("metadata_structure_id")
        metadata_values = request.data.get("metadata_values") or {}
        if isinstance(metadata_values, str):
            import json
            try:
                metadata_values = json.loads(metadata_values) if metadata_values.strip() else {}
            except (ValueError, AttributeError):
                metadata_values = {}
        if meta_id is not None:
            from apps.metadata.models import MetadataStructure
            structure = None
            if meta_id:
                structure = MetadataStructure.objects.filter(
                    pk=meta_id, is_active=True
                ).filter(applicable_to__contains="dossier").first()
                if structure:
                    from apps.metadata.validators import validate_metadata_values
                    errors = validate_metadata_values(structure, metadata_values)
                    if errors:
                        return Response(
                            {"metadata_values": {e["field"]: e["message"] for e in errors}},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            instance.metadata_structure = structure
            instance.metadata_values = metadata_values
        instance.save()
        if "allowed_users" in serializer.validated_data:
            instance.user_permissions.exclude(user_id__in=serializer.validated_data["allowed_users"]).delete()
            for uid in serializer.validated_data["allowed_users"]:
                DossierPermission.objects.get_or_create(
                    dossier=instance, user_id=uid, defaults={"can_read": True, "can_write": False}
                )
        if "allowed_ous" in serializer.validated_data:
            instance.ou_permissions.exclude(organizational_unit_id__in=serializer.validated_data["allowed_ous"]).delete()
            for ouid in serializer.validated_data["allowed_ous"]:
                DossierOUPermission.objects.get_or_create(
                    dossier=instance, organizational_unit_id=ouid, defaults={"can_read": True}
                )
        return Response(DossierDetailSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Solo ADMIN può eliminare un fascicolo."}, status=status.HTTP_403_FORBIDDEN)
        if instance.status != "open":
            return Response(
                {"detail": "Si può eliminare solo un fascicolo aperto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path="metadata")
    def metadata(self, request, pk=None):
        """
        PATCH /api/dossiers/{id}/metadata/
        Body: { metadata_structure_id: uuid | null, metadata_values: dict }
        Valida e salva metadati sul fascicolo.
        """
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
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
            ).filter(applicable_to__contains="dossier").first()
            if not structure:
                return Response(
                    {"metadata_structure_id": "Struttura non trovata o non applicabile ai fascicoli."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from apps.metadata.validators import validate_metadata_values
            errors = validate_metadata_values(structure, metadata_values)
            if errors:
                return Response(
                    {"metadata_values": {e["field"]: e["message"] for e in errors}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        dossier.metadata_structure = structure
        dossier.metadata_values = metadata_values
        dossier.save(update_fields=["metadata_structure", "metadata_values", "updated_at"])
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        doc_ids = list(dossier.dossier_documents.values_list("document_id", flat=True))
        if doc_ids:
            from apps.documents.models import Document
            not_approved = Document.objects.filter(
                id__in=doc_ids
            ).exclude(status=Document.STATUS_APPROVED)
            if not_approved.exists():
                return Response(
                    {"detail": "Impossibile archiviare: ci sono documenti non approvati nel fascicolo."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        dossier.status = "archived"
        dossier.archived_at = timezone.now()
        dossier.save(update_fields=["status", "archived_at", "updated_at"])
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["post"], url_path="add_document")
    def add_document(self, request, pk=None):
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        doc_id = request.data.get("document_id")
        if not doc_id:
            return Response({"document_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        doc = Document.objects.filter(pk=doc_id, is_deleted=False).first()
        if not doc:
            return Response({"document_id": "Documento non trovato."}, status=status.HTTP_400_BAD_REQUEST)
        _, created = DossierDocument.objects.get_or_create(
            dossier=dossier,
            document=doc,
            defaults={"added_by": request.user, "notes": request.data.get("notes", "")[:500]},
        )
        if not created:
            return Response({"detail": "Documento già nel fascicolo."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["delete"], url_path="remove_document/(?P<doc_id>[^/.]+)")
    def remove_document(self, request, pk=None, doc_id=None):
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        deleted, _ = DossierDocument.objects.filter(dossier=dossier, document_id=doc_id).delete()
        if not deleted:
            return Response({"detail": "Documento non presente nel fascicolo."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["post"], url_path="add_protocol")
    def add_protocol(self, request, pk=None):
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        proto_id = request.data.get("protocol_id")
        if not proto_id:
            return Response({"protocol_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        proto_id = str(proto_id).strip()
        protocol = None
        try:
            protocol = Protocol.objects.filter(pk=proto_id).first()
        except (ValueError, Exception):
            pass
        if not protocol:
            protocol = Protocol.objects.filter(protocol_id=proto_id).first()
        if not protocol:
            protocol = Protocol.objects.filter(protocol_number=proto_id).first()
        if not protocol:
            return Response({"protocol_id": "Protocollo non trovato."}, status=status.HTTP_400_BAD_REQUEST)
        _, created = DossierProtocol.objects.get_or_create(
            dossier=dossier,
            protocol=protocol,
            defaults={"added_by": request.user},
        )
        if not created:
            return Response({"detail": "Protocollo già nel fascicolo."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["delete"], url_path="remove_protocol/(?P<proto_id>[^/.]+)")
    def remove_protocol(self, request, pk=None, proto_id=None):
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        deleted, _ = DossierProtocol.objects.filter(dossier=dossier, protocol_id=proto_id).delete()
        if not deleted:
            return Response({"detail": "Protocollo non presente nel fascicolo."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["get"], url_path="documents")
    def documents_list(self, request, pk=None):
        dossier = self.get_object()
        if not _user_can_access_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        entries = dossier.dossier_documents.select_related("document").all()
        return Response(DossierDocumentEntrySerializer(entries, many=True).data)

    @action(detail=True, methods=["post"], url_path="chat")
    def chat(self, request, pk=None):
        """Crea o recupera la chat per il fascicolo (FASE 13)."""
        dossier = self.get_object()
        if not _user_can_access_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        from apps.chat.models import ChatRoom, ChatMembership
        from apps.chat.serializers import ChatRoomSerializer
        room = ChatRoom.get_or_create_for_dossier(dossier)
        ChatMembership.objects.get_or_create(room=room, user=request.user)
        return Response(ChatRoomSerializer(room, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="protocols")
    def protocols_list(self, request, pk=None):
        dossier = self.get_object()
        if not _user_can_access_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        entries = dossier.dossier_protocols.select_related("protocol").all()
        return Response(DossierProtocolEntrySerializer(entries, many=True).data)

    @action(detail=True, methods=["get"], url_path="detail_full")
    def detail_full(self, request, pk=None):
        """GET /api/dossiers/{id}/detail_full/ — dettaglio completo con cartelle, email, file."""
        dossier = self.get_object()
        if not _user_can_access_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["post"], url_path="add_folder")
    def add_folder(self, request, pk=None):
        """Body: { folder_id }"""
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if dossier.status not in ("open",):
            return Response({"detail": "Fascicolo chiuso o archiviato."}, status=status.HTTP_400_BAD_REQUEST)
        folder_id = request.data.get("folder_id")
        if not folder_id:
            return Response({"folder_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        folder = Folder.objects.filter(pk=folder_id).first()
        if not folder:
            return Response({"folder_id": "Cartella non trovata."}, status=status.HTTP_404_NOT_FOUND)
        _, created = DossierFolder.objects.get_or_create(
            dossier=dossier,
            folder=folder,
            defaults={"added_by": request.user},
        )
        if not created:
            return Response({"detail": "Cartella già nel fascicolo."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["post"], url_path="remove_folder")
    def remove_folder(self, request, pk=None):
        """Body: { dossier_folder_id } oppure { folder_id }"""
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        df_id = request.data.get("dossier_folder_id") or request.data.get("folder_id")
        if not df_id:
            return Response({"dossier_folder_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        qs = DossierFolder.objects.filter(dossier=dossier)
        try:
            qs = qs.filter(pk=df_id)
        except (TypeError, ValueError):
            qs = qs.filter(folder_id=df_id)
        deleted, _ = qs.delete()
        if not deleted:
            return Response({"detail": "Collegamento non trovato."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["post"], url_path="add_email")
    def add_email(self, request, pk=None):
        """Body: { email_type, from_address, to_addresses, subject, body, received_at }"""
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if dossier.status not in ("open",):
            return Response({"detail": "Fascicolo chiuso o archiviato."}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data
        received_at = data.get("received_at") or timezone.now().isoformat()
        from datetime import datetime
        try:
            if isinstance(received_at, str):
                received_at = timezone.make_aware(datetime.fromisoformat(received_at.replace("Z", "+00:00")))
        except (ValueError, TypeError):
            received_at = timezone.now()
        em = DossierEmail.objects.create(
            dossier=dossier,
            email_type=data.get("email_type", "email"),
            from_address=data.get("from_address", ""),
            to_addresses=data.get("to_addresses") or [],
            subject=(data.get("subject") or "")[:500],
            body=data.get("body", ""),
            received_at=received_at,
            message_id=(data.get("message_id") or "")[:500],
            added_by=request.user,
        )
        return Response(DossierEmailSerializer(em).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="upload_file")
    def upload_file(self, request, pk=None):
        """multipart/form-data — carica file direttamente nel fascicolo."""
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if dossier.status not in ("open",):
            return Response({"detail": "Fascicolo chiuso o archiviato."}, status=status.HTTP_400_BAD_REQUEST)
        f = request.FILES.get("file")
        if not f:
            return Response({"file": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        content = b""
        for chunk in f.chunks():
            content += chunk
        checksum = hashlib.sha256(content).hexdigest()
        f.seek(0)
        df = DossierFile.objects.create(
            dossier=dossier,
            file=f,
            file_name=getattr(f, "name", "upload")[:255],
            file_size=f.size,
            file_type=getattr(f, "content_type", "")[:100],
            checksum=checksum,
            uploaded_by=request.user,
            notes=(request.data.get("notes") or "")[:2000],
        )
        return Response(DossierFileSerializer(df).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        """Chiude fascicolo: status=archived, closed_at=now. Solo ADMIN/APPROVER."""
        if getattr(request.user, "role", None) not in ("ADMIN", "APPROVER"):
            return Response({"detail": "Solo ADMIN o APPROVER."}, status=status.HTTP_403_FORBIDDEN)
        dossier = self.get_object()
        if not _user_can_write_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if dossier.status not in ("open",):
            return Response({"detail": "Fascicolo già chiuso o archiviato."}, status=status.HTTP_400_BAD_REQUEST)
        dossier.status = "closed"
        dossier.closed_at = timezone.now()
        dossier.closed_by = request.user
        dossier.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
        return Response(DossierDetailSerializer(dossier).data)

    @action(detail=True, methods=["get"], url_path="generate_index")
    def generate_index(self, request, pk=None):
        """Genera indice PDF conforme AGID. Salva in dossier.index_file. Ritorna PDF inline."""
        dossier = self.get_object()
        if not _user_can_access_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        from .index_generator import generate_dossier_index_pdf
        from django.core.files.base import ContentFile
        pdf_bytes = generate_dossier_index_pdf(dossier)
        fname = f"indice_{dossier.identifier or dossier.id}.pdf"
        fname = "".join(c if c.isalnum() or c in "._-" else "_" for c in fname)
        dossier.index_file.save(fname, ContentFile(pdf_bytes), save=True)
        dossier.index_generated_at = timezone.now()
        dossier.save(update_fields=["index_generated_at", "updated_at"])
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{fname}"'
        return response

    @action(detail=True, methods=["get"], url_path="agid_metadata")
    def agid_metadata(self, request, pk=None):
        """GET /api/dossiers/{id}/agid_metadata/"""
        dossier = self.get_object()
        if not _user_can_access_dossier(request.user, dossier):
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        from apps.metadata.agid_metadata import get_agid_metadata_for_dossier
        meta = get_agid_metadata_for_dossier(dossier)
        return Response(meta)
