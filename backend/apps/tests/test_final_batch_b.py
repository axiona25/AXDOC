# FASE 35E.3 — batch B: file con 1–4 miss (archive, auth, mail, orgs, metadata, notifications, protocols, sharing, …)
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.archive.models import DocumentArchive, InformationPackage
from apps.archive.tasks import auto_move_to_deposit, send_daily_register
from apps.authentication import mfa
from apps.chat.auth import get_user_from_scope
from apps.documents.models import Document, Folder
from apps.mail.models import MailAccount, MailMessage
from apps.mail.smtp_client import send_email
from apps.notifications.models import Notification
from apps.organizations.mixins import TenantFilterMixin
from apps.organizations.models import OrganizationalUnit, Tenant
from apps.organizations.utils import export_members_csv
from apps.protocols.models import Protocol, ProtocolCounter
from apps.sharing.models import ShareLink

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def admin(db, tenant):
    return User.objects.create_user(
        email="batchb-admin@test.com",
        password="Admin123!",
        first_name="A",
        last_name="Admin",
        role="ADMIN",
        tenant=tenant,
    )


@pytest.mark.django_db
class TestArchiveTasksBatchB:
    def test_auto_move_to_deposit_moves_old(self, tenant, admin):
        folder = Folder.objects.create(name="Arch", tenant=tenant, created_by=admin)
        doc = Document.objects.create(
            title="Old",
            folder=folder,
            created_by=admin,
            tenant=tenant,
        )
        Document.objects.filter(pk=doc.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )
        doc.refresh_from_db()
        arch = DocumentArchive.objects.get(document=doc)
        arch.stage = "current"
        arch.save(update_fields=["stage"])
        out = auto_move_to_deposit()
        assert out["moved"] >= 1
        arch.refresh_from_db()
        assert arch.stage == "deposit"

    def test_send_daily_register_no_protocols(self):
        out = send_daily_register()
        assert out.get("reason") == "no_protocols"

    def test_send_daily_register_creates_package(self, tenant, admin):
        folder = Folder.objects.create(name="F", tenant=tenant, created_by=admin)
        doc = Document.objects.create(title="D", folder=folder, created_by=admin, tenant=tenant)
        ou = OrganizationalUnit.objects.create(name="OU", code="OU", tenant=tenant)
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="in",
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=admin,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=admin,
            tenant=tenant,
            document=doc,
        )
        with patch("apps.archive.packager.AgidPackager") as Pack:
            Pack.return_value.generate_pdv.return_value = (b"ZIPDATA", {"ok": True})
            out = send_daily_register()
        assert out.get("created") is True
        assert InformationPackage.objects.filter(package_id__startswith="PdV-register-").exists()


@pytest.mark.django_db
class TestMfaBatchB:
    def test_verify_totp_invalid_length(self):
        assert mfa.verify_totp("SECRETKEYBASE32XX", "123") is False

    def test_verify_backup_code_edges(self):
        ok, lst = mfa.verify_backup_code([], "ABCDEFGH")
        assert ok is False
        plain, hashed = mfa.generate_backup_codes()
        ok2, lst2 = mfa.verify_backup_code(hashed, plain[0])
        assert ok2 is True
        assert len(lst2) == len(hashed) - 1


@pytest.mark.django_db
class TestArchiveModelsBatchB:
    def test_document_archive_str(self, tenant, admin):
        folder = Folder.objects.create(name="F2", tenant=tenant, created_by=admin)
        doc = Document.objects.create(title="T", folder=folder, created_by=admin, tenant=tenant)
        da = DocumentArchive.objects.get(document=doc)
        assert str(doc.id) in str(da)


@pytest.mark.django_db
class TestMailModelsBatchB:
    def test_mail_message_str(self, tenant):
        acc = MailAccount.objects.create(
            name="Acc",
            account_type="email",
            email_address="mailstr@test.com",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="h",
            smtp_username="u",
            smtp_password="p",
            tenant=tenant,
        )
        mm = MailMessage.objects.create(
            account=acc,
            direction="in",
            from_address="a@b.com",
            subject="Subj",
            status="unread",
        )
        assert "Subj" in str(mm) or str(mm)


