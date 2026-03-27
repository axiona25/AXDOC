# FASE 35E.2 — batch A: file con 3–6 miss (workflows, notifications, sharing, mail, dashboard, chat, auth, admin, protocols, contacts)
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admin_panel.middleware import LicenseCheckMiddleware
from apps.admin_panel.models import SystemLicense
from apps.chat.models import ChatRoom, ChatMembership, ChatMessage
from apps.chat.serializers import ChatMembershipSerializer, ChatRoomSerializer
from apps.contacts.models import Contact
from apps.dashboard.export_service import ExportService
from apps.documents.models import Document, Folder
from apps.mail.imap_client import fetch_new_emails
from apps.mail.models import MailAccount
from apps.mail.serializers import MailAttachmentSerializer
from apps.notifications.services import NotificationService
from apps.organizations.models import OrganizationalUnit, Tenant
from apps.protocols.models import Protocol, ProtocolCounter
from apps.sharing.models import ShareLink
from apps.sharing.serializers import (
    PublicShareSerializer,
    ShareLinkCreateSerializer,
)
from apps.workflows.models import WorkflowInstance, WorkflowTemplate

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def admin(db):
    return User.objects.create_user(
        email="batcha-admin@test.com",
        password="Admin123!",
        first_name="A",
        last_name="Admin",
        role="ADMIN",
    )


@pytest.fixture
def folder(db, admin):
    return Folder.objects.create(name="BatchA", created_by=admin)


@pytest.fixture
def document(db, admin, folder):
    return Document.objects.create(
        title="Doc BatchA",
        folder=folder,
        status=Document.STATUS_DRAFT,
        created_by=admin,
    )


@pytest.mark.django_db
class TestWorkflowsViewsBatchA:
    """Copre perform_create/update/destroy su template bozza e deadline su istanza."""

    def test_draft_template_step_create_patch_delete(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="DraftTpl", created_by=admin, is_published=False)
        r = api_client.post(
            f"/api/workflows/templates/{tpl.id}/steps/",
            {
                "name": "S1",
                "action": "review",
                "assignee_type": "role",
                "assignee_role": "ADMIN",
            },
            format="json",
        )
        assert r.status_code == 201
        step_id = r.data["id"]
        r2 = api_client.patch(
            f"/api/workflows/templates/{tpl.id}/steps/{step_id}/",
            {"instructions": "ok"},
            format="json",
        )
        assert r2.status_code == 200
        r3 = api_client.delete(f"/api/workflows/templates/{tpl.id}/steps/{step_id}/")
        assert r3.status_code == 204

    def test_instance_deadline_when_step_has_deadline_days(self, api_client, admin, document):
        api_client.force_authenticate(user=admin)
        tpl = WorkflowTemplate.objects.create(name="DeadlineTpl", created_by=admin, is_published=False)
        api_client.post(
            f"/api/workflows/templates/{tpl.id}/steps/",
            {
                "name": "S1",
                "action": "review",
                "assignee_type": "role",
                "assignee_role": "ADMIN",
                "deadline_days": 4,
            },
            format="json",
        )
        tpl.is_published = True
        tpl.save(update_fields=["is_published"])
        resp = api_client.post(
            "/api/workflows/instances/",
            {"document": str(document.id), "template": str(tpl.id)},
            format="json",
        )
        assert resp.status_code == 201
        wi = WorkflowInstance.objects.get(id=resp.data["id"])
        si = wi.step_instances.select_related("step").first()
        assert si.step.deadline_days == 4
        assert si.deadline is not None


@pytest.mark.django_db
class TestNotificationsServicesBatchA:
    def test_tenant_id_swallows_get_current_tenant_exception(self):
        u = User.objects.create_user(
            email="nsv1@test.com",
            password="TestPass123!",
            first_name="N",
            last_name="S",
        )
        with patch(
            "apps.organizations.middleware.get_current_tenant",
            side_effect=RuntimeError("no tenant"),
        ):
            n = NotificationService.send(
                u,
                "test_type",
                "t",
                "b",
            )
        assert n.id


@pytest.mark.django_db
class TestSharingSerializersBatchA:
    def test_create_serializer_validation(self):
        s = ShareLinkCreateSerializer(data={"recipient_type": "internal"})
        assert s.is_valid() is False
        assert "recipient_user_id" in s.errors
        s2 = ShareLinkCreateSerializer(data={"recipient_type": "external", "recipient_email": "  "})
        assert s2.is_valid() is False
        assert "recipient_email" in s2.errors

    def test_public_share_protocol_branch_and_accesses(self, tenant, admin):
        ou = OrganizationalUnit.objects.create(name="OU", code="OU", tenant=tenant)
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="in",
            subject="Subj",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=admin,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=admin,
            tenant=tenant,
        )
        sl = ShareLink(
            tenant=tenant,
            target_type="protocol",
            protocol=p,
            shared_by=admin,
            recipient_type="external",
            recipient_email="x@y.com",
            max_accesses=10,
            access_count=3,
        )
        sl.save()
        ser = PublicShareSerializer(sl)
        data = ser.data
        assert data["document"]["status"] == "protocol"
        assert data["accesses_remaining"] == 7
        sl.max_accesses = None
        assert PublicShareSerializer(sl).data["accesses_remaining"] is None


