"""
Rubrica contatti esterni (persone e aziende non utenti del sistema).
"""
import uuid

from django.conf import settings
from django.db import models


CONTACT_TYPE = [
    ("person", "Persona"),
    ("company", "Azienda/Ente"),
]


class Contact(models.Model):
    """Contatto esterno (persona o azienda)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_type = models.CharField(max_length=10, choices=CONTACT_TYPE, default="person")

    # Dati anagrafici
    first_name = models.CharField(max_length=200, blank=True)
    last_name = models.CharField(max_length=200, blank=True)
    company_name = models.CharField(max_length=300, blank=True, help_text="Nome azienda/ente")
    job_title = models.CharField(max_length=200, blank=True, help_text="Ruolo/qualifica")
    tax_code = models.CharField(max_length=20, blank=True, help_text="Codice fiscale / P.IVA")

    # Contatti
    email = models.EmailField(blank=True, db_index=True)
    pec = models.EmailField(blank=True, help_text="PEC")
    phone = models.CharField(max_length=30, blank=True)
    mobile = models.CharField(max_length=30, blank=True)

    # Indirizzo
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=5, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=100, blank=True, default="Italia")

    # Metadati
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True, help_text='["fornitore", "cliente"]')
    is_favorite = models.BooleanField(default=False)

    # Ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_contacts",
    )
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contacts",
        help_text="U.O. proprietaria del contatto",
    )
    is_shared = models.BooleanField(default=True, help_text="Visibile a tutti gli utenti")

    # Origine
    source = models.CharField(max_length=20, default="manual", help_text="manual | mail_import | protocol")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name", "company_name"]
        verbose_name = "Contatto"
        verbose_name_plural = "Contatti"

    def __str__(self):
        if self.contact_type == "company":
            return self.company_name or self.email or str(self.id)
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email or str(self.id)

    @property
    def display_name(self):
        """Nome per visualizzazione UI."""
        if self.contact_type == "company":
            return self.company_name or self.email
        name = f"{self.first_name} {self.last_name}".strip()
        if name and self.company_name:
            return f"{name} ({self.company_name})"
        return name or self.email

    @property
    def primary_email(self):
        """Email principale (PEC se disponibile, altrimenti email)."""
        return self.pec or self.email
