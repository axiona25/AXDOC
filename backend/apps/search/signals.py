"""
Indicizzazione automatica alla creazione di una nuova versione documento (FASE 37).
"""
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.documents.models import DocumentVersion


@receiver(post_save, sender=DocumentVersion)
def auto_index_document_version(sender, instance, created, **kwargs):
    """
    Indicizza automaticamente il documento quando viene caricata una nuova versione.
    L'indicizzazione è asincrona (threading) per non bloccare l'upload.
    Se il file non è ancora su disco, index_document termina senza contenuto (es. OCR dopo).
    """
    if not created:
        return
    if not instance.file:
        return

    def _index():
        try:
            from apps.search.tasks import index_document

            index_document(str(instance.pk))
        except Exception:
            pass

    threading.Thread(target=_index, daemon=True).start()
