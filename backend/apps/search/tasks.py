"""
Indicizzazione documento (chiamata sincrona dopo upload).
"""
from django.utils import timezone
from .models import DocumentIndex
from .extractors import extract_text


def index_document(document_version_id):
    """
    Estrae testo dalla versione e crea/aggiorna DocumentIndex.
    Chiamato dopo upload nuova versione.
    """
    from apps.documents.models import DocumentVersion
    version = DocumentVersion.objects.filter(pk=document_version_id).select_related("document").first()
    if not version or not version.document_id:
        return
    doc = version.document
    content = ""
    error_msg = ""
    if version.file:
        path = getattr(version.file, "path", None)
        if path and __import__("os").path.isfile(path):
            try:
                content = extract_text(path, getattr(version, "file_type", None) or "")
            except Exception as e:
                error_msg = str(e)[:500]
    DocumentIndex.objects.update_or_create(
        document=doc,
        defaults={
            "document_version": version,
            "content": content,
            "error_message": error_msg,
            "indexed_at": timezone.now(),
        },
    )
