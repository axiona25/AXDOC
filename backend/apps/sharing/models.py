"""
Condivisione documenti e protocolli con link temporanei (FASE 11).
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


SHARE_TARGET_TYPE = [
    ("document", "Documento"),
    ("protocol", "Protocollo"),
]

SHARE_RECIPIENT_TYPE = [
    ("internal", "Utente interno"),
    ("external", "Utente esterno"),
]

SHARE_ACCESS_ACTION = [
    ("view", "Visualizzazione"),
    ("download", "Download"),
]


def _default_token():
    return uuid.uuid4().hex


class ShareLink(models.Model):
    """Link di condivisione per documento o protocollo (interno o esterno)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=64, unique=True, default=_default_token, db_index=True)
    target_type = models.CharField(max_length=20, choices=SHARE_TARGET_TYPE)
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="share_links",
    )
    protocol = models.ForeignKey(
        "protocols.Protocol",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="share_links",
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_share_links",
    )
    recipient_type = models.CharField(max_length=20, choices=SHARE_RECIPIENT_TYPE)

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="received_shares",
    )
    recipient_email = models.EmailField(blank=True)
    recipient_name = models.CharField(max_length=255, blank=True)

    can_download = models.BooleanField(default=True)
    password_protected = models.BooleanField(default=False)
    access_password = models.CharField(max_length=128, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True)
    max_accesses = models.IntegerField(null=True, blank=True)
    access_count = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Link condivisione"
        verbose_name_plural = "Link condivisione"

    def __str__(self):
        dest = self.recipient_user.email if self.recipient_user else self.recipient_email or "—"
        return f"Share {self.target_type} → {dest}"

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() >= self.expires_at:
            return False
        if self.max_accesses is not None and self.access_count >= self.max_accesses:
            return False
        return True

    def get_absolute_url(self):
        return f"/share/{self.token}"


class ShareAccessLog(models.Model):
    """Log ogni accesso al link pubblico."""
    share_link = models.ForeignKey(
        ShareLink,
        on_delete=models.CASCADE,
        related_name="access_logs",
    )
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    action = models.CharField(max_length=20, choices=SHARE_ACCESS_ACTION)

    class Meta:
        ordering = ["-accessed_at"]
