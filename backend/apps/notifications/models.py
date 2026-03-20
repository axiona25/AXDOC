"""
Notifiche in-app (RF-057, FASE 12).
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


NOTIFICATION_TYPE = [
    ("workflow_assigned", "Workflow assegnato"),
    ("workflow_approved", "Documento approvato"),
    ("workflow_rejected", "Documento rifiutato"),
    ("workflow_changes_requested", "Modifiche richieste"),
    ("workflow_completed", "Workflow completato"),
    ("document_shared", "Documento condiviso"),
    ("mention", "Menzione"),
    ("system", "Sistema"),
    ("signature_requested", "Firma richiesta"),
    ("signature_completed", "Firma completata"),
    ("signature_rejected", "Firma rifiutata"),
    ("signature_step_completed", "Step firma completato"),
]


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=40, choices=NOTIFICATION_TYPE)
    title = models.CharField(max_length=300)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    link_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} → {self.recipient.email}"