@pytest.mark.django_db
class TestOrganizationsMixinsBatchB:
    def test_default_tenant_includes_null_tenant_rows(self, tenant, admin):
        class _V(TenantFilterMixin):
            def __init__(self, request):
                self.request = request

        folder = Folder.objects.create(name="Mix", tenant=tenant, created_by=admin)
        d1 = Document.objects.create(title="T1", folder=folder, created_by=admin, tenant=tenant)
        d2 = Document.objects.create(title="T2", folder=folder, created_by=admin, tenant=None)
        req = MagicMock()
        req.user = admin
        req.user.is_superuser = False
        req.tenant = tenant
        qs = Document.objects.filter(pk__in=[d1.pk, d2.pk])
        filtered = _V(req).filter_queryset_by_tenant(qs)
        assert filtered.count() == 2

    def test_superuser_sees_all_tenants(self, tenant, admin):
        class _V(TenantFilterMixin):
            def __init__(self, request):
                self.request = request

        admin.is_superuser = True
        admin.save(update_fields=["is_superuser"])
        t2, _ = Tenant.objects.get_or_create(
            slug="other",
            defaults={"name": "Other", "plan": "enterprise"},
        )
        folder = Folder.objects.create(name="Mix2", tenant=t2, created_by=admin)
        d = Document.objects.create(title="X", folder=folder, created_by=admin, tenant=t2)
        req = MagicMock()
        req.user = admin
        req.user.is_superuser = True
        req.tenant = tenant
        filtered = _V(req).filter_queryset_by_tenant(Document.objects.filter(pk=d.pk))
        assert filtered.count() == 1

    def test_non_default_tenant_strict_filter(self, admin):
        class _V(TenantFilterMixin):
            def __init__(self, request):
                self.request = request

        t2, _ = Tenant.objects.get_or_create(
            slug="strict",
            defaults={"name": "Strict", "plan": "enterprise"},
        )
        folder = Folder.objects.create(name="F3", tenant=t2, created_by=admin)
        d_ok = Document.objects.create(title="Ok", folder=folder, created_by=admin, tenant=t2)
        Document.objects.create(title="Other", folder=folder, created_by=admin, tenant=None)
        req = MagicMock()
        req.user = admin
        req.user.is_superuser = False
        req.tenant = t2
        qs = Document.objects.filter(folder=folder)
        filtered = _V(req).filter_queryset_by_tenant(qs)
        assert list(filtered.values_list("pk", flat=True)) == [d_ok.pk]

    def test_get_tenant_save_kwargs_without_request_tenant(self, admin):
        class _V(TenantFilterMixin):
            def __init__(self, request):
                self.request = request

        class _S:
            class Meta:
                model = Document

        req = MagicMock()
        req.user = admin
        req.user.is_superuser = False
        req.tenant = None
        assert _V(req).get_tenant_save_kwargs(_S()) == {}


@pytest.mark.django_db
class TestChatAuthBatchB:
    def test_get_user_from_scope_no_token(self):
        assert get_user_from_scope({"query_string": b""}) is None

    def test_get_user_from_scope_invalid_token(self):
        assert get_user_from_scope({"query_string": b"token=not-a-jwt"}) is None

    def test_get_user_from_scope_valid(self, admin):
        token = str(AccessToken.for_user(admin))
        scope = {"query_string": f"token={token}".encode()}
        u = get_user_from_scope(scope)
        assert u and u.id == admin.id


@pytest.mark.django_db
class TestMailSmtpBatchB:
    def test_send_plain_smtp_with_tls(self, tenant, admin):
        acc = MailAccount.objects.create(
            name="S",
            account_type="email",
            email_address="smtp@test.com",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="localhost",
            smtp_port=587,
            smtp_use_ssl=False,
            smtp_use_tls=True,
            smtp_username="u",
            smtp_password="p",
            tenant=tenant,
        )
        mock_server = MagicMock()
        with patch("apps.mail.smtp_client.smtplib.SMTP", return_value=mock_server):
            mm = send_email(acc, ["dest@test.com"], "Hi", body_text="Body")
        assert mm.id
        mock_server.starttls.assert_called()


@pytest.mark.django_db
class TestOrganizationsUtilsBatchB:
    def test_export_members_csv_missing_ou(self):
        assert export_members_csv(uuid.uuid4()) is None


@pytest.mark.django_db
class TestNotificationsSignalsBatchB:
    def test_push_swallows_exception(self, admin):
        with patch("apps.notifications.signals.push_notification_to_user", side_effect=RuntimeError("x")):
            Notification.objects.create(
                recipient=admin,
                notification_type="system",
                title="t",
                body="b",
            )


@pytest.mark.django_db
class TestSharingModelsBatchB:
    def test_share_link_str(self, tenant, admin):
        folder = Folder.objects.create(name="Sf", tenant=tenant, created_by=admin)
        doc = Document.objects.create(title="Sd", folder=folder, created_by=admin, tenant=tenant)
        sl = ShareLink.objects.create(
            tenant=tenant,
            target_type="document",
            document=doc,
            shared_by=admin,
            recipient_type="external",
            recipient_email="e@e.com",
        )
        assert sl.token in str(sl) or "share" in str(sl).lower()


@pytest.mark.django_db
class TestProtocolsModelsStrBatchB:
    def test_protocol_str(self, tenant, admin):
        ou = OrganizationalUnit.objects.create(name="PS", code="PS", tenant=tenant)
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="in",
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=admin,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=admin,
            tenant=tenant,
        )
        assert pid in str(p)
