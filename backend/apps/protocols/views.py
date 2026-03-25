"""
API Protocolli: CRUD, filtri, archiviazione, download, allegati (RF-058..RF-063).
Compatibilità timbro AGID (stamped_document, coverpage).
Registro giornaliero: daily_register.
"""
import os
import tempfile
from datetime import datetime, timedelta

from django.http import HttpResponse, FileResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.guest_permissions import IsInternalUser
from apps.organizations.mixins import TenantFilterMixin
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Protocol, ProtocolCounter
from .serializers import ProtocolListSerializer, ProtocolDetailSerializer, ProtocolCreateSerializer
from apps.documents.models import Document
from .agid_converter import AGIDConverter, ConversionError
from apps.organizations.models import OrganizationalUnit
from apps.dashboard.export_service import ExportService


def _pdf_response(data: bytes, filename: str) -> HttpResponse:
    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def _protocol_filename(protocol, suffix="") -> str:
    raw = (protocol.protocol_id or protocol.protocol_number or str(protocol.id)).replace("/", "_")
    return f"{raw}{suffix}.pdf"


def _user_ou_ids(user):
    from apps.organizations.models import OrganizationalUnitMembership
    return set(
        OrganizationalUnitMembership.objects.filter(user=user).values_list(
            "organizational_unit_id", flat=True
        )
    )


def _normalize_protocol_direction_param(direction: str | None) -> str | None:
    if not direction:
        return None
    d = direction.strip().upper()
    if d == "IN":
        return "in"
    if d == "OUT":
        return "out"
    low = direction.strip().lower()
    if low in ("in", "out"):
        return low
    return None


def _protocol_export_queryset(view, request):
    """Stessi filtri della list + date_from/date_to per export."""
    qs = view.get_queryset()
    filter_param = request.query_params.get("filter", "").lower()
    if filter_param == "mine":
        ou_ids = _user_ou_ids(request.user)
        qs = qs.filter(organizational_unit_id__in=ou_ids) if ou_ids else qs.none()

    direction = _normalize_protocol_direction_param(request.query_params.get("direction"))
    if direction:
        qs = qs.filter(direction=direction)
    ou_id = request.query_params.get("ou_id")
    if ou_id:
        qs = qs.filter(organizational_unit_id=ou_id)
    year = request.query_params.get("year")
    if year:
        try:
            qs = qs.filter(year=int(year))
        except ValueError:
            pass
    status_filter = request.query_params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    search = (request.query_params.get("search") or "").strip()
    if search:
        from django.db.models import Q

        qs = qs.filter(
            Q(subject__icontains=search)
            | Q(sender_receiver__icontains=search)
            | Q(protocol_id__icontains=search)
        )

    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    return qs.order_by("-registered_at", "-created_at")