@pytest.mark.django_db
class TestSharingServicesNotifyExceptionBatchA:
    def test_internal_notify_failure_still_succeeds(self, tenant):
        u1 = User.objects.create_user(
            email="se1@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        u2 = User.objects.create_user(
            email="se2@test.com",
            password="TestPass123!",
            first_name="C",
            last_name="D",
        )
        folder = Folder.objects.create(name="Fs", tenant=tenant, created_by=u1)
        doc = Document.objects.create(title="Ds", folder=folder, created_by=u1, owner=u1)
        req = MagicMock()
        req.user = u1
        req.tenant = tenant
        req.META = {"REMOTE_ADDR": "127.0.0.1"}
        from apps.sharing.services import create_share_link

        with patch(
            "apps.notifications.services.NotificationService.notify_document_shared",
            side_effect=RuntimeError("notify"),
        ):
            sl, err = create_share_link(
                req,
                target_type="document",
                document=doc,
                recipient_type="internal",
                recipient_user=u2,
            )
        assert err is None
        assert sl.id

    def test_check_password_not_protected(self, tenant):
        u = User.objects.create_user(
            email="se3@test.com",
            password="TestPass123!",
            first_name="E",
            last_name="F",
        )
        folder = Folder.objects.create(name="Fs2", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="Ds2", folder=folder, created_by=u, owner=u)
        sl = ShareLink.objects.create(
            tenant=tenant,
            target_type="document",
            document=doc,
            shared_by=u,
            recipient_type="external",
            recipient_email="a@b.com",
            password_protected=False,
        )
        from apps.sharing.services import check_share_password

        assert check_share_password(sl, "") is True


@pytest.mark.django_db
class TestMailImapBatchA:
    def test_plain_imap_and_fetch_error(self, tenant):
        acc = MailAccount.objects.create(
            name="A",
            account_type="email",
            email_address="a@test.com",
            imap_host="localhost",
            imap_port=143,
            imap_use_ssl=False,
            imap_username="u",
            imap_password="p",
            smtp_host="localhost",
            smtp_port=587,
            smtp_username="u",
            smtp_password="p",
            tenant=tenant,
        )
        mock_conn = MagicMock()
        mock_conn.uid.side_effect = [("OK", [b"1"]), ("BAD", None)]
        with patch("apps.mail.imap_client.imaplib.IMAP4", return_value=mock_conn):
            n = fetch_new_emails(acc, max_messages=5)
        assert n == 0
        mock_conn.logout.assert_called()

        with patch("apps.mail.imap_client.imaplib.IMAP4", side_effect=OSError("down")):
            n2 = fetch_new_emails(acc)
        assert n2 == 0


@pytest.mark.django_db
class TestDashboardExportBatchA:
    def test_excel_column_width_fallback_and_pdf_empty_headers(self):
        r = ExportService.generate_excel(
            "R",
            ["A", "B", "C"],
            [["1", "2", "3"]],
            column_widths=[12],
        )
        assert r.status_code == 200
        r2 = ExportService.generate_pdf("T", ["Col"], [], orientation="landscape")
        assert r2.status_code == 200
        assert r2["Content-Type"] == "application/pdf"


@pytest.mark.django_db
class TestChatModelsSerializersBatchA:
    def test_chat_room_str_and_membership_serializer_exception(self, admin):
        room = ChatRoom.objects.create(room_type="direct", name="")
        assert "direct" in str(room)
        mem = ChatMembership.objects.create(room=room, user=admin)
        with patch(
            "apps.chat.serializers.UserPresence.objects.filter",
            side_effect=RuntimeError("db"),
        ):
            data = ChatMembershipSerializer(instance=mem).data
        assert data["is_online"] is False

    def test_room_serializer_unread_without_request_user(self, admin):
        room = ChatRoom.objects.create(room_type="group", name="G")
        ChatMembership.objects.create(room=room, user=admin)
        msg = ChatMessage.objects.create(room=room, sender=admin, content="hi")
        ser = ChatRoomSerializer(instance=room, context={"request": None})
        assert ser.data["unread_count"] == 0
        assert ser.data["last_message"]["id"] == str(msg.id)


