"""
Fascicoli: organizzazione documenti e protocolli (RF-064..RF-069).
FASE 22: codice identificativo ANNO/UO/PROGRESSIVO, cartelle, email/PEC, file, indice AGID.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


DOSSIER_STATUS = [
    ("open", "Aperto"),
    ("archived", "Archiviato"),
    ("closed", "Chiuso"),
]

ARCHIVE_STAGE_CHOICES = [
    ("current", "Corrente"),
    ("deposit", "Deposito"),
    ("historical", "Storico"),
]


class Dossier(models.Model):
    """Fascicolo con titolo, identificatore univoco, responsabile e permessi (RF-064..RF-069, FASE 22)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="dossiers",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=500)
    identifier = models.CharField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=DOSSIER_STATUS,
        default="open",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="responsible_dossiers",
    )
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dossiers",
        help_text="UO per generazione codice identificativo ANNO/UO/PROG.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_dossiers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    metadata_structure = models.ForeignKey(
        "metadata.MetadataStructure",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dossiers",
    )
    metadata_values = models.JSONField(default=dict, blank=True)
    # FASE 22: classificazione e conservazione
    classification_code = models.CharField(max_length=50, blank=True)
    classification_label = models.CharField(max_length=200, blank=True)
    retention_years = models.IntegerField(default=10)
    retention_basis = models.CharField(max_length=200, blank=True)
    archive_stage = models.CharField(
        max_length=20,
        choices=ARCHIVE_STAGE_CHOICES,
        default="current",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="closed_dossiers",
    )
    index_generated_at = models.DateTimeField(null=True, blank=True)
    index_file = models.FileField(
        upload_to="dossiers/indexes/%Y/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Fascicolo"
        verbose_name_plural = "Fascicoli"

    def __str__(self):
        return f"{self.identifier} — {self.title}"

    def validate_metadata(self, values):
        """Valida metadata_values rispetto alla struttura associata. Ritorna lista errori."""
        if not self.metadata_structure_id:
            return []
        from apps.metadata.validators import validate_metadata_values
        return validate_metadata_values(self.metadata_structure, values)

    def get_documents(self):
        """Documenti inclusi nel fascicolo."""
        from apps.documents.models import Document
        return Document.objects.filter(
            id__in=self.dossier_documents.values_list("document_id", flat=True)
        )

    def get_protocols(self):
        """Protocolli fasciolati."""
        from apps.protocols.models import Protocol
        return Protocol.objects.filter(
            id__in=self.dossier_protocols.values_list("protocol_id", flat=True)
        )

    def _ensure_identifier(self):
        """Se identifier è vuoto (solo in creazione), genera ANNO/UO_CODE/PROGRESSIVO."""
        if self.identifier and str(self.identifier).strip():
            return
        if self.pk is not None:
            return
        # Preferisci la relazione in memoria (es. da create(organizational_unit=ou))
        ou = getattr(self, "organizational_unit", None)
        if not ou:
            ou_id = getattr(self, "organizational_unit_id", None)
            if ou_id:
                from apps.organizations.models import OrganizationalUnit
                ou = OrganizationalUnit.objects.filter(pk=ou_id).first()
        if not ou or not getattr(ou, "code", None):
            return
        year = timezone.now().year
        prefix = f"{year}/{ou.code}/"
        existing = Dossier.objects.filter(
            organizational_unit=ou,
            identifier__startswith=prefix,
        ).values_list("identifier", flat=True)
        progressivos = []
        for ident in existing:
            try:
                parts = ident.split("/")
                if len(parts) == 3 and parts[2].isdigit():
                    progressivos.append(int(parts[2]))
            except (ValueError, IndexError):
                pass
        next_num = (max(progressivos) + 1) if progressivos else 1
        self.identifier = f"{prefix}{next_num:04d}"

    def save(self, *args, **kwargs):
        self._ensure_identifier()
        super().save(*args, **kwargs)


class DossierDocument(models.Model):
    """Documento inserito nel fascicolo."""
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name="dossier_documents",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="dossier_links",
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [["dossier", "document"]]


class DossierProtocol(models.Model):
    """Protocollo fasciolato."""
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name="dossier_protocols",
    )
    protocol = models.ForeignKey(
        "protocols.Protocol",
        on_delete=models.CASCADE,
        related_name="dossier_links",
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["dossier", "protocol"]]


class DossierPermission(models.Model):
    """Permesso utente su fascicolo."""
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name="user_permissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dossier_permissions",
    )
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)

    class Meta:
        unique_together = [["dossier", "user"]]


class DossierOUPermission(models.Model):
    """Permesso UO su fascicolo."""
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name="ou_permissions",
    )
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        on_delete=models.CASCADE,
        related_name="dossier_permissions",
    )
    can_read = models.BooleanField(default=True)

    class Meta:
        unique_together = [["dossier", "organizational_unit"]]


class DossierFolder(models.Model):
    """Cartella collegata al fascicolo (FASE 22)."""
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name="dossier_folders",
    )
    folder = models.ForeignKey(
        "documents.Folder",
        on_delete=models.CASCADE,
        related_name="dossier_links",
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dossier_folders_added",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["dossier", "folder"]]


class DossierEmail(models.Model):
    """Email/PEC collegata al fascicolo (FASE 22)."""
    EMAIL_TYPE_CHOICES = [
        ("pec", "PEC"),
        ("email", "Email"),
        ("peo", "PEO"),
    ]
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name="dossier_emails",
    )
    email_type = models.CharField(max_length=10, choices=EMAIL_TYPE_CHOICES, default="email")
    from_address = models.EmailField()
    to_addresses = models.JSONField(default=list, blank=True)
    subject = models.CharField(max_length=500)
    body = models.TextField(blank=True)
    received_at = models.DateTimeField()
    message_id = models.CharField(max_length=500, blank=True)
    raw_file = models.FileField(
        upload_to="dossiers/emails/%Y/%m/",
        null=True,
        blank=True,
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dossier_emails_added",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]


class DossierFile(models.Model):
    """File caricato direttamente nel fascicolo (FASE 22)."""
    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name="dossier_files",
    )
    file = models.FileField(upload_to="dossiers/files/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=100, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dossier_files_uploaded",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
