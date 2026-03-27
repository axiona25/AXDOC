# FASE 35.3 — Copertura mail/views.py (test connessione, filtri messaggi, invio edge case)
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import BOUNDARY, encode_multipart
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.mail.views import MailMessageViewSet

from apps.mail.models import MailAccount, MailMessage
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.protocols.models import Protocol

User = get_user_model()


@pytest.fixture
def admin(db):
    return User.objects.create_user(email="m353-adm@test.com", password="Test123!", role="ADMIN")


@pytest.fixture
def operator(db):
    u = User.objects.create_user(email="m353-op@test.com", password="Test123!", role="OPERATOR")
    return u


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="OU-M353", code="M353")


@pytest.fixture
def admin_client(admin):
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


@pytest.fixture
def operator_client(operator, ou):
    OrganizationalUnitMembership.objects.create(user=operator, organizational_unit=ou, role="OPERATOR")
    c = APIClient()
    c.force_authenticate(user=operator)
    return c


@pytest.fixture
def mail_account_ssl(db, admin):
    return MailAccount.objects.create(
        name="SSL",
        email_address="ssl@test.com",
        imap_host="imap.example.com",
        imap_port=993,
        imap_use_ssl=True,
        imap_username="u",
        imap_password="p",
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_use_ssl=True,
        smtp_use_tls=False,
        smtp_username="u",
        smtp_password="p",
        created_by=admin,
    )


@pytest.fixture
def mail_account_plain(db, admin):
    return MailAccount.objects.create(
        name="Plain",
        email_address="plain@test.com",
        imap_host="imap.example.com",
        imap_port=143,
        imap_use_ssl=False,
        imap_username="u",
        imap_password="p",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_use_ssl=False,
        smtp_use_tls=True,
        smtp_username="u",
        smtp_password="p",
        created_by=admin,
    )


@pytest.mark.django_db
class TestMailAccountCreate:
    def test_create_sets_created_by(self, admin_client, admin):
        addr = f"acc-{uuid.uuid4().hex[:10]}@example.com"
        r = admin_client.post(
            "/api/mail/accounts/",
            {
                "name": "Nuovo",
                "account_type": "email",
                "email_address": addr,
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "imap_use_ssl": True,
                "imap_username": "u",
                "imap_password": "p",
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_use_ssl": True,
                "smtp_use_tls": False,
                "smtp_username": "u",
                "smtp_password": "p",
            },
            format="json",
        )
        assert r.status_code == 201
        assert MailAccount.objects.filter(email_address=addr, created_by=admin).exists()


@pytest.mark.django_db
class TestMailAccountTestConnection:
    @patch("apps.mail.views.smtplib.SMTP_SSL")
    @patch("apps.mail.views.imaplib.IMAP4_SSL")
    def test_connection_success_ssl(self, mock_imap_cls, mock_smtp_cls, admin_client, mail_account_ssl):
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        r = admin_client.post(f"/api/mail/accounts/{mail_account_ssl.id}/test_connection/")
        assert r.status_code == 200
        data = r.json()
        assert data["imap"] is True
        assert data["smtp"] is True
        mock_imap.login.assert_called_once()
        mock_imap.logout.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch("apps.mail.views.smtplib.SMTP")
    @patch("apps.mail.views.imaplib.IMAP4")
    def test_connection_plain_smtp_starttls(self, mock_imap_cls, mock_smtp_cls, admin_client, mail_account_plain):
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        r = admin_client.post(f"/api/mail/accounts/{mail_account_plain.id}/test_connection/")
        assert r.status_code == 200
        assert r.json()["imap"] is True
        assert r.json()["smtp"] is True
        mock_smtp.starttls.assert_called_once()

    @patch("apps.mail.views.smtplib.SMTP_SSL")
    @patch("apps.mail.views.imaplib.IMAP4_SSL")
    def test_connection_imap_error_surfaces(self, mock_imap_cls, mock_smtp_cls, admin_client, mail_account_ssl):
        mock_imap_cls.side_effect = OSError("imap down")
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        r = admin_client.post(f"/api/mail/accounts/{mail_account_ssl.id}/test_connection/")
        assert r.status_code == 200
        assert r.json()["imap"] is False
        assert "imap down" in r.json()["imap_error"]

    @patch("apps.mail.views.smtplib.SMTP_SSL")
    @patch("apps.mail.views.imaplib.IMAP4_SSL")
    def test_connection_smtp_error_surfaces(self, mock_imap_cls, mock_smtp_cls, admin_client, mail_account_ssl):
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_smtp_cls.side_effect = OSError("smtp down")
        r = admin_client.post(f"/api/mail/accounts/{mail_account_ssl.id}/test_connection/")
        assert r.status_code == 200
        assert r.json()["imap"] is True
        assert r.json()["smtp"] is False
        assert "smtp down" in r.json()["smtp_error"]


