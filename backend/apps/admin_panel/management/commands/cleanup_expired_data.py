from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Pulisce dati scaduti secondo le policy di data retention GDPR."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe eliminato senza farlo.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        from apps.admin_panel.models import SystemSettings

        try:
            settings_obj = SystemSettings.objects.first()
            audit_days = (
                settings_obj.gdpr_audit_retention_days if settings_obj else 1825
            )
            doc_days = settings_obj.gdpr_data_retention_days if settings_obj else 3650
        except Exception:
            audit_days = 1825
            doc_days = 3650

        from apps.authentication.models import AuditLog

        audit_cutoff = now - timedelta(days=audit_days)
        expired_audit = AuditLog.objects.filter(timestamp__lt=audit_cutoff)
        audit_count = expired_audit.count()
        if not dry_run:
            expired_audit.delete()
        self.stdout.write(
            f"{'[DRY RUN] ' if dry_run else ''}Audit log eliminati: {audit_count}"
        )

        from apps.documents.models import Document

        doc_cutoff = now - timedelta(days=doc_days)
        expired_docs = Document.objects.filter(
            is_deleted=True, updated_at__lt=doc_cutoff
        )
        doc_count = expired_docs.count()
        if not dry_run:
            expired_docs.delete()
        self.stdout.write(
            f"{'[DRY RUN] ' if dry_run else ''}Documenti eliminati definitivamente: {doc_count}"
        )

        from apps.notifications.models import Notification

        notif_cutoff = now - timedelta(days=90)
        expired_notifs = Notification.objects.filter(
            is_read=True, created_at__lt=notif_cutoff
        )
        notif_count = expired_notifs.count()
        if not dry_run:
            expired_notifs.delete()
        self.stdout.write(
            f"{'[DRY RUN] ' if dry_run else ''}Notifiche lette eliminate: {notif_count}"
        )

        from apps.sharing.models import ShareLink

        expired_shares = ShareLink.objects.filter(
            expires_at__isnull=False, expires_at__lt=now
        )
        share_count = expired_shares.count()
        if not dry_run:
            expired_shares.delete()
        self.stdout.write(
            f"{'[DRY RUN] ' if dry_run else ''}Share link scaduti eliminati: {share_count}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] ' if dry_run else ''}Pulizia completata."
            )
        )
