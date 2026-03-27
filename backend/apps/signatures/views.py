"""
API Firma digitale e conservazione (RF-075..RF-080, FASE 20).
"""
import io
import zipfile
from django.utils import timezone
from datetime import timedelta
from django.http import FileResponse, HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import SignatureRequest, SignatureSequenceStep, ConservationRequest
from .serializers import (
    SignatureRequestSerializer,
    SignatureRequestDetailSerializer,
    SignatureSequenceStepSerializer,
    OTPVerifySerializer,
    ConservationRequestSerializer,
    SendToConservationSerializer,
)
from .services import SignatureService, ConservationService
from .providers import get_signature_provider
from .verification import verify_signature as do_verify_signature, apply_timestamp


def _notify(recipient, notification_type, title, body, link_url="", metadata=None):
    try:
        from apps.notifications.services import NotificationService
        NotificationService.send(recipient, notification_type, title, body, link_url=link_url or "", metadata=metadata or {})
    except Exception:
        pass


@extend_schema_view(
    list=extend_schema(tags=["Firma Digitale"], summary="Lista richieste di firma"),
    retrieve=extend_schema(tags=["Firma Digitale"], summary="Dettaglio richiesta firma"),
)
class SignatureRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """Richieste firma: list, retrieve, verify_otp, resend_otp, verify; FASE 20: request_for_protocol/dossier, sign_step, reject_step, status_detail, download_signed."""
    serializer_class = SignatureRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SignatureRequest.objects.all().select_related(
            "document", "document_version", "requested_by", "signer", "protocol", "dossier"
        ).prefetch_related("sequence_steps", "sequence_steps__signer")
        if getattr(self.request.user, "role", None) != "ADMIN":
            from django.db.models import Q
            qs = qs.filter(
                Q(signer=self.request.user)
                | Q(requested_by=self.request.user)
                | Q(sequence_steps__signer=self.request.user)
            ).distinct()
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        if target_type:
            if target_type == "protocol":
                qs = qs.filter(protocol__isnull=False)
                if target_id:
                    qs = qs.filter(protocol_id=target_id)
            elif target_type == "dossier":
                qs = qs.filter(dossier__isnull=False)
                if target_id:
                    qs = qs.filter(dossier_id=target_id)
            elif target_type == "document" and target_id:
                qs = qs.filter(document_id=target_id)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SignatureRequestDetailSerializer
        return SignatureRequestSerializer

    @action(detail=True, methods=["get"], url_path="verify")
    def verify(self, request, pk=None):
        """Verifica validità firma (RF-075, FASE 20). Usa verification.verify_signature per risultato completo."""
        sig = self.get_object()
        if not sig.signed_file:
            return Response({"valid": False, "error": "Nessun file firmato."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            path = sig.signed_file.path
        except (ValueError, OSError):
            return Response({"valid": False, "error": "File non disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        result = do_verify_signature(path, sig.format or "cades")
        return Response(result)

    @action(detail=False, methods=["post"], url_path="request_for_protocol")
    def request_for_protocol(self, request):
        """POST /api/signatures/request_for_protocol/ — Crea SignatureRequest target_type=protocol con sequence_steps."""
        from apps.protocols.models import Protocol
        protocol_id = request.data.get("protocol_id")
        if not protocol_id:
            return Response({"protocol_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        protocol = Protocol.objects.filter(id=protocol_id).first()
        if not protocol:
            return Response({"protocol_id": "Protocollo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        signers_data = request.data.get("signers") or []
        if not signers_data:
            return Response({"signers": "Almeno un firmatario."}, status=status.HTTP_400_BAD_REQUEST)
        fmt = request.data.get("signature_type") or request.data.get("format") or "cades"
        if fmt not in ("cades", "pades_invisible", "pades_graphic"):
            fmt = "cades"
        require_sequential = bool(request.data.get("require_sequential", False))
        sign_all_documents = bool(request.data.get("sign_all_documents", False))
        notes = (request.data.get("notes") or "").strip()[:500]
        User = request.user.__class__
        sig = SignatureRequest.objects.create(
            target_type="protocol",
            protocol=protocol,
            requested_by=request.user,
            format=fmt,
            status="pending_otp",
            sign_all_documents=sign_all_documents,
            require_sequential=require_sequential,
            signature_reason=notes,
        )
        for i, item in enumerate(signers_data):
            user_id = item.get("user_id")
            if not user_id:
                continue
            signer = User.objects.filter(id=user_id).first()
            if not signer:
                continue
            role = (item.get("role_required") or "any").strip() or "any"
            if role not in ("any", "operator", "reviewer", "approver", "admin"):
                role = "any"
            SignatureSequenceStep.objects.create(
                signature_request=sig,
                order=i,
                signer=signer,
                role_required=role,
                status="pending",
            )
        if require_sequential:
            _notify(
                sig.sequence_steps.first().signer if sig.sequence_steps.exists() else None,
                "signature_requested",
                "Firma richiesta",
                f"È richiesta la tua firma sul protocollo {getattr(protocol, 'protocol_id', protocol_id)}.",
                link_url=f"/protocols/{protocol_id}",
                metadata={"signature_request_id": str(sig.id)},
            )
        else:
            for step in sig.sequence_steps.all():
                _notify(step.signer, "signature_requested", "Firma richiesta", f"Firma richiesta su protocollo {getattr(protocol, 'protocol_id', protocol_id)}.", link_url=f"/protocols/{protocol_id}", metadata={"signature_request_id": str(sig.id)})
        return Response(SignatureRequestDetailSerializer(sig).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="request_for_dossier")
    def request_for_dossier(self, request):
        """POST /api/signatures/request_for_dossier/ — Crea SignatureRequest target_type=dossier."""
        from apps.dossiers.models import Dossier
        dossier_id = request.data.get("dossier_id")
        if not dossier_id:
            return Response({"dossier_id": "Obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        dossier = Dossier.objects.filter(id=dossier_id).first()
        if not dossier:
            return Response({"dossier_id": "Fascicolo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        signers_data = request.data.get("signers") or []
        if not signers_data:
            return Response({"signers": "Almeno un firmatario."}, status=status.HTTP_400_BAD_REQUEST)
        fmt = request.data.get("signature_type") or request.data.get("format") or "cades"
        if fmt not in ("cades", "pades_invisible", "pades_graphic"):
            fmt = "cades"
        require_sequential = bool(request.data.get("require_sequential", False))
        sign_all_documents = bool(request.data.get("sign_all_documents", True))
        notes = (request.data.get("notes") or "").strip()[:500]
        User = request.user.__class__
        sig = SignatureRequest.objects.create(
            target_type="dossier",
            dossier=dossier,
            requested_by=request.user,
            format=fmt,
            status="pending_otp",
            sign_all_documents=sign_all_documents,
            require_sequential=require_sequential,
            signature_reason=notes,
        )
        for i, item in enumerate(signers_data):
            user_id = item.get("user_id")
            if not user_id:
                continue
            signer = User.objects.filter(id=user_id).first()
            if not signer:
                continue
            role = (item.get("role_required") or "any").strip() or "any"
            if role not in ("any", "operator", "reviewer", "approver", "admin"):
                role = "any"
            SignatureSequenceStep.objects.create(
                signature_request=sig,
                order=i,
                signer=signer,
                role_required=role,
                status="pending",
            )
        if require_sequential:
            first_step = sig.sequence_steps.order_by("order").first()
            if first_step:
                _notify(first_step.signer, "signature_requested", "Firma richiesta", f"Firma richiesta sul fascicolo {getattr(dossier, 'identifier', dossier_id)}.", link_url=f"/dossiers/{dossier_id}", metadata={"signature_request_id": str(sig.id)})
        else:
            for step in sig.sequence_steps.all():
                _notify(step.signer, "signature_requested", "Firma richiesta", f"Firma richiesta su fascicolo {getattr(dossier, 'identifier', dossier_id)}.", link_url=f"/dossiers/{dossier_id}", metadata={"signature_request_id": str(sig.id)})
        return Response(SignatureRequestDetailSerializer(sig).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="sign_step")
    def sign_step(self, request, pk=None):
        """POST /api/signatures/{id}/sign_step/ — Firma step corrente, avanza sequenza, applica marca temporale."""
        sig = self.get_object()
        steps = list(sig.sequence_steps.order_by("order"))
        if not steps:
            return Response({"detail": "Nessuno step di firma."}, status=status.HTTP_400_BAD_REQUEST)
        if sig.status == "completed":
            return Response({"detail": "Richiesta già completata."}, status=status.HTTP_400_BAD_REQUEST)
        if sig.status == "rejected":
            return Response({"detail": "Richiesta rifiutata."}, status=status.HTTP_400_BAD_REQUEST)
        idx = max(0, min(sig.current_signer_index, len(steps) - 1))
        step = steps[idx]
        if step.signer_id != request.user.id:
            return Response({"detail": "Non sei il firmatario di questo step."}, status=status.HTTP_403_FORBIDDEN)
        if step.status != "pending":
            return Response({"detail": "Step già firmato o rifiutato."}, status=status.HTTP_400_BAD_REQUEST)
        step.status = "signed"
        step.signed_at = timezone.now()
        step.certificate_info = request.data.get("certificate_info") or {}
        step.save(update_fields=["status", "signed_at", "certificate_info"])
        sig.advance_sequence()
        if sig.status == "completed":
            _notify(sig.requested_by, "signature_completed", "Firma completata", f"Tutte le firme sono state apposte su {sig.get_target_display()}.", metadata={"signature_request_id": str(sig.id)})
        elif sig.require_sequential:
            next_signer = sig.get_current_signer()
            if next_signer:
                _notify(next_signer, "signature_step_completed", "Firma step completata", f"È il tuo turno per firmare: {sig.get_target_display()}.", metadata={"signature_request_id": str(sig.id)})
        return Response(SignatureRequestDetailSerializer(sig).data)

    @action(detail=True, methods=["post"], url_path="reject_step")
    def reject_step(self, request, pk=None):
        """POST /api/signatures/{id}/reject_step/ — Rifiuta step, request → rejected."""
        sig = self.get_object()
        reason = (request.data.get("reason") or "").strip()
        steps = list(sig.sequence_steps.order_by("order"))
        if not steps:
            return Response({"detail": "Nessuno step."}, status=status.HTTP_400_BAD_REQUEST)
        idx = max(0, min(sig.current_signer_index, len(steps) - 1))
        step = steps[idx]
        if step.signer_id != request.user.id:
            return Response({"detail": "Non sei il firmatario di questo step."}, status=status.HTTP_403_FORBIDDEN)
        if step.status != "pending":
            return Response({"detail": "Step già elaborato."}, status=status.HTTP_400_BAD_REQUEST)
        step.status = "rejected"
        step.rejection_reason = reason[:2000]
        step.save(update_fields=["status", "rejection_reason"])
        sig.status = "rejected"
        sig.save(update_fields=["status", "updated_at"])
        _notify(sig.requested_by, "signature_rejected", "Firma rifiutata", f"La firma è stata rifiutata: {reason or 'Nessuna motivazione'}.", metadata={"signature_request_id": str(sig.id)})
        return Response(SignatureRequestDetailSerializer(sig).data)

    @action(detail=True, methods=["get"], url_path="status_detail")
    def status_detail(self, request, pk=None):
        """GET /api/signatures/{id}/status_detail/ — Stato completo con tutti i sequence_steps."""
        sig = self.get_object()
        data = SignatureRequestDetailSerializer(sig).data
        data["sequence_steps"] = SignatureSequenceStepSerializer(sig.sequence_steps.order_by("order"), many=True).data
        return Response(data)

    @action(detail=True, methods=["get"], url_path="download_signed")
    def download_signed(self, request, pk=None):
        """GET /api/signatures/{id}/download_signed/ — .p7m o .pdf firmato; se multi-documento: ZIP."""
        sig = self.get_object()
        if not sig.signed_file:
            return Response({"detail": "Nessun file firmato disponibile."}, status=status.HTTP_404_NOT_FOUND)
        try:
            sig.signed_file.open("rb")
            content = sig.signed_file.read()
            sig.signed_file.close()
        except (ValueError, OSError):
            return Response({"detail": "File non disponibile."}, status=status.HTTP_404_NOT_FOUND)
        filename = sig.signed_file_name or "signed.p7m"
        if sig.target_type != "document" and len(sig.get_all_target_documents()) > 1:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(filename, content)
            buf.seek(0)
            response = HttpResponse(buf.getvalue(), content_type="application/zip")
            response["Content-Disposition"] = f'attachment; filename="signed_{sig.id}.zip"'
            return response
        response = HttpResponse(content, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="verify_otp")
    def verify_otp(self, request, pk=None):
        """Verifica OTP e completa firma (RF-078). Solo il signer. Per protocol/dossier usare sign_step."""
        sig = self.get_object()
        if sig.target_type != "document" or not sig.document_version_id:
            return Response({"detail": "Per protocollo/fascicolo usare sign_step."}, status=status.HTTP_400_BAD_REQUEST)
        if sig.signer_id != request.user.id:
            return Response({"detail": "Solo il firmatario può inserire l'OTP."}, status=status.HTTP_403_FORBIDDEN)
        ser = OTPVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        success, message = SignatureService.verify_otp(sig, ser.validated_data["otp_code"])
        if success:
            return Response({"success": True, "message": message})
        return Response({"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="resend_otp")
    def resend_otp(self, request, pk=None):
        """Reinvia OTP. Solo il signer, solo se pending_otp e non scaduto."""
        sig = self.get_object()
        if sig.target_type != "document":
            return Response({"detail": "Resend OTP solo per richieste su documento."}, status=status.HTTP_400_BAD_REQUEST)
        if sig.signer_id != request.user.id:
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if sig.status != "pending_otp":
            return Response({"detail": "Richiesta non in attesa di OTP."}, status=status.HTTP_400_BAD_REQUEST)
        if sig.otp_expires_at and sig.otp_expires_at < timezone.now():
            return Response({"detail": "OTP scaduto."}, status=status.HTTP_400_BAD_REQUEST)
        if sig.otp_resend_count >= sig.max_otp_resends:
            return Response({"detail": "Numero massimo di reinvii raggiunto."}, status=status.HTTP_400_BAD_REQUEST)
        provider = get_signature_provider()
        doc_path = ""
        if sig.document_version and getattr(sig.document_version, "file", None) and sig.document_version.file:
            try:
                p = getattr(sig.document_version.file, "path", None)
                if p:
                    doc_path = p
            except (ValueError, OSError):
                pass
        signer = sig.signer or sig.get_current_signer()
        if not signer:  # pragma: no cover — con signer_id valido il firmatario è sempre caricabile
            return Response({"detail": "Nessun firmatario."}, status=status.HTTP_400_BAD_REQUEST)
        result = provider.request_signature(
            document_path=doc_path,
            signer_phone=getattr(signer, "phone", None) or getattr(signer, "mobile", None) or "***0000",
            format=sig.format,
            reason=sig.signature_reason,
            location=sig.signature_location,
        )
        sig.otp_attempts = 0
        sig.otp_resend_count += 1
        sig.otp_expires_at = result.get("otp_expires_at") or (timezone.now() + timedelta(minutes=10))
        sig.otp_sent_at = timezone.now()
        sig.save(update_fields=["otp_attempts", "otp_resend_count", "otp_expires_at", "otp_sent_at", "updated_at"])
        return Response({"message": result.get("message", "OTP reinviato.")})


class ConservationRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """Richieste conservazione: list (ADMIN), retrieve, check_status."""
    serializer_class = ConservationRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ConservationRequest.objects.all().select_related("document", "document_version", "requested_by", "protocol")
        if getattr(self.request.user, "role", None) != "ADMIN":
            qs = qs.filter(requested_by=self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="check_status")
    def check_status(self, request, pk=None):
        """Aggiorna stato da provider (RF-080)."""
        cons = self.get_object()
        if cons.requested_by_id != request.user.id and getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        ConservationService.check_status(cons)
        return Response(ConservationRequestSerializer(cons).data)

    @action(detail=False, methods=["post"], url_path="check_all_pending")
    def check_all_pending(self, request):
        """Aggiorna tutte le richieste sent/in_progress. Solo ADMIN."""
        if getattr(request.user, "role", None) != "ADMIN":
            return Response({"detail": "Solo ADMIN."}, status=status.HTTP_403_FORBIDDEN)
        result = ConservationService.check_all_pending()
        return Response(result)


@extend_schema(
    tags=["Firma Digitale"],
    summary="Verifica firma P7M",
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {"file": {"type": "string", "format": "binary"}},
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "valid": {"type": "boolean"},
                "signers": {"type": "array", "items": {"type": "object"}},
                "errors": {"type": "array", "items": {"type": "string"}},
                "file_name": {"type": "string"},
                "file_size": {"type": "integer"},
            },
        }
    },
)
class VerifyP7MView(APIView):
    """
    POST /api/verify_p7m/
    Upload di un file .p7m e verifica della firma digitale.
    Ritorna info sul firmatario, validità certificato, errori.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        import os
        import tempfile

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "Campo 'file' obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.lower().endswith(".p7m"):
            return Response({"detail": "Solo file .p7m accettati."}, status=status.HTTP_400_BAD_REQUEST)

        with tempfile.NamedTemporaryFile(suffix=".p7m", delete=False) as tmp:
            for chunk in file_obj.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            from .verification import verify_p7m

            result = verify_p7m(tmp_path)
            result["file_name"] = file_obj.name
            result["file_size"] = file_obj.size
            return Response(result)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


@extend_schema(
    tags=["Firma Digitale"],
    summary="Estrai contenuto da file P7M",
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {"file": {"type": "string", "format": "binary"}},
        }
    },
    responses={200: OpenApiTypes.BINARY},
)
class ExtractP7MView(APIView):
    """
    POST /api/extract_p7m/
    Upload di un file .p7m, estrae il documento originale e lo ritorna come download.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        import os
        import tempfile

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "Campo 'file' obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.lower().endswith(".p7m"):
            return Response({"detail": "Solo file .p7m accettati."}, status=status.HTTP_400_BAD_REQUEST)

        with tempfile.NamedTemporaryFile(suffix=".p7m", delete=False) as tmp:
            for chunk in file_obj.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        result = {}
        try:
            from .verification import extract_p7m_content

            result = extract_p7m_content(tmp_path)

            if not result["success"]:
                return Response(
                    {"detail": result.get("error", "Estrazione fallita.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            extracted_path = result["extracted_path"]
            original_name = result["original_name"] or "documento_estratto"
            content_type = result["content_type"] or "application/octet-stream"

            with open(extracted_path, "rb") as f:
                content = f.read()

            response = HttpResponse(content, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{original_name}"'
            return response
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if result.get("extracted_path") and os.path.exists(result["extracted_path"]):
                os.unlink(result["extracted_path"])
                extracted_dir = os.path.dirname(result["extracted_path"])
                if extracted_dir and os.path.isdir(extracted_dir):
                    try:
                        os.rmdir(extracted_dir)
                    except OSError:
                        pass