@pytest.mark.django_db
class TestMailMessageViewSetBranches:
    def test_create_returns_405(self, admin_client):
        r = admin_client.post("/api/mail/messages/", {}, format="json")
        assert r.status_code == 405

    def test_non_admin_filters_by_protocol_ou(self, operator_client, mail_account_ssl, admin, operator, ou):
        ou2 = OrganizationalUnit.objects.create(name="OU2-M353", code="M353B")
        p1 = Protocol.objects.create(
            protocol_id="2026/M353/0001",
            subject="S1",
            direction="in",
            status="active",
            created_by=admin,
            organizational_unit=ou,
        )
        p2 = Protocol.objects.create(
            protocol_id="2026/M353/0002",
            subject="S2",
            direction="in",
            status="active",
            created_by=admin,
            organizational_unit=ou2,
        )
        m_ok = MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="a@b.c",
            subject="X",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
            protocol=p1,
        )
        MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="a@b.c",
            subject="Hidden",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
            protocol=p2,
        )
        MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="a@b.c",
            subject="NoProto",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
            protocol=None,
        )
        r = operator_client.get("/api/mail/messages/")
        assert r.status_code == 200
        rows = r.json().get("results", r.json())
        ids = {str(x["id"]) for x in rows}
        assert str(m_ok.id) in ids

    def test_list_query_params_and_retrieve_marks_read(self, admin_client, admin, mail_account_ssl, ou):
        msg = MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="from@x.com",
            from_name="From Name",
            subject="SubStatus",
            status="unread",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        proto = Protocol.objects.create(
            protocol_id="2026/M353/F",
            subject="F",
            direction="in",
            status="active",
            created_by=admin,
            organizational_unit=ou,
        )
        msg.protocol = proto
        msg.save(update_fields=["protocol"])
        r = admin_client.get(
            "/api/mail/messages/",
            {
                "account": str(mail_account_ssl.id),
                "folder": "INBOX",
                "direction": "in",
                "status": "unread",
                "search": "SubStatus",
                "protocol": str(proto.id),
            },
        )
        assert r.status_code == 200
        r2 = admin_client.get(f"/api/mail/messages/{msg.id}/")
        assert r2.status_code == 200
        msg.refresh_from_db()
        assert msg.status == "read"

    @patch("apps.mail.views.send_email")
    def test_send_invalid_account(self, mock_send, admin_client):
        r = admin_client.post(
            "/api/mail/messages/send/",
            {
                "account_id": "00000000-0000-0000-0000-000000000001",
                "to": ["z@z.z"],
                "subject": "S",
            },
            format="json",
        )
        assert r.status_code == 400
        mock_send.assert_not_called()

    @patch("apps.mail.views.send_email")
    def test_send_with_reply_and_protocol_json(self, mock_send, admin_client, mail_account_ssl, admin, ou):
        prev = MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="old@test.com",
            subject="Old",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        proto = Protocol.objects.create(
            protocol_id="2026/M353/P1",
            subject="P",
            direction="out",
            status="active",
            created_by=admin,
            organizational_unit=ou,
        )

        def _mk(**kwargs):
            return MailMessage.objects.create(
                account=kwargs["account"],
                direction="out",
                from_address=kwargs["account"].email_address,
                subject=kwargs["subject"],
                body_text=kwargs.get("body_text") or "",
                status="read",
                folder="SENT",
                sent_at=timezone.now(),
            )

        mock_send.side_effect = _mk
        r = admin_client.post(
            "/api/mail/messages/send/",
            {
                "account_id": str(mail_account_ssl.id),
                "to": ["to@test.com"],
                "subject": "Re",
                "reply_to_message_id": str(prev.id),
                "protocol_id": str(proto.id),
            },
            format="json",
        )
        assert r.status_code == 201
        call_kw = mock_send.call_args.kwargs
        assert call_kw["reply_to_message"] is not None

    @patch("apps.mail.views.send_email")
    def test_send_inactive_account_returns_400(self, mock_send, admin_client, admin):
        inactive = MailAccount.objects.create(
            name="Off",
            email_address="inactive353@example.com",
            imap_host="i",
            imap_port=993,
            imap_use_ssl=True,
            imap_username="u",
            imap_password="p",
            smtp_host="s",
            smtp_port=465,
            smtp_use_ssl=True,
            smtp_use_tls=False,
            smtp_username="u",
            smtp_password="p",
            created_by=admin,
            is_active=False,
        )
        r = admin_client.post(
            "/api/mail/messages/send/",
            {"account_id": str(inactive.id), "to": ["a@example.com"], "subject": "S"},
            format="json",
        )
        assert r.status_code == 400
        mock_send.assert_not_called()

    @patch("apps.mail.views.send_email", side_effect=RuntimeError("smtp fail"))
    def test_send_internal_error(self, mock_send, admin_client, mail_account_ssl):
        r = admin_client.post(
            "/api/mail/messages/send/",
            {"account_id": str(mail_account_ssl.id), "to": ["user@example.com"], "subject": "E"},
            format="json",
        )
        assert r.status_code == 500
        assert "smtp fail" in r.json()["detail"]

    @patch("apps.mail.views.send_email")
    def test_send_multipart_includes_uploaded_files_as_attachments(self, mock_send, admin, mail_account_ssl):
        def _mk(**kwargs):
            atts = kwargs.get("attachments") or []
            assert len(atts) == 1
            assert atts[0]["filename"] == "a.txt"
            assert atts[0]["data"] == b"payload-bytes"
            return MailMessage.objects.create(
                account=kwargs["account"],
                direction="out",
                from_address=kwargs["account"].email_address,
                subject=kwargs["subject"],
                body_text=kwargs.get("body_text") or "",
                status="read",
                folder="SENT",
                sent_at=timezone.now(),
            )

        mock_send.side_effect = _mk
        f = SimpleUploadedFile("a.txt", b"payload-bytes", content_type="text/plain")
        body = encode_multipart(
            BOUNDARY,
            {
                "account_id": str(mail_account_ssl.id),
                "subject": "Multipart subj",
                "to": "dest@example.com",
                "f1": f,
            },
        )
        django_request = APIRequestFactory().post(
            "/api/mail/messages/send/",
            data=body,
            content_type=f"multipart/form-data; boundary={BOUNDARY}",
        )
        force_authenticate(django_request, user=admin)
        response = MailMessageViewSet.as_view({"post": "send_message"})(django_request)
        assert response.status_code == 201
        mock_send.assert_called_once()


