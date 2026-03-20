"""
Task Celery per archivio (FASE 21).
auto_move_to_deposit: ogni domenica, sposta documenti correnti > 12 mesi → deposito.
send_daily_register: ogni giorno, genera registro protocollo + crea PdV automatico.
"""
from django.utils import timezone
from datetime import timedelta

try:
    from celery import shared_task
except ImportError:
    def shared_task(f):
        return f


@shared_task
def auto_move_to_deposit():
    """Sposta in deposito i documenti in Archivio Corrente da più di 12 mesi."""
    from .models import DocumentArchive
    threshold = timezone.now() - timedelta(days=365)
    qs = DocumentArchive.objects.filter(
        stage="current",
        document__created_at__lt=threshold,
        document__is_deleted=False,
    )
    count = 0
    for rec in qs:
        rec.stage = "deposit"
        rec.archive_date = timezone.now()
        rec.save(update_fields=["stage", "archive_date", "updated_at"])
        count += 1
    return {"moved": count}


@shared_task
def send_daily_register():
    """Genera registro protocollo del giorno e crea PdV automatico (mock)."""
    from apps.protocols.models import Protocol
    from .models import InformationPackage
    from django.contrib.auth import get_user_model
    User = get_user_model()
    today = timezone.now().date()
    protocols = list(Protocol.objects.filter(registered_at__date=today))
    if not protocols:
        return {"created": False, "reason": "no_protocols"}
    admin = User.objects.filter(role="ADMIN").first()
    if not admin:
        return {"created": False, "reason": "no_admin"}
    from .packager import AgidPackager
    from apps.documents.models import Document
    docs = list(Document.objects.filter(id__in=[p.document_id for p in protocols if p.document_id]))
    packager = AgidPackager()
    zip_bytes, manifest = packager.generate_pdv(docs, protocols, [])
    import hashlib
    from django.core.files.base import ContentFile
    package_id = f"PdV-register-{today.isoformat()}"
    pkg = InformationPackage.objects.create(
        package_type="PdV",
        package_id=package_id,
        created_by=admin,
        status="ready",
        checksum=hashlib.sha256(zip_bytes).hexdigest(),
    )
    pkg.package_file.save(f"{package_id}.zip", ContentFile(zip_bytes), save=True)
    return {"created": True, "package_id": package_id}
