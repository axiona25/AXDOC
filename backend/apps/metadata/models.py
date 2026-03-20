"""
Strutture metadati dinamiche (RF-040..RF-047).
"""
import uuid
import re
from django.db import models
from django.conf import settings

FIELD_TYPES = [
    ("text", "Testo libero"),
    ("number", "Numero"),
    ("date", "Data"),
    ("datetime", "Data e ora"),
    ("boolean", "Sì/No"),
    ("select", "Selezione singola"),
    ("multiselect", "Selezione multipla"),
    ("email", "Email"),
    ("phone", "Telefono"),
    ("textarea", "Testo lungo"),
    ("url", "URL"),
]


def _user_model():
    return settings.AUTH_USER_MODEL


SIGNATURE_FORMAT_CHOICES = [
    ("cades", "CAdES (.p7m)"),
    ("pades_invisible", "PAdES invisibile"),
    ("pades_graphic", "PAdES grafica"),
]


class MetadataStructure(models.Model):
    """Struttura metadati: nome, estensioni consentite, UO consentite (RF-040..RF-042). Firma e conservazione (FASE 10)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    allowed_file_extensions = models.JSONField(
        default=list,
        help_text="Lista estensioni es. ['.pdf', '.docx']. Vuoto = tutti.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_metadata_structures",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    signature_enabled = models.BooleanField(
        default=False,
        help_text="Se True, i documenti di questo tipo possono essere firmati.",
    )
    signature_format = models.CharField(
        max_length=20,
        choices=SIGNATURE_FORMAT_CHOICES,
        default="pades_invisible",
    )
    conservation_enabled = models.BooleanField(default=False)
    conservation_class = models.CharField(max_length=10, default="1")
    conservation_document_type = models.CharField(max_length=200, blank=True)

    applicable_to = models.JSONField(
        default=lambda: ["document"],
        blank=True,
        help_text="Tipi entità: 'document', 'folder', 'dossier', 'email'. Default: ['document'].",
    )

    allowed_signers = models.ManyToManyField(
        _user_model(),
        related_name="metadata_structures_as_allowed_signer",
        blank=True,
        help_text="Firmatari autorizzati per questa struttura. Vuoto = tutti gli APPROVER.",
    )

    class Meta:
        verbose_name = "Struttura metadati"
        verbose_name_plural = "Strutture metadati"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def validate_metadata(self, values):
        """
        Valida values rispetto ai campi della struttura.
        Ritorna lista di errori: [{"field": "name", "message": "..."}, ...]
        """
        from .validators import validate_metadata_values
        return validate_metadata_values(self, values)


class MetadataStructureOU(models.Model):
    """UO consentite a usare questa struttura (vuoto = tutte)."""
    structure = models.ForeignKey(
        MetadataStructure,
        on_delete=models.CASCADE,
        related_name="allowed_organizational_units",
    )
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        on_delete=models.CASCADE,
        related_name="allowed_metadata_structures",
    )

    class Meta:
        unique_together = [["structure", "organizational_unit"]]
        verbose_name = "UO consentita per struttura"
        verbose_name_plural = "UO consentite per struttura"


class MetadataField(models.Model):
    """Campo di una struttura metadati (RF-045)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    structure = models.ForeignKey(
        MetadataStructure,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    is_searchable = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    options = models.JSONField(
        default=list,
        help_text="Per select/multiselect: [{\"value\": \"v1\", \"label\": \"Label 1\"}, ...]",
    )
    default_value = models.JSONField(null=True, blank=True)
    validation_rules = models.JSONField(
        default=dict,
        help_text="Es: {\"min\": 0, \"max\": 100} per number; {\"regex\": \"...\"} per text",
    )
    help_text = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = [["structure", "name"]]
        verbose_name = "Campo metadato"
        verbose_name_plural = "Campi metadato"

    def __str__(self):
        return f"{self.structure.name} — {self.label}"
