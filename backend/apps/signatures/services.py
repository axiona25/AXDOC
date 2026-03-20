"""
Servizi firma e conservazione (RF-075..RF-080).
"""
import base64
import os
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db.models import Max

from .models import SignatureRequest, ConservationRequest
from .providers import get_signature_provider, get_conservation_provider


def _signer_phone(user):
    """Numero di telefono per OTP (da profilo utente o placeholder)."""
    return getattr(user, "phone", None) or getattr(user, "mobile", None) or ""


class SignatureService:
    """Logica richiesta firma e verifica OTP."""

    @staticmethod
    def request(document, document_version, requested_by, signer, format_type, reason="", location="", graphic_image_path=None):
        """
        Avvia richiesta firma: crea SignatureRequest, chiama provider, imposta OTP.
        Ritorna (signature_request, otp_message).
        """
        provider = get_signature_provider()
        doc_path = ""
        if document_version and getattr(document_version, "file", None) and document_version.file:
            try:
                p = getattr(document_version.file, "path", None)
                if p and os.path.isfile(p):
                    doc_path = p
            except (ValueError, OSError):
                pass
        signer_phone = _signer_phone(signer) or "***0000"
        result = provider.request_signature(
            document_path=doc_path,
            signer_phone=signer_phone,
            format=format_type,
            reason=reason,
            location=location,
            graphic_image_path=graphic_image_path,
        )
        from datetime import timedelta
        expires = result.get("otp_expires_at") or (timezone.now() + timedelta(minutes=10))
        sig = SignatureRequest.objects.create(
            document=document,
            document_version=document_version,
            requested_by=requested_by,
            signer=signer,
            format=format_type,
            status="pending_otp",
            provider_request_id=result.get("provider_request_id", ""),
            otp_expires_at=expires,
            otp_sent_at=timezone.now(),
            signature_reason=reason,
            signature_location=location,
        )
        return sig, result.get("message", "OTP inviato")

    @staticmethod
    def verify_otp(signature_request, otp_code):
        """
        Verifica OTP e completa firma: chiama provider, salva file firmato, crea nuova DocumentVersion.
        Ritorna (success, message).
        """
        if signature_request.status != "pending_otp":
            return False, "Richiesta non in attesa di OTP."
        if signature_request.otp_expires_at and signature_request.otp_expires_at < timezone.now():
            signature_request.status = "expired"
            signature_request.save(update_fields=["status", "updated_at"])
            return False, "OTP scaduto."
        if signature_request.otp_attempts >= 3:
            signature_request.status = "failed"
            signature_request.error_message = "Troppi tentativi OTP errati."
            signature_request.save(update_fields=["status", "error_message", "updated_at"])
            return False, "Troppi tentativi. Richiesta annullata."

        signature_request.otp_attempts += 1
        signature_request.save(update_fields=["otp_attempts", "updated_at"])

        provider = get_signature_provider()
        result = provider.confirm_signature(
            signature_request.provider_request_id,
            otp_code,
        )
        if not result.get("success"):
            if signature_request.otp_attempts >= 3:
                signature_request.status = "failed"
                signature_request.error_message = result.get("error", "OTP non valido")
                signature_request.save(update_fields=["status", "error_message", "updated_at"])
            return False, result.get("error", "OTP non valido")

        signed_b64 = result.get("signed_file_base64")
        if not signed_b64:
            signature_request.status = "failed"
            signature_request.error_message = "Provider non ha restituito il file firmato."
            signature_request.save(update_fields=["status", "error_message", "updated_at"])
            return False, "File firmato non ricevuto."

        try:
            content = base64.b64decode(signed_b64)
        except Exception as e:
            signature_request.status = "failed"
            signature_request.error_message = str(e)
            signature_request.save(update_fields=["status", "error_message", "updated_at"])
            return False, "File firmato non valido."

        from apps.documents.models import DocumentVersion

        doc = signature_request.document
        ext = "p7m" if signature_request.format == "cades" else "pdf"
        file_name = f"{doc.title}_firmato.{ext}"[:500]
        signature_request.signed_file.save(file_name, ContentFile(content), save=True)
        signature_request.signed_file_name = file_name
        signature_request.signed_at = timezone.now()
        signature_request.status = "completed"
        signature_request.otp_verified = True
        signature_request.save(update_fields=["signed_file", "signed_file_name", "signed_at", "status", "otp_verified", "updated_at"])

        next_ver = (doc.versions.aggregate(max_v=Max("version_number"))["max_v"] or 0)
        next_ver += 1
        doc.versions.update(is_current=False)
        new_version = DocumentVersion.objects.create(
            document=doc,
            version_number=next_ver,
            file_name=file_name,
            file_size=len(content),
            file_type="application/pdf" if ext == "pdf" else "application/pkcs7-mime",
            change_description="Documento firmato digitalmente",
            is_current=True,
            created_by=signature_request.signer,
        )
        new_version.file.save(file_name, ContentFile(content), save=True)
        doc.current_version = next_ver
        doc.updated_at = timezone.now()
        doc.save(update_fields=["current_version", "updated_at"])

        if hasattr(__import__("apps.authentication.models", fromlist=["AuditLog"]), "AuditLog"):
            from apps.authentication.models import AuditLog
            AuditLog.log(
                signature_request.signer,
                "DOCUMENT_SIGNED",
                {"document_id": str(doc.id), "signature_request_id": str(signature_request.id), "version": next_ver},
                None,
            )
        return True, "Documento firmato con successo."

    @staticmethod
    def get_document_signature_status(document):
        """Stato firme del documento: lista SignatureRequest."""
        return list(document.signature_requests.all().order_by("-created_at"))


