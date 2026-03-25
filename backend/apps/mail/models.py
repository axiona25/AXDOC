"""
Modelli per il client di posta PEC/Email di AXDOC.
"""
import uuid

from django.conf import settings
from django.db import models


class MailAccount(models.Model):
    """Account di posta configurato (IMAP + SMTP)."""

    tenant = models.ForeignKey(
        "organizations.Tenant",
        on_delete=models.CASCADE,
        related_name="mail_accounts",
        null=True,
        blank=True,
    )

    ACCOUNT_TYPE_CHOICES = [
        ("email", "Email"),
        ("pec", "PEC"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Nome visualizzato (es: PEC Aziendale)")
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES, default="email")
    email_address = models.EmailField(unique=True)

    # IMAP (ricezione)
    imap_host = models.CharField(max_length=255)
    imap_port = models.IntegerField(default=993)
    imap_use_ssl = models.BooleanField(default=True)
    imap_username = models.CharField(max_length=255)
    imap_password = models.CharField(max_length=500, help_text="Cifrata a riposo in futuro")

    # SMTP (invio)
    smtp_host = models.CharField(max_length=255)
    smtp_port = models.IntegerField(default=465)
    smtp_use_ssl = models.BooleanField(default=True)
    smtp_use_tls = models.BooleanField(default=False)
    smtp_username = models.CharField(max_length=255)
    smtp_password = models.CharField(max_length=500)

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Account predefinito per l'invio")
    last_fetch_at = models.DateTimeField(null=True, blank=True)
    last_fetch_uid = models.CharField(max_length=100, blank=True, help_text="Ultimo UID IMAP scaricato")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Account di posta"
        verbose_name_plural = "Account di posta"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} ({self.email_address})"


MAIL_DIRECTION_CHOICES = [
    ("in", "Ricevuta"),
    ("out", "Inviata"),
]

MAIL_STATUS_CHOICES = [
    ("unread", "Non letta"),
    ("read", "Letta"),
    ("archived", "Archiviata"),
    ("trash", "Cestinata"),
]


class MailMessage(models.Model):
    """Singola email ricevuta o inviata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(MailAccount, on_delete=models.CASCADE, related_name="messages")
    direction = models.CharField(max_length=5, choices=MAIL_DIRECTION_CHOICES, default="in")
    message_id = models.CharField(max_length=500, blank=True, help_text="Message-ID header")
    in_reply_to = models.CharField(max_length=500, blank=True, help_text="In-Reply-To header")

    from_address = models.EmailField()
    from_name = models.CharField(max_length=300, blank=True)
    to_addresses = models.JSONField(default=list, help_text='[{"email": "...", "name": "..."}]')
    cc_addresses = models.JSONField(default=list, blank=True)
    bcc_addresses = models.JSONField(default=list, blank=True)

    subject = models.CharField(max_length=1000, blank=True)
    body_text = models.TextField(blank=True, help_text="Corpo in testo semplice")
    body_html = models.TextField(blank=True, help_text="Corpo in HTML")
    has_attachments = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=MAIL_STATUS_CHOICES, default="unread")
    is_starred = models.BooleanField(default=False)
    folder = models.CharField(max_length=100, default="INBOX")
    imap_uid = models.CharField(max_length=100, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True, help_text="Data invio/ricezione dal header")
    fetched_at = models.DateTimeField(auto_now_add=True)

    protocol = models.ForeignKey(
        "protocols.Protocol",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="emails",
    )

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Email"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["account", "folder", "sent_at"]),
            models.Index(fields=["message_id"]),
        ]

    def __str__(self):
        return f"{self.subject} ({self.from_address})"


class MailAttachment(models.Model):
    """Allegato di una email."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(MailMessage, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=500)
    content_type = models.CharField(max_length=200, blank=True)
    size = models.IntegerField(default=0)
    file = models.FileField(upload_to="mail_attachments/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Allegato email"
        verbose_name_plural = "Allegati email"

    def __str__(self):
        return self.filename