@pytest.mark.django_db
class TestAuthenticationSerializersBatchA:
    def test_password_mismatch_branches(self):
        from apps.authentication.serializers import (
            ChangePasswordRequiredSerializer,
            PasswordResetConfirmSerializer,
        )

        s = PasswordResetConfirmSerializer(
            data={
                "token": "12345678-1234-5678-1234-567812345678",
                "new_password": "Abcd1234!",
                "new_password_confirm": "Abcd1234?",
            }
        )
        assert s.is_valid() is False
        s2 = ChangePasswordRequiredSerializer(
            data={"new_password": "Abcd1234!", "confirm_password": "Xbcd1234!"}
        )
        assert s2.is_valid() is False


@pytest.mark.django_db
class TestMailSerializersBatchA:
    def test_attachment_url_without_request(self, tenant, admin):
        from apps.mail.models import MailAttachment, MailMessage

        acc = MailAccount.objects.create(
            name="M",
            account_type="email",
            email_address="m@test.com",
            imap_host="h",
            imap_port=993,
            imap_use_ssl=True,
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
            subject="S",
            status="unread",
        )
        att = MailAttachment.objects.create(
            message=mm,
            filename="f.txt",
            content_type="text/plain",
            size=1,
        )
        url = MailAttachmentSerializer(instance=att, context={}).get_url(att)
        assert url is None


@pytest.mark.django_db
class TestContactsModelsBatchA:
    def test_str_display_primary(self, admin):
        c1 = Contact.objects.create(
            contact_type="company",
            company_name="Acme",
            email="a@a.com",
            created_by=admin,
        )
        assert "Acme" in str(c1)
        c2 = Contact.objects.create(
            contact_type="person",
            first_name="Luigi",
            last_name="Rossi",
            email="l@r.com",
            created_by=admin,
        )
        assert "Rossi" in str(c2)
        assert c2.display_name
        c3 = Contact.objects.create(
            contact_type="person",
            first_name="A",
            last_name="B",
            pec="pec@test.com",
            created_by=admin,
        )
        assert c3.primary_email == c3.pec


@pytest.mark.django_db
class TestLicenseMiddlewareBatchA:
    @override_settings(DEBUG=True)
    def test_debug_true_skips_license_check(self):
        SystemLicense.objects.update_or_create(
            pk=1,
            defaults={
                "organization_name": "T",
                "expires_at": date.today() - timedelta(days=1),
            },
        )
        mw = LicenseCheckMiddleware(lambda r: None)
        req = RequestFactory().get("/api/documents/")
        assert mw.process_request(req) is None

    @override_settings(DEBUG=False)
    def test_valid_future_license_allows_request(self):
        SystemLicense.objects.update_or_create(
            pk=1,
            defaults={
                "organization_name": "T",
                "expires_at": date.today() + timedelta(days=30),
            },
        )
        mw = LicenseCheckMiddleware(lambda r: None)
        req = RequestFactory().get("/api/documents/")
        assert mw.process_request(req) is None

    @override_settings(DEBUG=False)
    def test_expired_license_returns_402(self):
        SystemLicense.objects.update_or_create(
            pk=1,
            defaults={
                "organization_name": "T",
                "expires_at": date.today() - timedelta(days=1),
            },
        )
        mw = LicenseCheckMiddleware(lambda r: None)
        req = RequestFactory().get("/api/documents/")
        resp = mw.process_request(req)
        assert resp.status_code == 402
        payload = json.loads(resp.content.decode())
        assert payload["error"] == "license_expired"

    @override_settings(DEBUG=False)
    def test_exempt_path_skips_check(self):
        SystemLicense.objects.update_or_create(
            pk=1,
            defaults={
                "organization_name": "T",
                "expires_at": date.today() - timedelta(days=1),
            },
        )
        mw = LicenseCheckMiddleware(lambda r: None)
        req = RequestFactory().get("/api/auth/login/")
        assert mw.process_request(req) is None


@pytest.mark.django_db
class TestProtocolsHelpersBatchA:
    def test_normalize_direction_and_year_valueerror(self, api_client, admin, tenant):
        from apps.protocols.views import _normalize_protocol_direction_param

        assert _normalize_protocol_direction_param("  IN ") == "in"
        assert _normalize_protocol_direction_param("bad") is None
        ou = OrganizationalUnit.objects.create(name="P", code="P", tenant=tenant)
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
            sender_receiver="X",
            registered_at=timezone.now(),
            registered_by=admin,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=admin,
            tenant=tenant,
        )
        api_client.force_authenticate(user=admin)
        r = api_client.get("/api/protocols/", {"year": "notint"})
        assert r.status_code == 200
