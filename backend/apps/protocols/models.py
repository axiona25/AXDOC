"""
Protocollazione documenti: contatore progressivo, registro protocolli (RF-058..RF-063).
Compatibilità timbro AGID (FASE 07): protocol_number, protocol_date, document_file.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ProtocolCounter(models.Model):
    """Contatore progressivo per anno + UO (RF-059)."""
    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="protocol_counters",
        null=True,
        blank=True,
    )
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        on_delete=models.CASCADE,
        related_name="protocol_counters",
    )
    year = models.IntegerField()
    last_number = models.IntegerField(default=0)

    class Meta:
        unique_together = [["organizational_unit", "year"]]
        verbose_name = "Contatore protocollo"
        verbose_name_plural = "Contatori protocollo"

    @classmethod
    def get_next_number(cls, ou, year):
        """Incremento atomico: ritorna il prossimo numero per anno/UO."""
        from django.db import transaction
        with transaction.atomic():
            counter, _ = cls.objects.select_for_update().get_or_create(
                organizational_unit=ou,
                year=year,
                defaults={
                    "last_number": 0,
                    "tenant": getattr(ou, "tenant", None),
                },
            )
            counter.last_number += 1
            counter.save(update_fields=["last_number"])
            return counter.last_number


PROTOCOL_DIRECTION = [
    ("in", "In entrata"),
    ("out", "In uscita"),
]

PROTOCOL_STATUS = [
    ("active", "Attivo"),
    ("archived", "Archiviato"),
]

PROTOCOL_CATEGORY = [
    ("file", "Documento/File"),
    ("email", "Email"),
    ("pec", "PEC"),
    ("other", "Altro"),
]


class Protocol(models.Model):
    """
    Protocollo: numerazione progressiva per anno/UO, documento collegato (RF-058..RF-063).
    Mantiene protocol_number e document_file per compatibilità timbro AGID.
    """
    DIRECTION_IN = "in"
    DIRECTION_OUT = "out"
    DIRECTION_IN_LEGACY = "IN"
    DIRECTION_OUT_LEGACY = "OUT"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="protocols",
        null=True,
        blank=True,
    )
    number = models.IntegerField(null=True, blank=True, help_text="Progressivo anno/UO")
    year = models.IntegerField(null=True, blank=True)
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="protocols",
    )
    protocol_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Es: 2024/IT/0042",
    )
    direction = models.CharField(
        max_length=10,
        choices=PROTOCOL_DIRECTION,
        default="in",
    )
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="protocols",
    )
    subject = models.CharField(max_length=500, blank=True)
    sender_receiver = models.CharField(max_length=500, blank=True)
    registered_at = models.DateTimeField(null=True, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_protocols",
    )
    status = models.CharField(
        max_length=20,
        choices=PROTOCOL_STATUS,
        default="active",
    )
    notes = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=PROTOCOL_CATEGORY,
        default="file",
        help_text="Categoria del protocollo",
    )
    description = models.TextField(
        blank=True,
        help_text="Descrizione estesa del protocollo",
    )

    # Legacy / AGID (FASE 07)
    protocol_number = models.CharField(max_length=100, blank=True)
    protocol_date = models.DateTimeField(null=True, blank=True)
    document_file = models.FileField(
        upload_to="protocol_docs/",
        null=True,
        blank=True,
        help_text="File da timbrare (AGID)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_protocols",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    attachments = models.ManyToManyField(
        "documents.Document",
        through="ProtocolAttachment",
        through_fields=("protocol", "document"),
        related_name="attached_to_protocols",
        blank=True,
    )

    class Meta:
        ordering = ["-registered_at", "-created_at"]
        verbose_name = "Protocollo"
        verbose_name_plural = "Protocolli"
        unique_together = [["organizational_unit", "year", "number"]]

    def __str__(self):
        return self.protocol_id or self.protocol_number or str(self.id)

    def _direction_display_agid(self):
        if self.direction in (self.DIRECTION_IN, self.DIRECTION_IN_LEGACY):
            return "In entrata"
        return "In uscita"

    def get_direction_display(self):
        return dict(PROTOCOL_DIRECTION).get(self.direction) or self._direction_display_agid()


class ProtocolAttachment(models.Model):
    """Allegati al protocollo (M2M Document)."""
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.CASCADE,
        related_name="attachment_links",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="protocol_attachments",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["protocol", "document"]]