@extend_schema_view(
    list=extend_schema(tags=["Protocolli"], summary="Lista protocolli"),
    create=extend_schema(tags=["Protocolli"], summary="Crea protocollo"),
    retrieve=extend_schema(tags=["Protocolli"], summary="Dettaglio protocollo"),
    update=extend_schema(tags=["Protocolli"], summary="Aggiorna protocollo"),
    partial_update=extend_schema(tags=["Protocolli"], summary="Aggiorna parziale protocollo"),
    destroy=extend_schema(tags=["Protocolli"], summary="Elimina protocollo"),
)
class ProtocolViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    Protocolli: list (filtri direction, ou, year, status, search), retrieve, create, update.
    destroy → 400 (non si eliminano). Azioni: archive, download, add_attachment.
    Solo utenti interni (FASE 17).
    """
    permission_classes = [IsAuthenticated, IsInternalUser]
    queryset = Protocol.objects.all()

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            "organizational_unit", "document", "registered_by", "created_by"
        )
        if getattr(self.request.user, "role", None) == "ADMIN":
            return qs
        ou_ids = _user_ou_ids(self.request.user)
        if not ou_ids:
            return qs.none()
        return qs.filter(organizational_unit_id__in=ou_ids)

    def get_serializer_class(self):
        if self.action == "list":
            return ProtocolListSerializer
        if self.action == "retrieve":
            return ProtocolDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProtocolCreateSerializer
        return ProtocolListSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        filter_param = request.query_params.get("filter", "").lower()
        if filter_param == "mine":
            ou_ids = _user_ou_ids(request.user)
            qs = qs.filter(organizational_unit_id__in=ou_ids) if ou_ids else qs.none()

        direction = _normalize_protocol_direction_param(request.query_params.get("direction"))
        if direction:
            qs = qs.filter(direction=direction)
        ou_id = request.query_params.get("ou_id")
        if ou_id:
            qs = qs.filter(organizational_unit_id=ou_id)
        year = request.query_params.get("year")
        if year:
            try:
                qs = qs.filter(year=int(year))
            except ValueError:
                pass
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = (request.query_params.get("search") or "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(subject__icontains=search)
                | Q(sender_receiver__icontains=search)
                | Q(protocol_id__icontains=search)
            )

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        qs = qs.order_by("-registered_at", "-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="daily_register")
    def daily_register(self, request):
        """
        Registro giornaliero: elenco protocolli registrati in una data (YYYY-MM-DD).
        Query param: date (obbligatorio), ou_id (opzionale).
        Ritorna lista non paginata con segnatura AGID.
        """
        date_str = (request.query_params.get("date") or "").strip()
        if not date_str:
            return Response(
                {"detail": "Parametro date obbligatorio (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Formato date non valido. Usare YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
        end = start + timedelta(days=1)
        qs = self.get_queryset().filter(
            registered_at__gte=start,
            registered_at__lt=end,
        )
        ou_id = request.query_params.get("ou_id")
        if ou_id:
            qs = qs.filter(organizational_unit_id=ou_id)
        qs = qs.order_by("registered_at")
        serializer = ProtocolListSerializer(qs, many=True)
        return Response({
            "date": date_str,
            "protocols": serializer.data,
        })

    def create(self, request, *args, **kwargs):
        serializer = ProtocolCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ou = serializer.validated_data.get("organizational_unit")
        if not ou:
            return Response(
                {"organizational_unit": "Unità organizzativa obbligatoria."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ou_ids = _user_ou_ids(request.user)
        if getattr(request.user, "role", None) != "ADMIN" and ou.id not in ou_ids:
            return Response(
                {"detail": "Non autorizzato a creare protocolli per questa UO."},
                status=status.HTTP_403_FORBIDDEN,
            )
        year = timezone.now().year
        next_number = ProtocolCounter.get_next_number(ou, year)
        protocol_id = f"{year}/{ou.code}/{next_number:04d}"

        doc = serializer.validated_data.get("document")
        if doc and getattr(doc, "is_protocolled", False):
            return Response(
                {"document": "Documento già protocollato."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = serializer.validated_data.get("category", "file")
        description = serializer.validated_data.get("description", "")
        attachment_ids = serializer.validated_data.get("attachment_ids") or []
        dossier_ids = serializer.validated_data.get("dossier_ids") or []
        file_upload = serializer.validated_data.get("file_upload")

        protocol = Protocol(
            number=next_number,
            year=year,
            organizational_unit=ou,
            protocol_id=protocol_id,
            direction=serializer.validated_data.get("direction", "in"),
            document=doc,
            subject=serializer.validated_data.get("subject", ""),
            sender_receiver=serializer.validated_data.get("sender_receiver", ""),
            registered_at=timezone.now(),
            registered_by=request.user,
            status="active",
            notes=serializer.validated_data.get("notes", ""),
            category=category,
            description=description,
            protocol_number=protocol_id,
            protocol_date=timezone.now(),
            created_by=request.user,
        )

        if file_upload:
            protocol.document_file = file_upload

        protocol.save()

        if doc:
            Document.objects.filter(pk=doc.pk).update(
                is_protocolled=True, updated_at=timezone.now()
            )

        if attachment_ids:
            existing_docs = Document.objects.filter(pk__in=attachment_ids, is_deleted=False)
            for d in existing_docs:
                if doc and d.pk == doc.pk:
                    continue
                protocol.attachments.add(d)

        if dossier_ids:
            try:
                from apps.dossiers.models import Dossier, DossierProtocol

                dossiers = Dossier.objects.filter(pk__in=dossier_ids, is_deleted=False)
                for dossier in dossiers:
                    DossierProtocol.objects.get_or_create(
                        dossier=dossier,
                        protocol=protocol,
                        defaults={"added_by": request.user},
                    )
            except ImportError:
                pass

        return Response(
            ProtocolDetailSerializer(protocol, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        allowed = {"subject", "sender_receiver", "notes"}
        data = {k: v for k, v in request.data.items() if k in allowed}
        serializer = ProtocolCreateSerializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ProtocolDetailSerializer(instance, context={"request": request}).data
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "I protocolli non si eliminano; usare archivia."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"], url_path="export_excel")
    def export_excel(self, request):
        """
        GET .../export_excel/?date_from=&date_to=&direction=in|out|IN|OUT&ou_id=
        """
        qs = _protocol_export_queryset(self, request).select_related("organizational_unit")[:5000]
        headers = [
            "N. Protocollo",
            "Data",
            "Direzione",
            "Oggetto",
            "Mittente/Destinatario",
            "UO",
            "Stato",
        ]
        rows = []
        for p in qs:
            rows.append(
                [
                    p.protocol_id or (str(p.number) if p.number is not None else str(p.id)[:8]),
                    p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else "",
                    p.get_direction_display(),
                    p.subject or "",
                    p.sender_receiver or "",
                    p.organizational_unit.name if p.organizational_unit_id else "",
                    p.get_status_display(),
                ]
            )
        return ExportService.generate_excel(
            title="Report Protocolli",
            headers=headers,
            rows=rows,
            column_widths=[18, 18, 14, 40, 28, 22, 12],
        )

    @action(detail=False, methods=["get"], url_path="export_pdf")
    def export_pdf(self, request):
        qs = _protocol_export_queryset(self, request).select_related("organizational_unit")[:5000]
        headers = [
            "N. Protocollo",
            "Data",
            "Dir.",
            "Oggetto",
            "Mittente/Dest.",
            "UO",
            "Stato",
        ]
        rows = []
        for p in qs:
            rows.append(
                [
                    p.protocol_id or (str(p.number) if p.number is not None else ""),
                    p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else "",
                    p.get_direction_display()[:12],
                    (p.subject or "")[:80],
                    (p.sender_receiver or "")[:40],
                    (p.organizational_unit.name if p.organizational_unit_id else "")[:20],
                    p.get_status_display(),
                ]
            )
        return ExportService.generate_pdf(
            title="Report Protocolli",
            headers=headers,
            rows=rows,
            orientation="landscape",
            column_widths=[28, 22, 14, 55, 35, 22, 18],
        )

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        protocol = self.get_object()
        protocol.status = "archived"
        protocol.save(update_fields=["status"])
        return Response(
            ProtocolDetailSerializer(protocol, context={"request": request}).data
        )

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """Scarica il documento protocollato (versione corrente) o 404."""
        protocol = self.get_object()
        if protocol.document:
            doc = protocol.document
            ver = getattr(doc, "current_version_obj", None)
            if ver and getattr(ver, "file", None) and ver.file:
                try:
                    f = ver.file.open("rb")
                    return FileResponse(
                        f,
                        as_attachment=True,
                        filename=ver.file_name or "document",
                    )
                except (ValueError, OSError):
                    pass
        return Response(
            {"detail": "Nessun documento da scaricare per questo protocollo."},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(detail=True, methods=["post"], url_path="add_attachment")
    def add_attachment(self, request, pk=None):
        protocol = self.get_object()
        doc_id = request.data.get("document_id")
        if not doc_id:
            return Response(
                {"document_id": "Obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        doc = Document.objects.filter(pk=doc_id, is_deleted=False).first()
        if not doc:
            return Response(
                {"document_id": "Documento non trovato."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if protocol.attachments.filter(pk=doc_id).exists():
            return Response(
                {"detail": "Documento già allegato."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        protocol.attachments.add(doc)
        return Response(
            ProtocolDetailSerializer(protocol, context={"request": request}).data,
        )

    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        """Crea link di condivisione per il protocollo (FASE 11)."""
        protocol = self.get_object()
        from apps.sharing.serializers import ShareLinkCreateSerializer
        from apps.sharing.services import create_share_link
        from django.conf import settings
        from apps.users.models import User

        ser = ShareLinkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        recipient_user = None
        if data["recipient_type"] == "internal" and data.get("recipient_user_id"):
            recipient_user = User.objects.filter(pk=data["recipient_user_id"]).first()
            if not recipient_user:
                return Response({"recipient_user_id": "Utente non trovato."}, status=status.HTTP_400_BAD_REQUEST)

        share, err = create_share_link(
            request=request,
            target_type="protocol",
            protocol=protocol,
            recipient_type=data["recipient_type"],
            recipient_user=recipient_user,
            recipient_email=data.get("recipient_email", ""),
            recipient_name=data.get("recipient_name", ""),
            can_download=data.get("can_download", True),
            expires_in_days=data.get("expires_in_days"),
            max_accesses=data.get("max_accesses"),
            password=data.get("password"),
        )
        frontend = getattr(settings, "FRONTEND_URL", "") or ""
        url = f"{frontend}/share/{share.token}"
        return Response(
            {"share_link_id": str(share.id), "token": share.token, "url": url},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="shares")
    def shares_list(self, request, pk=None):
        """Lista condivisioni attive del protocollo."""
        protocol = self.get_object()
        from apps.sharing.serializers import ShareLinkSerializer
        qs = protocol.share_links.all().select_related("recipient_user", "shared_by").order_by("-created_at")
        return Response(ShareLinkSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="stamped_document")
    def stamped_document(self, request, pk=None):
        """
        Scarica documento con timbro AGID applicato.
        Se il protocollo ha document: usa il file della versione corrente.
        Altrimenti usa document_file se presente, altrimenti solo copertina.
        """
        protocol = self.get_object()
        input_path = None
        if protocol.document:
            ver = getattr(protocol.document, "current_version_obj", None)
            if ver and getattr(ver, "file", None) and ver.file.name:
                input_path = ver.file.path if hasattr(ver.file, "path") else None
                if not input_path or not os.path.isfile(input_path):
                    input_path = None
        if not input_path and protocol.document_file:
            input_path = protocol.document_file.path if hasattr(protocol.document_file, "path") else None
            if not input_path or not os.path.isfile(input_path):
                input_path = None
        try:
            if input_path:
                fd, output_path = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)
                try:
                    AGIDConverter.apply_protocol_stamp(input_path, protocol, output_path)
                    with open(output_path, "rb") as f:
                        data = f.read()
                    return _pdf_response(data, _protocol_filename(protocol))
                finally:
                    if os.path.isfile(output_path):
                        os.unlink(output_path)
            fd, output_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            try:
                AGIDConverter.generate_protocol_coverpage(protocol, output_path)
                with open(output_path, "rb") as f:
                    data = f.read()
                return _pdf_response(
                    data,
                    _protocol_filename(protocol, "_copertina"),
                )
            finally:
                if os.path.isfile(output_path):
                    os.unlink(output_path)
        except ConversionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="coverpage")
    def coverpage(self, request, pk=None):
        """Genera e scarica la pagina di copertina PDF del protocollo."""
        protocol = self.get_object()
        fd, output_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            AGIDConverter.generate_protocol_coverpage(protocol, output_path)
            with open(output_path, "rb") as f:
                data = f.read()
            return _pdf_response(data, _protocol_filename(protocol, "_copertina"))
        finally:
            if os.path.isfile(output_path):
                os.unlink(output_path)
