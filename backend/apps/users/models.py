"""
Modello utente custom per AXDOC (RF-011..RF-020).
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager per il modello User con email come USERNAME_FIELD."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email obbligatoria")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("must_change_password", False)
        return self.create_user(email, password, **extra_fields)


ROLE_CHOICES = [
    ("OPERATOR", "Operatore"),
    ("REVIEWER", "Revisore"),
    ("APPROVER", "Approvatore"),
    ("ADMIN", "Amministratore"),
]

USER_TYPE_CHOICES = [
    ("internal", "Utente interno"),
    ("guest", "Utente ospite"),
]


class User(AbstractBaseUser, PermissionsMixin):
    """
    Utente AXDOC: autenticazione per email, ruoli, blocco account.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default="internal",
        help_text="Interno: accesso pieno; Ospite: solo documenti condivisi.",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="OPERATOR")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    must_change_password = models.BooleanField(default=True)
    # MFA (RF-002, RNF-008)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=256, blank=True)  # cifrato a riposo
    mfa_backup_codes = models.JSONField(default=list, blank=True)  # hash dei codici monouso
    mfa_setup_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
    )
    updated_at = models.DateTimeField(auto_now=True)
    privacy_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Ultima accettazione informativa privacy (GDPR).",
    )
    data_retention_days = models.IntegerField(
        default=3650,
        help_text="Giorni di conservazione dati personali (default 10 anni PA).",
    )
    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "Utente"
        verbose_name_plural = "Utenti"

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def is_locked(self):
        return (
            self.locked_until is not None and self.locked_until > timezone.now()
        )

    def get_primary_ou_name(self):
        """Ritorna il nome della prima UO attiva (FASE 02)."""
        membership = self.ou_memberships.filter(is_active=True).first()
        return membership.organizational_unit.name if membership else ""

    @property
    def is_guest(self):
        return getattr(self, "user_type", "internal") == "guest"

    @property
    def is_internal(self):
        return getattr(self, "user_type", "internal") == "internal"


class UserGroup(models.Model):
    """
    Gruppo trasversale di utenti (RF-016), distinto da UO e ruoli.
    Usabile per permessi su documenti, notifiche, reportistica.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="user_groups",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="groups",
        help_text="Unità organizzativa di appartenenza del gruppo.",
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_groups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Gruppo utenti"
        verbose_name_plural = "Gruppi utenti"

    def __str__(self):
        return self.name


class UserGroupMembership(models.Model):
    """Appartenenza di un utente a un gruppo."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        UserGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    added_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="added_group_memberships",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["group", "user"]]
        verbose_name = "Membro gruppo"
        verbose_name_plural = "Membri gruppo"

    def __str__(self):
        return f"{self.user.email} in {self.group.name}"


CONSENT_TYPE_CHOICES = [
    ("privacy_policy", "Informativa Privacy"),
    ("data_processing", "Trattamento Dati"),
    ("marketing", "Comunicazioni Marketing"),
    ("analytics", "Analisi e Statistiche"),
    ("third_party", "Condivisione Terze Parti"),
]


class ConsentRecord(models.Model):
    """Registro consensi GDPR per utente."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="consents",
    )
    consent_type = models.CharField(max_length=50, choices=CONSENT_TYPE_CHOICES)
    version = models.CharField(
        max_length=20,
        help_text="Versione del documento accettato, es. '1.0'",
    )
    granted = models.BooleanField(help_text="True = consenso dato, False = revocato")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "consent_type"]),
        ]

    def __str__(self):
        action = "granted" if self.granted else "revoked"
        return f"{self.user.email} {action} {self.consent_type} v{self.version}"