class ConservationService:
    """Logica invio e monitoraggio conservazione."""

    @staticmethod
    def submit(document, document_version, requested_by, metadata, protocol=None):
        """Invia documento in conservazione. Ritorna conservation_request."""
        provider = get_conservation_provider()
        doc_path = ""
        if document_version and getattr(document_version, "file", None) and document_version.file:
            try:
                p = getattr(document_version.file, "path", None)
                if p and os.path.isfile(p):
                    doc_path = p
            except (ValueError, OSError):
                pass
        result = provider.submit_for_conservation(doc_path, metadata)
        cons = ConservationRequest.objects.create(
            document=document,
            document_version=document_version,
            protocol=protocol,
            requested_by=requested_by,
            status="sent",
            submitted_at=timezone.now(),
            provider_request_id=result.get("provider_request_id", ""),
            provider_package_id=result.get("provider_package_id", ""),
            document_type=metadata.get("document_type", ""),
            document_date=metadata.get("document_date"),
            reference_number=metadata.get("reference_number", ""),
            conservation_class=metadata.get("conservation_class", "1"),
        )
        if hasattr(__import__("apps.authentication.models", fromlist=["AuditLog"]), "AuditLog"):
            from apps.authentication.models import AuditLog
            AuditLog.log(
                requested_by,
                "DOCUMENT_SENT_TO_CONSERVATION",
                {"document_id": str(document.id), "conservation_request_id": str(cons.id)},
                None,
            )
        return cons

    @staticmethod
    def check_status(conservation_request):
        """Aggiorna stato da provider. Ritorna conservation_request aggiornato."""
        provider = get_conservation_provider()
        result = provider.check_conservation_status(conservation_request.provider_request_id)
        conservation_request.last_checked_at = timezone.now()
        conservation_request.status = result.get("status", conservation_request.status)
        if result.get("certificate_url"):
            conservation_request.certificate_url = result["certificate_url"]
        if result.get("status") == "completed":
            conservation_request.completed_at = timezone.now()
        if result.get("status") in ("failed", "rejected") and result.get("message"):
            conservation_request.error_message = result.get("message", "")
        conservation_request.save()
        return conservation_request

    @staticmethod
    def check_all_pending():
        """Aggiorna tutte le richieste sent/in_progress. Ritorna dict con counted/updated/completed/failed."""
        qs = ConservationRequest.objects.filter(status__in=["sent", "in_progress"])
        checked = updated = completed = failed = 0
        for req in qs:
            checked += 1
            old_status = req.status
            ConservationService.check_status(req)
            updated += 1
            if req.status == "completed":
                completed += 1
            elif req.status in ("failed", "rejected"):
                failed += 1
        return {"checked": checked, "updated": updated, "completed": completed, "failed": failed}

    @staticmethod
    def get_document_conservation_status(document):
        """Stato conservazione del documento."""
        return list(document.conservation_requests.all().order_by("-created_at"))
