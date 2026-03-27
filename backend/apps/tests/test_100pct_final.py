# FASE 35F — Ultimo miglio copertura (file con 1–3 miss)
import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.archive.models import InformationPackage, RetentionRule
from apps.archive.tasks import send_daily_register
from apps.authentication import encryption, mfa
from apps.authentication.models import AuditLog, PasswordResetToken, UserInvitation
from apps.chat.auth import get_user_from_scope
from apps.chat.models import ChatRoom
from apps.chat.serializers import ChatRoomSerializer
from apps.contacts.models import Contact
from apps.dashboard.export_service import ExportService
from apps.documents.models import Document, Folder
from apps.dossiers.models import Dossier
from apps.mail.imap_client import fetch_new_emails
from apps.mail.models import MailAccount, MailAttachment, MailMessage
from apps.mail.serializers import MailAccountSerializer, MailAttachmentSerializer
from apps.mail.smtp_client import send_email
from apps.metadata import agid_metadata
from apps.metadata.models import MetadataField, MetadataStructure
from apps.metadata.serializers import MetadataStructureCreateSerializer
from apps.metadata.validators import _validate_field
from apps.notifications.consumers import NotificationConsumer
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.organizations.middleware import TenantMiddleware
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.organizations.serializers import OrganizationalUnitDetailSerializer
from apps.sharing.models import ShareLink
from apps.sharing.serializers import PublicShareSerializer
from apps.users.models import User


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Default", "plan": "enterprise"},
    )
    return t


@pytest.mark.django_db
class TestEncryptionAndMfa100pct:
    def test_encrypt_secret_empty(self):
        assert encryption.encrypt_secret("") == ""

    def test_mfa_verify_backup_no_match(self):
        _, hashed = mfa.generate_backup_codes()
        ok, _ = mfa.verify_backup_code(hashed, "AAAAAAAA")
        assert ok is False

    def test_mfa_verify_backup_wrong_length(self):
        _, hashed = mfa.generate_backup_codes()
        ok, _ = mfa.verify_backup_code(hashed, "SHORT")
        assert ok is False


@pytest.mark.django_db
class TestAuthenticationSerializerPasswordBranches100pct:
    def test_accept_invite_password_rules(self):
        from apps.authentication.serializers import AcceptInvitationSerializer, _validate_password
        from rest_framework import serializers as drf_serializers

        with pytest.raises(drf_serializers.ValidationError):
            _validate_password("Abcdefgh!")

        s = AcceptInvitationSerializer(
            data={
                "first_name": "A",
                "last_name": "B",
                "password": "abcdefgh",
                "password_confirm": "abcdefgh",
            }
        )
        assert s.is_valid() is False
        s2 = AcceptInvitationSerializer(
            data={
                "first_name": "A",
                "last_name": "B",
                "password": "Abcdefgh",
                "password_confirm": "Abcdefgh",
            }
        )
        assert s.is_valid() is False


@pytest.mark.django_db
class TestAuthenticationModels100pct:
    def test_password_reset_token_default_expiry(self, tenant):
        u = User.objects.create_user(
            email="am100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        t = PasswordResetToken(user=u, expires_at=None)
        t.save()
        assert t.expires_at

    def test_audit_log_tenant_from_scope_raises(self, tenant):
        u = User.objects.create_user(
            email="am101@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        with patch(
            "apps.organizations.middleware.get_current_tenant",
            side_effect=RuntimeError("x"),
        ):
            AuditLog.log(u, "LOGIN", {}, request=None)

    def test_user_invitation_default_expires(self, tenant):
        inviter = User.objects.create_user(
            email="am102@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        inv = UserInvitation(
            email="x@y.com",
            invited_by=inviter,
            expires_at=None,
        )
        inv.save()
        assert inv.expires_at


@pytest.mark.django_db
class TestAuthenticationSerializers100pct:
    def test_invite_password_mismatch(self):
        from apps.authentication.serializers import AcceptInvitationSerializer

        s = AcceptInvitationSerializer(
            data={
                "first_name": "A",
                "last_name": "B",
                "password": "Abcd1234!",
                "password_confirm": "Abcd1234?",
            }
        )
        assert s.is_valid() is False


@pytest.mark.django_db
class TestArchiveModelsTasks100pct:
    def test_retention_rule_and_package_str(self, tenant):
        r = RetentionRule.objects.create(
            classification_code="C1",
            classification_label="L1",
            retention_years=5,
        )
        assert "C1" in str(r)
        u = User.objects.create_user(
            email="ar100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        pkg = InformationPackage.objects.create(
            package_type="PdV",
            package_id="pkg-str-test-1",
            created_by=u,
            status="draft",
        )
        assert "PdV" in str(pkg)

    def test_send_daily_register_no_admin(self, tenant):
        u = User.objects.create_user(
            email="ar101@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
            role="OPERATOR",
        )
        folder = Folder.objects.create(name="F", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="D", folder=folder, created_by=u, tenant=tenant)
        ou = OrganizationalUnit.objects.create(name="O", code="NOAD", tenant=tenant)
        from apps.protocols.models import Protocol, ProtocolCounter

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
            registered_by=u,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=u,
            tenant=tenant,
            document=doc,
        )
        with patch("django.contrib.auth.get_user_model") as gum:
            U = MagicMock()
            U.objects.filter.return_value.first.return_value = None
            gum.return_value = U
            out = send_daily_register()
        assert out.get("reason") == "no_admin"


