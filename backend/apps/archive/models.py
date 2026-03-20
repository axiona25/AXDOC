"""
Alberatura archivistica AGID: corrente → deposito → storico.
Pacchetti PdV/PdA/PdD, massimario di scarto (FASE 21).
"""
import hashlib
import uuid
from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save

STAGE_CHOICES = [
    ("current", "Archivio Corrente"),
    ("deposit", "Archivio di Deposito"),
    ("historical", "Archivio Storico"),
]

CONSERVATION_STATUS_CHOICES = [
    ("not_sent", "Non inviato"),
    ("pending", "In attesa"),
    ("accepted", "Accettato"),
    ("rejected", "Rifiutato"),
]

PACKAGE_TYPE_CHOICES = [
    ("PdV", "Versamento"),
    ("PdA", "Archiviazione"),
    ("PdD", "Distribuzione"),
]

PACKAGE_STATUS_CHOICES = [
    ("draft", "Bozza"),
    ("ready", "Pronto"),
    ("sent", "Inviato"),
    ("accepted", "Accettato"),
    ("rejected", "Rifiutato"),
]


class DocumentArchive(models.Model):
    """Stato archivistico di un documento (FASE 21)."""
    document = models.OneToOneField(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="archive_record",
    )
    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default="current",
    )
    classification_code = models.CharField(max_length=50, blank=True)
    classification_label = models.CharField(max_length=200, blank=True)
    retention_years = models.IntegerField(default=10)
    retention_rule = models.CharField(max_length=200, blank=True)
    archive_date = models.DateTimeField(null=True, blank=True)
    archive_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="archived_documents",
    )
    historical_date = models.DateTimeField(null=True, blank=True)
    historical_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="historical_documents",
    )
    discard_date = models.DateField(null=True, blank=True)
    discard_approved = models.BooleanField(default=False)
    conservation_package_id = models.CharField(max_length=200, blank=True)
    conservation_sent_at = models.DateTimeField(null=True, blank=True)
    conservation_status = models.CharField(
        max_length=20,
        choices=CONSERVATION_STATUS_CHOICES,
        default="not_sent",
    )
    conservation_response = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Record archivistico"
        verbose_name_plural = "Record archivistici"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.document_id} — {self.get_stage_display()}"


@receiver(post_save, sender="documents.Document")
def create_document_archive(sender, instance, created, **kwargs):
    """Crea DocumentArchive automaticamente alla creazione del documento."""
    if created and not getattr(instance, "_skip_archive_creation", False):
        DocumentArchive.objects.get_or_create(
            document=instance,
            defaults={"stage": "current"},
        )


class RetentionRule(models.Model):
    """Regola del massimario di scarto (titolario)."""
    ACTION_CHOICES = [
        ("discard", "Scarto"),
        ("permanent_preserve", "Conservazione permanente"),
        ("review", "Revisione"),
    ]
    classification_code = models.CharField(max_length=50, unique=True)
    classification_label = models.CharField(max_length=200)
    document_types = models.JSONField(default=list, blank=True)
    retention_years = models.IntegerField()
    retention_basis = models.CharField(max_length=500, blank=True)
    action_after_retention = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        default="review",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Regola di conservazione"
        verbose_name_plural = "Regole di conservazione"
        ordering = ["classification_code"]

    def __str__(self):
        return f"{self.classification_code} — {self.classification_label}"


class InformationPackage(models.Model):
    """Pacchetto informativo PdV, PdA o PdD (FASE 21)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_type = models.CharField(
        max_length=10,
        choices=PACKAGE_TYPE_CHOICES,
    )
    package_id = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_packages",
    )
    package_file = models.FileField(
        upload_to="packages/%Y/%m/",
        null=True,
        blank=True,
    )
    manifest_file = models.FileField(
        upload_to="packages/%Y/%m/",
        null=True,
        blank=True,
    )
    checksum = models.CharField(max_length=64, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    timestamp_token = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=PACKAGE_STATUS_CHOICES,
        default="draft",
    )
    conservation_response = models.JSONField(default=dict, blank=True)
    documents = models.ManyToManyField(
        "documents.Document",
        through="PackageDocument",
        related_name="information_packages",
        blank=True,
    )
    protocols = models.ManyToManyField(
        "protocols.Protocol",
        through="PackageProtocolLink",
        related_name="information_packages",
        blank=True,
    )
    dossiers = models.ManyToManyField(
        "dossiers.Dossier",
        through="PackageDossierLink",
        related_name="information_packages",
        blank=True,
    )

    class Meta:
        verbose_name = "Pacchetto informativo"
        verbose_name_plural = "Pacchetti informativi"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.package_type} {self.package_id}"


class PackageDocument(models.Model):
    """Documento incluso in un pacchetto (through M2M)."""
    package = models.ForeignKey(
        InformationPackage,
        on_delete=models.CASCADE,
        related_name="package_documents",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="package_links",
    )
    metadata_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [["package", "document"]]


class PackageProtocolLink(models.Model):
    """Protocollo incluso in un pacchetto (through M2M)."""
    package = models.ForeignKey(
        InformationPackage,
        on_delete=models.CASCADE,
        related_name="package_protocol_links",
    )
    protocol = models.ForeignKey(
        "protocols.Protocol",
        on_delete=models.CASCADE,
        related_name="package_protocol_links",
    )

    class Meta:
        unique_together = [["package", "protocol"]]


class PackageDossierLink(models.Model):
    """Fascicolo incluso in un pacchetto (through M2M)."""
    package = models.ForeignKey(
        InformationPackage,
        on_delete=models.CASCADE,
        related_name="package_dossier_links",
    )
    dossier = models.ForeignKey(
        "dossiers.Dossier",
        on_delete=models.CASCADE,
        related_name="package_dossier_links",
    )

    class Meta:
        unique_together = [["package", "dossier"]]
