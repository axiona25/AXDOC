"""Test task Celery archivio (FASE 33)."""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model
from apps.documents.models import Document, Folder
from apps.archive.models import DocumentArchive, InformationPackage
from apps.archive.tasks import auto_move_to_deposit, send_daily_register
from apps.organizations.models import OrganizationalUnit
from apps.protocols.models import Protocol

User = get_user_model()


@pytest.mark.django_db
class TestArchiveTasks:
    def test_auto_move_to_deposit_moves_old(self, db):
        u = User.objects.create_user(email="arch-t1@test.com", password="test")
        f = Folder.objects.create(name="FA")
        old = Document.objects.create(
            title="Old doc",
            folder=f,
            created_by=u,
            status=Document.STATUS_APPROVED,
        )
        old.created_at = timezone.now() - timedelta(days=400)
        old.save(update_fields=["created_at"])
        rec = old.archive_record
        rec.stage = "current"
        rec.save(update_fields=["stage"])

        res = auto_move_to_deposit()
        assert res.get("moved", 0) >= 1
        rec.refresh_from_db()
        assert rec.stage == "deposit"

    def test_auto_move_to_deposit_no_candidates(self, db):
        res = auto_move_to_deposit()
        assert res.get("moved", 0) == 0

    @patch(
        "apps.archive.packager.AgidPackager.generate_pdv",
        return_value=(b"PK\x03\x04fake", {"type": "PdV"}),
    )
    def test_send_daily_register_creates_package(self, mock_pdv, db):
        today = timezone.now().date()
        InformationPackage.objects.filter(package_id=f"PdV-register-{today.isoformat()}").delete()
        admin = User.objects.create_user(email="adm-arch@test.com", password="test", role="ADMIN")
        ou = OrganizationalUnit.objects.create(name="OU", code="OU1")
        u = User.objects.create_user(email="usr-arch@test.com", password="test")
        f = Folder.objects.create(name="F")
        doc = Document.objects.create(title="D", folder=f, created_by=u, status=Document.STATUS_APPROVED)
        p = Protocol.objects.create(
            organizational_unit=ou,
            direction="out",
            subject="S",
            registered_by=u,
            created_by=u,
            document=doc,
            registered_at=timezone.now(),
        )
        res = send_daily_register()
        assert res.get("created") is True
        assert "package_id" in res

    def test_send_daily_register_no_protocols(self, db):
        res = send_daily_register()
        assert res.get("created") is False
        assert res.get("reason") == "no_protocols"