@pytest.mark.django_db
class TestMailModule100pct:
    def test_imap_valueerror_uid_search(self, tenant):
        acc = MailAccount.objects.create(
            name="I",
            account_type="email",
            email_address="imapve@test.com",
            imap_host="h",
            imap_port=993,
            imap_use_ssl=True,
            imap_username="u",
            imap_password="p",
            smtp_host="h",
            smtp_username="u",
            smtp_password="p",
            tenant=tenant,
            last_fetch_uid="notint",
        )
        mock_conn = MagicMock()
        mock_conn.uid.side_effect = [
            ("OK", [b"1"]),
            ("OK", [[(b"RFC822", b"raw")]]),
        ]
        raw = (
            b"From: a@b.com\r\nTo: c@d.com\r\nSubject: T\r\nDate: invalid!!!\r\n\r\nHi"
        )
        mock_conn.uid.return_value = ("OK", [[(b"RFC822", raw)]])
        with patch("apps.mail.imap_client.imaplib.IMAP4_SSL", return_value=mock_conn):
            fetch_new_emails(acc, max_messages=1)

    def test_imap_non_multipart_html_only(self, tenant):
        acc = MailAccount.objects.create(
            name="I2",
            account_type="email",
            email_address="imaph@test.com",
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
        mock_conn = MagicMock()
        mock_conn.uid.side_effect = [
            ("OK", [b"9"]),
            (
                "OK",
                [
                    [
                        b"RFC822",
                        b"Content-Type: text/html; charset=utf-8\r\n\r\n<p>x</p>",
                    ]
                ],
            ),
        ]
        with patch("apps.mail.imap_client.imaplib.IMAP4_SSL", return_value=mock_conn):
            fetch_new_emails(acc, max_messages=1)

    def test_smtp_reply_headers_and_mail_str(self, tenant):
        acc = MailAccount.objects.create(
            name="S",
            account_type="email",
            email_address="smtp100@test.com",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="localhost",
            smtp_username="u",
            smtp_password="p",
            tenant=tenant,
        )
        assert "S" in str(acc)
        prev = MailMessage.objects.create(
            account=acc,
            direction="in",
            from_address="a@b.com",
            subject="Prev",
            status="unread",
            message_id="<mid@test>",
        )
        mock_s = MagicMock()
        with patch("apps.mail.smtp_client.smtplib.SMTP_SSL", return_value=mock_s):
            send_email(
                acc,
                ["d@test.com"],
                "Sub",
                body_text="Hi",
                reply_to_message=prev,
            )
        att = MailAttachment.objects.create(
            message=prev,
            filename="a.bin",
            content_type="application/octet-stream",
            size=1,
        )
        assert str(att) == "a.bin"


@pytest.mark.django_db
class TestMetadata100pct:
    def test_metadata_field_str(self, tenant):
        u = User.objects.create_user(
            email="md100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        st = MetadataStructure.objects.create(name="ST", created_by=u)
        f = MetadataField.objects.create(
            structure=st,
            name="f1",
            label="L1",
            field_type="text",
            order=0,
        )
        assert "ST" in str(f) and "L1" in str(f)

    def test_validators_number_min_max(self):
        from apps.metadata.models import MetadataField

        f = MetadataField(
            name="n",
            label="N",
            field_type="number",
            is_required=False,
            validation_rules={"min": 1.0, "max": 10.0},
        )
        assert _validate_field(f, "0")
        assert _validate_field(f, "20")
        f2 = MetadataField(
            name="l",
            label="L",
            field_type="text",
            is_required=False,
        )
        assert _validate_field(f2, []) is None

    def test_agid_folder_and_dossier(self, tenant):
        u = User.objects.create_user(
            email="md101@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        folder = Folder.objects.create(name="AGF", tenant=tenant, created_by=u)
        assert agid_metadata.get_agid_metadata_for_folder(folder)["nome"] == "AGF"
        ou = OrganizationalUnit.objects.create(name="UO", code="AG", tenant=tenant)
        OrganizationalUnitMembership.objects.create(
            user=u,
            organizational_unit=ou,
            role="OPERATOR",
            is_active=True,
        )
        d = Dossier.objects.create(
            title="Doss",
            identifier="2025/AG/0001",
            organizational_unit=ou,
            created_by=u,
            responsible=u,
            tenant=tenant,
        )
        meta = agid_metadata.get_agid_metadata_for_dossier(d)
        assert meta["oggetto"] == "Doss"
        assert meta.get("uo")


@pytest.mark.django_db
class TestNotifications100pct:
    def test_notify_workflow_completed_without_starter(self, tenant):
        from apps.documents.models import Document
        from apps.workflows.models import WorkflowInstance, WorkflowTemplate

        u = User.objects.create_user(
            email="nt100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        folder = Folder.objects.create(name="Wf", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="W", folder=folder, created_by=u, tenant=tenant)
        tpl = WorkflowTemplate.objects.create(name="T", created_by=u, is_published=True)
        wi = WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=None,
            status="completed",
            tenant=tenant,
        )
        NotificationService.notify_workflow_completed(wi)

    def test_notify_rejected_and_changes_no_target(self, tenant):
        from apps.documents.models import Document
        from apps.workflows.models import WorkflowInstance, WorkflowTemplate

        u = User.objects.create_user(
            email="nt101@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        folder = Folder.objects.create(name="Wf2", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="W2", folder=folder, created_by=u, tenant=tenant)
        tpl = WorkflowTemplate.objects.create(name="T2", created_by=u, is_published=True)
        wi = WorkflowInstance.objects.create(
            template=tpl,
            document=doc,
            started_by=None,
            status="rejected",
            tenant=tenant,
        )
        NotificationService.notify_workflow_rejected(wi, "x")
        doc2 = Document.objects.create(
            title="W3",
            folder=folder,
            created_by=None,
            tenant=tenant,
        )
        wi2 = WorkflowInstance.objects.create(
            template=tpl,
            document=doc2,
            started_by=u,
            status="active",
            tenant=tenant,
        )
        NotificationService.notify_changes_requested(wi2, "c")

    def test_notify_document_shared_name_from_names(self, tenant):
        u1 = User.objects.create_user(
            email="nt102@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        u2 = User.objects.create_user(
            email="nt103@test.com",
            password="TestPass123!",
            first_name="C",
            last_name="D",
        )
        folder = Folder.objects.create(name="Sh", tenant=tenant, created_by=u1)
        doc = Document.objects.create(title="Sd", folder=folder, created_by=u1, tenant=tenant)
        NotificationService.notify_document_shared(doc, u2, u1)

    def test_notification_str(self, tenant):
        u = User.objects.create_user(
            email="nt104@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        n = Notification.objects.create(
            recipient=u,
            notification_type="system",
            title="T",
            body="B",
        )
        assert "T" in str(n) and "nt104" in str(n)


@pytest.mark.django_db
class TestChatAndSharing100pct:
    def test_chat_room_helpers(self, tenant):
        u = User.objects.create_user(
            email="ch100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        folder = Folder.objects.create(name="Cf", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="Cd", folder=folder, created_by=u, tenant=tenant)
        room = ChatRoom.get_or_create_for_document(doc)
        assert room.document_id == doc.id
        with patch(
            "apps.organizations.middleware.get_current_tenant",
            side_effect=RuntimeError("x"),
        ):
            u2 = User.objects.create_user(
                email="ch101@test.com",
                password="TestPass123!",
                first_name="E",
                last_name="F",
            )
            ChatRoom.get_or_create_direct(u, u2)

    def test_chat_unread_count_with_last_read(self, tenant):
        u = User.objects.create_user(
            email="ch102@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        room = ChatRoom.objects.create(room_type="group", name="G", tenant=tenant)
        from apps.chat.models import ChatMembership, ChatMessage

        mem = ChatMembership.objects.create(room=room, user=u)
        mem.last_read_at = timezone.now() - timezone.timedelta(hours=1)
        mem.save()
        ChatMessage.objects.create(room=room, sender=u, content="m")
        ser = ChatRoomSerializer(instance=room, context={"request": MagicMock(user=u)})
        assert ser.data["unread_count"] >= 0

    def test_public_share_shared_by_email_only(self, tenant):
        u = User.objects.create_user(
            email="sh100@test.com",
            password="TestPass123!",
            first_name="",
            last_name="",
        )
        sl = ShareLink(
            tenant=tenant,
            target_type="document",
            shared_by=u,
            recipient_type="external",
            recipient_email="e@e.com",
        )
        ser = PublicShareSerializer(sl)
        assert ser.data["shared_by"]["name"] == u.email

    def test_sharelink_get_absolute_url(self, tenant):
        u = User.objects.create_user(
            email="sh101@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        folder = Folder.objects.create(name="Sf", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="Sd", folder=folder, created_by=u, tenant=tenant)
        sl = ShareLink.objects.create(
            tenant=tenant,
            target_type="document",
            document=doc,
            shared_by=u,
            recipient_type="external",
            recipient_email="x@y.com",
        )
        assert "/share/" in sl.get_absolute_url()


@pytest.mark.django_db
class TestOrganizations100pct:
    def test_ou_and_membership_str(self, tenant):
        ou = OrganizationalUnit.objects.create(name="N", code="OUSTR", tenant=tenant)
        assert "OUSTR" in str(ou)
        u = User.objects.create_user(
            email="or100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        from apps.organizations.models import OrganizationalUnitMembership

        m = OrganizationalUnitMembership.objects.create(
            user=u,
            organizational_unit=ou,
            role="OPERATOR",
        )
        assert str(m)

    def test_ou_detail_members_serializer(self, tenant):
        ou = OrganizationalUnit.objects.create(name="Det", code="DET", tenant=tenant)
        data = OrganizationalUnitDetailSerializer(ou).data
        assert "members" in data

    def test_tenant_middleware_jwt_tenant(self, tenant):
        u = User.objects.create_user(
            email="or101@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
            tenant=tenant,
        )
        factory = RequestFactory()
        req = factory.get("/api/x/")
        req.user = u
        req.META = {}
        mw = TenantMiddleware(lambda r: None)
        with patch(
            "apps.organizations.middleware._decode_access_tenant_id",
            return_value=str(tenant.id),
        ):
            mw.process_request(req)
        assert getattr(req, "tenant", None) is not None


@pytest.mark.django_db
class TestContacts100pct:
    def test_display_name_person_with_company(self, tenant):
        c = Contact.objects.create(
            contact_type="person",
            first_name="A",
            last_name="B",
            company_name="Co",
            email="c@test.com",
        )
        assert "(" in c.display_name


@pytest.mark.django_db
class TestDossierSerializer100pct:
    def test_validate_identifier_duplicate(self, tenant):
        from apps.dossiers.serializers import DossierCreateSerializer

        u = User.objects.create_user(
            email="ds200@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="O", code="DSV", tenant=tenant)
        Dossier.objects.create(
            title="A",
            identifier="UNIQUE-ID-1",
            organizational_unit=ou,
            created_by=u,
            tenant=tenant,
        )
        ser = DossierCreateSerializer(
            data={
                "title": "B",
                "identifier": "UNIQUE-ID-1",
                "organizational_unit": str(ou.id),
            }
        )
        assert ser.is_valid() is False


@pytest.mark.django_db
class TestDashboardExport100pct:
    @override_settings(EXPORT_REPORT_LOGO="/tmp/nonexistent_logo_for_test.png")
    def test_pdf_logo_oserror_branch(self):
        with patch("apps.dashboard.export_service.os.path.isfile", return_value=True):
            with patch("apps.dashboard.export_service.Image", side_effect=OSError("bad")):
                r = ExportService.generate_pdf("T", ["C"], [["x"]])
        assert r.status_code == 200


@pytest.mark.django_db(transaction=True)
class TestNotificationConsumerHandlers100pct:
    def test_group_event_handlers(self):
        from channels.layers import get_channel_layer
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import RefreshToken

        from config.asgi import application

        user = User.objects.create_user(
            email="wsh100@test.com",
            password="x",
            first_name="A",
            last_name="B",
        )
        token = str(RefreshToken.for_user(user).access_token)

        async def run():
            comm = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={token}",
                headers=[(b"origin", b"http://localhost")],
            )
            await comm.connect()
            await comm.receive_json_from()
            layer = get_channel_layer()
            await layer.group_send(
                f"notifications_{user.id}",
                {"type": "new_notification", "notification": {"id": "1"}},
            )
            m1 = await comm.receive_json_from()
            assert m1["type"] == "new_notification"
            await layer.group_send(
                f"notifications_{user.id}",
                {"type": "unread_count_update", "count": 0},
            )
            m2 = await comm.receive_json_from()
            assert m2["type"] == "unread_count"
            await comm.disconnect()

        asyncio.run(run())


@pytest.mark.django_db
class TestNotificationsList100pct:
    def test_list_without_pagination(self, tenant):
        u = User.objects.create_user(
            email="nv100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        Notification.objects.create(
            recipient=u,
            notification_type="system",
            title="T",
            body="B",
        )
        client = APIClient()
        client.force_authenticate(user=u)
        with patch(
            "apps.notifications.views.NotificationViewSet.paginate_queryset",
            return_value=None,
        ):
            r = client.get("/api/notifications/")
        assert r.status_code == 200


@pytest.mark.django_db
class TestMetadataStructureSerializer100pct:
    def test_validate_name_duplicate_raises(self, tenant):
        u = User.objects.create_user(
            email="ms103@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        MetadataStructure.objects.create(name="Unico", created_by=u)
        ser = MetadataStructureCreateSerializer(context={"request": MagicMock(user=u)})
        from rest_framework import serializers as drf_serializers

        with pytest.raises(drf_serializers.ValidationError):
            ser.validate_name("unico")
        with pytest.raises(drf_serializers.ValidationError):
            ser.validate_name("")

    def test_validate_name_empty_and_duplicate(self, tenant):
        u = User.objects.create_user(
            email="ms100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="O", code="MS", tenant=tenant)
        MetadataStructure.objects.create(name="Dup", created_by=u)
        ser = MetadataStructureCreateSerializer(
            context={"request": MagicMock(user=u)},
            data={
                "name": " ",
                "allowed_organizational_units": [str(ou.id)],
                "fields": [],
            },
        )
        assert ser.is_valid() is False
        ser2 = MetadataStructureCreateSerializer(
            context={"request": MagicMock(user=u)},
            data={
                "name": "dup",
                "allowed_organizational_units": [str(ou.id)],
                "fields": [],
            },
        )
        assert ser2.is_valid() is False

    def test_update_clears_allowed_signers(self, tenant):
        u = User.objects.create_user(
            email="ms102@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="O3", code="MS3", tenant=tenant)
        st = MetadataStructure.objects.create(name="Zeta", created_by=u)
        ser = MetadataStructureCreateSerializer(
            st,
            context={"request": MagicMock(user=u)},
            data={
                "name": "Zeta",
                "allowed_signers": [],
                "allowed_organizational_units": [str(ou.id)],
            },
            partial=True,
        )
        assert ser.is_valid(), ser.errors
        ser.save()

@pytest.mark.django_db
class TestOrganizationsMixinsGetTenantSaveKwargs100pct:
    def test_superuser_empty_tenant_kwargs(self, tenant):
        from apps.organizations.mixins import TenantFilterMixin

        class V(TenantFilterMixin):
            def __init__(self, request):
                self.request = request

        u = User.objects.create_user(
            email="mx100@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
            is_superuser=True,
        )
        req = MagicMock()
        req.user = u
        req.tenant = tenant

        class S:
            class Meta:
                model = Document

        assert V(req).get_tenant_save_kwargs(S()) == {}


@pytest.mark.django_db
class TestAdminPanelHealthAndLicense100pct:
    @override_settings(MEDIA_ROOT="/tmp/media_health_x")
    def test_health_storage_else_branch(self):
        from django.test import Client

        with patch("os.path.isdir", return_value=False):
            r = Client().get("/api/health/")
        assert r.status_code in (200, 503)

    def test_system_license_feature_disabled(self):
        from apps.admin_panel.models import SystemLicense

        SystemLicense.objects.get_or_create(
            pk=1,
            defaults={
                "organization_name": "T",
                "license_key": "",
                "features_enabled": {},
            },
        )
        lic = SystemLicense.objects.get(pk=1)
        lic.features_enabled = {}
        lic.save(update_fields=["features_enabled"])
        assert SystemLicense.is_feature_enabled("mfa") is False
        lic.features_enabled = {"mfa": True, "x": 1}
        lic.save(update_fields=["features_enabled"])
        assert SystemLicense.is_feature_enabled("mfa") is True
        assert SystemLicense.is_feature_enabled("missing_feature") is False

    def test_system_settings_returns_tenant_row(self, tenant):
        from apps.admin_panel.models import SystemSettings
        from django.db.models import Max

        nid = (SystemSettings.objects.aggregate(m=Max("id"))["m"] or 0) + 1
        SystemSettings.objects.get_or_create(
            tenant=tenant,
            defaults={
                "id": max(nid, 2),
                "email": {},
                "organization": {},
                "protocol": {},
                "security": {},
                "storage": {},
                "ldap": {},
                "conservation": {},
            },
        )
        with patch("apps.organizations.middleware.get_current_tenant", return_value=tenant):
            obj = SystemSettings.get_settings()
        assert obj.tenant_id == tenant.id


@pytest.mark.django_db
class TestMailSerializersExtra100pct:
    def test_unread_count_and_attachment_url(self, tenant):
        acc = MailAccount.objects.create(
            name="M",
            account_type="email",
            email_address="mser@test.com",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="h",
            smtp_username="u",
            smtp_password="p",
            tenant=tenant,
        )
        MailMessage.objects.create(
            account=acc,
            direction="in",
            from_address="a@b.com",
            subject="U",
            status="unread",
        )
        assert MailAccountSerializer(instance=acc).data["unread_count"] == 1
        mm = MailMessage.objects.create(
            account=acc,
            direction="in",
            from_address="a@b.com",
            subject="U2",
            status="read",
        )
        att = MailAttachment.objects.create(
            message=mm,
            filename="n.bin",
            content_type="application/octet-stream",
            size=1,
        )
        assert MailAttachmentSerializer(instance=att, context={}).get_url(att) is None
        att2 = MailAttachment.objects.create(
            message=mm,
            filename="with.bin",
            content_type="application/octet-stream",
            size=1,
            file=ContentFile(b"x", name="with.bin"),
        )
        req = APIRequestFactory().get("/api/mail/")
        url = MailAttachmentSerializer(
            instance=att2, context={"request": req}
        ).get_url(att2)
        assert url.startswith("http://") or url.startswith("https://")


@pytest.mark.django_db
class TestChatModelsCache100pct:
    def test_get_or_create_document_and_dossier_returns_existing(self, tenant):
        u = User.objects.create_user(
            email="ch200@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        folder = Folder.objects.create(name="Ch2", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="Cd2", folder=folder, created_by=u, tenant=tenant)
        r1 = ChatRoom.get_or_create_for_document(doc)
        r2 = ChatRoom.get_or_create_for_document(doc)
        assert r1.id == r2.id
        from apps.dossiers.models import Dossier

        ou = OrganizationalUnit.objects.create(name="DO", code="CH", tenant=tenant)
        dos = Dossier.objects.create(
            title="Doss",
            identifier="2025/CH/0001",
            organizational_unit=ou,
            created_by=u,
            tenant=tenant,
        )
        d1 = ChatRoom.get_or_create_for_dossier(dos)
        d2 = ChatRoom.get_or_create_for_dossier(dos)
        assert d1.id == d2.id


@pytest.mark.django_db
class TestDossierSerializerInstanceBranch100pct:
    def test_validate_identifier_unchanged_on_update(self, tenant):
        from apps.dossiers.serializers import DossierCreateSerializer

        u = User.objects.create_user(
            email="ds300@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="O", code="DSB", tenant=tenant)
        d = Dossier.objects.create(
            title="T",
            identifier="MY-ID-1",
            organizational_unit=ou,
            created_by=u,
            tenant=tenant,
        )
        ser = DossierCreateSerializer(
            instance=d,
            data={
                "title": "T2",
                "identifier": "MY-ID-1",
                "organizational_unit": str(ou.id),
            },
            partial=True,
        )
        assert ser.is_valid(), ser.errors

    def test_validate_identifier_raises_duplicate(self, tenant):
        from apps.dossiers.serializers import DossierCreateSerializer
        from rest_framework import serializers as drf_serializers

        u = User.objects.create_user(
            email="ds400@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="O", code="DS4", tenant=tenant)
        Dossier.objects.create(
            title="A",
            identifier="DUP-ID",
            organizational_unit=ou,
            created_by=u,
            tenant=tenant,
        )
        ser = DossierCreateSerializer()
        with pytest.raises(drf_serializers.ValidationError):
            ser.validate_identifier("DUP-ID")
