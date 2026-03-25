"""Test cleanup_expired_data (FASE 28)."""
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.authentication.models import AuditLog
from apps.admin_panel.models import SystemSettings
from apps.sharing.models import ShareLink
from apps.users.models import User
from apps.documents.models import Document, Folder


class CleanupExpiredDataTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cleanup@test.com",
            password="TestPass123!",
            first_name="C",
            last_name="Lean",
            must_change_password=False,
        )

    def test_cleanup_deletes_old_audit_logs(self):
        log = AuditLog.objects.create(user=self.user, action="LOGIN", detail={})
        old = timezone.now() - timedelta(days=2000)
        AuditLog.objects.filter(pk=log.pk).update(timestamp=old)
        call_command("cleanup_expired_data")
        self.assertFalse(AuditLog.objects.filter(pk=log.pk).exists())

    def test_cleanup_dry_run_does_not_delete(self):
        log = AuditLog.objects.create(user=self.user, action="LOGIN", detail={})
        old = timezone.now() - timedelta(days=2000)
        AuditLog.objects.filter(pk=log.pk).update(timestamp=old)
        call_command("cleanup_expired_data", dry_run=True)
        self.assertTrue(AuditLog.objects.filter(pk=log.pk).exists())

    def test_cleanup_deletes_expired_share_links(self):
        folder = Folder.objects.create(name="f", created_by=self.user)
        doc = Document.objects.create(
            title="d",
            created_by=self.user,
            folder=folder,
            owner=self.user,
        )
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=self.user,
            recipient_type="external",
            recipient_email="x@y.z",
            expires_at=timezone.now() - timedelta(days=1),
        )
        call_command("cleanup_expired_data")
        self.assertFalse(ShareLink.objects.filter(pk=share.pk).exists())

    def test_respects_systemsettings_retention(self):
        SystemSettings.objects.update_or_create(
            pk=1,
            defaults={
                "gdpr_audit_retention_days": 30,
                "gdpr_data_retention_days": 3650,
            },
        )
        log = AuditLog.objects.create(user=self.user, action="LOGIN", detail={})
        old = timezone.now() - timedelta(days=60)
        AuditLog.objects.filter(pk=log.pk).update(timestamp=old)
        call_command("cleanup_expired_data")
        self.assertFalse(AuditLog.objects.filter(pk=log.pk).exists())
