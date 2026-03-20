"""
Indice full-text per documenti (FASE 12, RF-072).
"""
from django.db import models


class DocumentIndex(models.Model):
    """Contenuto estratto dai file per full-text search."""
    document = models.OneToOneField(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="search_index",
    )
    document_version = models.ForeignKey(
        "documents.DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    content = models.TextField(blank=True)
    indexed_at = models.DateTimeField(auto_now=True)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "Indice documento"
        indexes = [models.Index(fields=["document"])]
