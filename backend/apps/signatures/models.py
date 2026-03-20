"""
Firma digitale e conservazione (RF-075..RF-080).
"""
import uuid
from django.db import models
from django.conf import settings


SIGNATURE_FORMAT = [
    ("cades", "CAdES (.p7m)"),
    ("pades_invisible", "PAdES invisibile"),
    ("pades_graphic", "PAdES grafica"),
]

SIGNATURE_STATUS = [
    ("pending_otp", "In attesa OTP"),
    ("pending_provider", "In elaborazione provider"),
    ("completed", "Completata"),
    ("failed", "Fallita"),
    ("expired", "Scaduta"),
    ("rejected", "Rifiutata"),
]

TARGET_TYPE = [
    ("document", "Documento"),
    ("protocol", "Protocollo"),
    ("dossier", "Fascicolo"),
]

SEQUENCE_STEP_STATUS = [
    ("pending", "In attesa"),
    ("signed", "Firmato"),
    ("rejected", "Rifiutato"),
    ("skipped", "Saltato"),
]

ROLE_REQUIRED = [
    ("any", "Qualsiasi"),
    ("operator", "Operatore"),
    ("reviewer", "Revisore"),
    ("approver", "Approvatore"),
    ("admin", "Amministratore"),
]

CONSERVATION_STATUS = [
    ("draft", "Da inviare"),
    ("pending", "In attesa invio"),
    ("sent", "Inviato al provider"),
    ("in_progress", "In elaborazione"),
    ("completed", "Conservato"),
    ("failed", "Fallito"),
    ("rejected", "Rifiutato dal provider"),
]


class SignatureRequest(models.Model):
    """Richiesta di firma digitale su documento, protocollo o fascicolo (RF-075..RF-078, FASE 20)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE,
        default="document",
    )
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    document_version = models.ForeignKey(
        "documents.DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    protocol = models.ForeignKey(
        "protocols.Protocol",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    dossier = models.ForeignKey(
        "dossiers.Dossier",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requested_signatures",
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="signature_requests_as_signer",
    )
    format = models.CharField(max_length=20, choices=SIGNATURE_FORMAT)
    status = models.CharField(max_length=30, choices=SIGNATURE_STATUS, default="pending_otp")
    sign_all_documents = models.BooleanField(default=False)
    signed_document_ids = models.JSONField(default=list, blank=True)
    signature_sequence = models.JSONField(default=list, blank=True)
    current_signer_index = models.IntegerField(default=0)
    require_sequential = models.BooleanField(default=False)

    provider = models.CharField(max_length=50, default="aruba")
    provider_request_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    otp_sent_at = models.DateTimeField(null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    otp_attempts = models.IntegerField(default=0)
    max_otp_resends = models.IntegerField(default=3)
    otp_resend_count = models.IntegerField(default=0)

    signed_file = models.FileField(upload_to="signed/%Y/%m/", null=True, blank=True)
    signed_file_name = models.CharField(max_length=500, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    signature_reason = models.CharField(max_length=500, blank=True)
    signature_location = models.CharField(max_length=255, blank=True)
    graphic_signature_image = models.ImageField(
        upload_to="sig_images/",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Richiesta firma"
        verbose_name_plural = "Richieste firma"

    def __str__(self):
        t = self.get_target_display()
        return f"Firma {t} — {self.get_format_display()} ({self.status})"

    def get_target_display(self):
        """Descrizione testuale del target (per UI)."""
        if self.target_type == "document" and self.document_id:
            return self.document.title if self.document else str(self.document_id)
        if self.target_type == "protocol" and self.protocol_id:
            return getattr(self.protocol, "protocol_id", None) or getattr(self.protocol, "protocol_number", None) or str(self.protocol_id)
        if self.target_type == "dossier" and self.dossier_id:
            return getattr(self.dossier, "identifier", None) or getattr(self.dossier, "title", None) or str(self.dossier_id)
        return str(self.id)

    def get_current_signer(self):
        """Restituisce l'utente che deve firmare in questo step (da sequence_steps o signer legacy)."""
        steps = list(self.sequence_steps.order_by("order"))
        if steps and 0 <= self.current_signer_index < len(steps):
            step = steps[self.current_signer_index]
            if step.status == "pending":
                return step.signer
        if self.signer_id and self.target_type == "document":
            return self.signer
        return None

    def advance_sequence(self):
        """Avanza al prossimo firmatario. Se tutti firmati, status → completed."""
        steps = list(self.sequence_steps.order_by("order"))
        if not steps:
            self.status = "completed"
            self.save(update_fields=["status", "updated_at"])
            return
        next_idx = self.current_signer_index + 1
        while next_idx < len(steps) and steps[next_idx].status != "pending":
            next_idx += 1
        if next_idx >= len(steps):
            self.status = "completed"
            self.current_signer_index = len(steps)
        else:
            self.current_signer_index = next_idx
        self.save(update_fields=["current_signer_index", "status", "updated_at"])

    def get_all_target_documents(self):
        """Lista di (Document, DocumentVersion) da firmare per questo target."""
        from apps.documents.models import Document, DocumentVersion
        from apps.protocols.models import ProtocolAttachment
        if self.target_type == "document" and self.document_id:
            doc = self.document
            if not doc:
                return []
            ver = self.document_version or doc.versions.filter(is_current=True).first()
            if ver:
                return [(doc, ver)]
            return [(doc, None)]
        if self.target_type == "protocol" and self.protocol_id:
            prot = self.protocol
            if not prot:
                return []
            out = []
            seen = set()
            if prot.document_id:
                doc = prot.document
                if doc:
                    ver = doc.versions.filter(is_current=True).first()
                    out.append((doc, ver))
                    seen.add(doc.id)
            if self.sign_all_documents:
                for link in prot.attachment_links.select_related("document").all():
                    doc = link.document
                    if doc and doc.id not in seen:
                        seen.add(doc.id)
                        ver = doc.versions.filter(is_current=True).first()
                        out.append((doc, ver))
            return out if out else []
        if self.target_type == "dossier" and self.dossier_id:
            dossier = self.dossier
            if not dossier:
                return []
            from apps.dossiers.models import DossierDocument
            doc_ids = list(DossierDocument.objects.filter(dossier=dossier).values_list("document_id", flat=True))
            if not doc_ids:
                return []
            out = []
            for doc in Document.objects.filter(id__in=doc_ids):
                ver = doc.versions.filter(is_current=True).first()
                out.append((doc, ver))
            return out
        return []


