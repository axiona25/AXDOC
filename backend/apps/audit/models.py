"""
Modelli audit supplementari (incidenti di sicurezza NIS2).
"""
import uuid
from django.conf import settings
from django.db import models


class SecurityIncident(models.Model):
    """Registro incidenti di sicurezza (NIS2 / ISO 27001)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="security_incidents",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=[
            ("low", "Basso"),
            ("medium", "Medio"),
            ("high", "Alto"),
            ("critical", "Critico"),
        ],
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("open", "Aperto"),
            ("investigating", "In indagine"),
            ("mitigated", "Mitigato"),
            ("resolved", "Risolto"),
            ("closed", "Chiuso"),
        ],
        default="open",
    )
    category = models.CharField(
        max_length=50,
        choices=[
            ("unauthorized_access", "Accesso non autorizzato"),
            ("data_breach", "Violazione dati"),
            ("malware", "Malware"),
            ("phishing", "Phishing"),
            ("dos", "Denial of Service"),
            ("misconfiguration", "Errata configurazione"),
            ("other", "Altro"),
        ],
    )
    affected_systems = models.TextField(blank=True, default="")
    affected_users_count = models.IntegerField(default=0)
    data_compromised = models.BooleanField(default=False)
    containment_actions = models.TextField(blank=True, default="")
    remediation_actions = models.TextField(blank=True, default="")
    reported_to_authority = models.BooleanField(default=False)
    authority_report_date = models.DateTimeField(null=True, blank=True)
    authority_reference = models.CharField(max_length=100, blank=True, default="")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_incidents",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_incidents",
    )
    detected_at = models.DateTimeField(help_text="Quando è stato rilevato l'incidente")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"