@pytest.mark.django_db
class TestLinkProtocolBranches:
    def test_link_empty_and_by_protocol_id_string(self, admin_client, mail_account_ssl, admin, ou):
        proto = Protocol.objects.create(
            protocol_id="2026/M353/LINK",
            protocol_number="PN-M353-1",
            subject="L",
            direction="in",
            status="active",
            created_by=admin,
            organizational_unit=ou,
        )
        msg = MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="x@y.z",
            subject="L",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        r0 = admin_client.post(f"/api/mail/messages/{msg.id}/link_protocol/", {}, format="json")
        assert r0.status_code == 400

        r1 = admin_client.post(
            f"/api/mail/messages/{msg.id}/link_protocol/",
            {"protocol_id": "2026/M353/LINK"},
            format="json",
        )
        assert r1.status_code == 200
        msg.refresh_from_db()
        assert msg.protocol_id == proto.id

        msg2 = MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="x@y.z",
            subject="L2",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        r2 = admin_client.post(
            f"/api/mail/messages/{msg2.id}/link_protocol/",
            {"protocol_id": "PN-M353-1"},
            format="json",
        )
        assert r2.status_code == 200

    def test_unlink_protocol(self, admin_client, mail_account_ssl, admin, ou):
        proto = Protocol.objects.create(
            protocol_id="2026/M353/UL",
            subject="U",
            direction="in",
            status="active",
            created_by=admin,
            organizational_unit=ou,
        )
        msg = MailMessage.objects.create(
            account=mail_account_ssl,
            direction="in",
            from_address="x@y.z",
            subject="U",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
            protocol=proto,
        )
        r = admin_client.post(f"/api/mail/messages/{msg.id}/unlink_protocol/")
        assert r.status_code == 200
        msg.refresh_from_db()
        assert msg.protocol_id is None