class SignatureSequenceStep(models.Model):
    """Step della sequenza di firma multi-firmatario (FASE 20)."""
    signature_request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name="sequence_steps",
    )
    order = models.PositiveIntegerField()
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signature_sequence_steps",
    )
    role_required = models.CharField(
        max_length=20,
        choices=ROLE_REQUIRED,
        default="any",
    )
    status = models.CharField(
        max_length=20,
        choices=SEQUENCE_STEP_STATUS,
        default="pending",
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    certificate_info = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = [["signature_request", "order"]]
        verbose_name = "Step firma"
        verbose_name_plural = "Step firma"

    def __str__(self):
        return f"Step {self.order} — {self.signer.email if self.signer else '?'} ({self.status})"


class ConservationRequest(models.Model):
    """Richiesta di conservazione digitale (RF-079, RF-080)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="conservation_requests",
    )
    document_version = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.CASCADE,
        related_name="conservation_requests",
    )
    protocol = models.ForeignKey(
        "protocols.Protocol",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conservation_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conservation_requests",
    )

    provider = models.CharField(max_length=50, default="aruba")
    provider_request_id = models.CharField(max_length=255, blank=True)
    provider_package_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=CONSERVATION_STATUS,
        default="draft",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    document_type = models.CharField(max_length=200)
    document_date = models.DateField()
    reference_number = models.CharField(max_length=200, blank=True)
    conservation_class = models.CharField(max_length=10, default="1")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True)
    certificate_url = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Richiesta conservazione"
        verbose_name_plural = "Richieste conservazione"

    def __str__(self):
        return f"Conservazione {self.document.title} — {self.status}"
