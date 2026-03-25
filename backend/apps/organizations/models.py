"""
Unità Organizzative e membership (RF-021..RF-027).
Multi-tenant: Tenant (FASE 29).
"""
import uuid
from django.db import models
from django.conf import settings


class Tenant(models.Model):
    """
    Organizzazione root (tenant) per multi-tenancy.
    Schema condiviso con discriminatore tenant_id (MySQL-friendly).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Nome organizzazione")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Identificativo URL-safe (es. comune-milano)",
    )
    domain = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Dominio personalizzato. Vuoto = subdomain o default.",
    )
    logo_url = models.URLField(blank=True, default="")
    primary_color = models.CharField(
        max_length=7,
        default="#4f46e5",
        help_text="Colore primario HEX",
    )
    max_users = models.IntegerField(default=50, help_text="Numero massimo utenti")
    max_storage_gb = models.IntegerField(default=10, help_text="Storage massimo in GB")
    plan = models.CharField(
        max_length=20,
        choices=[
            ("free", "Free"),
            ("starter", "Starter"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ],
        default="starter",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationalUnit(models.Model):
    """Unità organizzativa con gerarchia parent/children (RF-024)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="organizational_units",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)  # RF-027
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_organizational_units",
    )

    class Meta:
        verbose_name = "Unità Organizzativa"
        verbose_name_plural = "Unità Organizzative"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def get_ancestors(self):
        """Lista UO parent fino alla radice."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """Lista UO figlie ricorsiva."""
        descendants = list(self.children.filter(is_active=True))
        for child in list(descendants):
            descendants.extend(child.get_descendants())
        return descendants

    def get_all_members(self):
        """Tutti gli utenti membri di questa UO e delle figlie (attivi)."""
        user_ids = set(
            self.memberships.filter(is_active=True).values_list("user_id", flat=True)
        )
        for child in self.get_descendants():
            user_ids.update(
                child.memberships.filter(is_active=True).values_list("user_id", flat=True)
            )
        from django.contrib.auth import get_user_model
        return get_user_model().objects.filter(pk__in=user_ids)


OU_ROLE_CHOICES = [
    ("OPERATOR", "Operatore"),
    ("REVIEWER", "Revisore"),
    ("APPROVER", "Approvatore"),
]


class OrganizationalUnitMembership(models.Model):
    """Assegnazione utente a UO con ruolo (RF-025)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ou_memberships",
    )
    organizational_unit = models.ForeignKey(
        OrganizationalUnit,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=OU_ROLE_CHOICES, default="OPERATOR")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [["user", "organizational_unit"]]
        verbose_name = "Membership UO"
        verbose_name_plural = "Membership UO"

    def __str__(self):
        return f"{self.user} in {self.organizational_unit} ({self.role})"
