"""
Modelli per autenticazione: token reset password, audit log, inviti (RF-003, RF-004, RF-010, RF-018, RNF-007).
"""
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta

INVITATION_EXPIRY_DAYS = 7


class PasswordResetToken(models.Model):
    """Token monouso per reset password (scadenza 1h)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    class Meta:
        verbose_name = "Token reset password"


ACTION_CHOICES = [
    ("LOGIN", "Login"),
    ("LOGIN_FAILED", "Login Fallito"),
    ("LOGOUT", "Logout"),
    ("PASSWORD_RESET", "Reset Password"),
    ("PASSWORD_CHANGED", "Password Cambiata"),
    ("USER_CREATED", "Utente Creato"),
    ("USERS_IMPORTED", "Import utenti"),
    ("USER_UPDATED", "Utente Modificato"),
    ("USER_INVITED", "Invito Inviato"),
    ("INVITATION_ACCEPTED", "Invito Accettato"),
    ("DOCUMENT_CREATED", "Documento Creato"),
    ("DOCUMENT_UPLOADED", "Documento Caricato"),
    ("DOCUMENT_DOWNLOADED", "Documento Scaricato"),
    ("DOCUMENT_DELETED", "Documento Eliminato"),
    ("DOCUMENT_SHARED", "Documento Condiviso"),
    ("WORKFLOW_STARTED", "Workflow Avviato"),
    ("WORKFLOW_APPROVED", "Documento Approvato"),
    ("WORKFLOW_REJECTED", "Documento Rifiutato"),
    ("PROTOCOL_CREATED", "Protocollo Creato"),
    ("DOCUMENT_SIGNED", "Documento Firmato"),
    ("DOCUMENT_CONSERVED", "Documento in Conservazione"),
    ("DOCUMENT_ENCRYPTED", "Documento Cifrato"),
    ("USER_ANONYMIZED", "Utente anonimizzato"),
]


class AuditLog(models.Model):
    """Registro azioni per tracciabilità (RF-010, RNF-007)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        "users.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"

    @classmethod
    def log(cls, user, action, detail=None, request=None):
        ip = None
        ua = ""
        tenant = None
        if request:
            x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = (
                x_forwarded.split(",")[0].strip()
                if x_forwarded
                else request.META.get("REMOTE_ADDR")
            )
            ua = request.META.get("HTTP_USER_AGENT", "") or ""
            tenant = getattr(request, "tenant", None)
        if tenant is None:
            try:
                from apps.organizations.middleware import get_current_tenant

                tenant = get_current_tenant()
            except Exception:
                tenant = None
        cls.objects.create(
            user=user,
            tenant=tenant,
            action=action,
            detail=detail or {},
            ip_address=ip,
            user_agent=ua[:500],
        )


class UserInvitation(models.Model):
    """Invito utente via email (RF-018). Link valido 7 giorni."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    invited_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitations",
    )
    role = models.CharField(max_length=20, default="OPERATOR")  # ruolo globale utente
    ou_role = models.CharField(max_length=20, blank=True, default="OPERATOR")  # ruolo nella UO
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=INVITATION_EXPIRY_DAYS)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    class Meta:
        verbose_name = "Invito utente"
        ordering = ["-created_at"]
