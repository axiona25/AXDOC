"""Test estesi API mail (FASE 33B)."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.mail.models import MailAccount, MailMessage
from apps.organizations.models import OrganizationalUnit
from apps.protocols.models import Protocol

User = get_user_model()


@pytest.fixture
def admin_client(db):
    u = User.objects.create_user(email="mve-admin@test.com", password="Test123!", role="ADMIN")
    c = APIClient()
    c.force_authenticate(user=u)
    return c, u


@pytest.fixture
def mail_account(db, admin_client):
    _, user = admin_client
    return MailAccount.objects.create(
        name="Acc",
        email_address="acc@test.com",
        imap_host="imap.test.com",
        imap_port=993,
        imap_use_ssl=True,
        imap_username="u",
        imap_password="p",
        smtp_host="smtp.test.com",
        smtp_port=465,
        smtp_use_ssl=True,
        smtp_use_tls=False,
        smtp_username="u",
        smtp_password="p",
        created_by=user,
    )


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="OU-M", code="OUM")


@pytest.fixture
def protocol(db, admin_client, ou):
    _, user = admin_client
    return Protocol.objects.create(
        protocol_id="2025/M/0001",
        subject="S",
        direction="out",
        status="active",
        created_by=user,
        organizational_unit=ou,
    )


@pytest.mark.django_db
class TestMailMessageActions:
    def test_mark_read_unread_toggle_star(self, admin_client, mail_account):
        client, _ = admin_client
        msg = MailMessage.objects.create(
            account=mail_account,
            direction="in",
            from_address="ext@test.com",
            subject="Subj",
            status="unread",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        r = client.post(f"/api/mail/messages/{msg.id}/mark_read/")
        assert r.status_code == 200
        msg.refresh_from_db()
        assert msg.status == "read"

        r2 = client.post(f"/api/mail/messages/{msg.id}/mark_unread/")
        assert r2.status_code == 200
        msg.refresh_from_db()
        assert msg.status == "unread"

        r3 = client.post(f"/api/mail/messages/{msg.id}/toggle_star/")
        assert r3.status_code == 200
        assert r3.json()["is_starred"] is True

    def test_list_filter_folder_and_direction(self, admin_client, mail_account):
        client, _ = admin_client
        MailMessage.objects.create(
            account=mail_account,
            direction="out",
            from_address="acc@test.com",
            subject="Out",
            status="read",
            folder="SENT",
            sent_at=timezone.now(),
        )
        r = client.get("/api/mail/messages/", {"folder": "SENT", "direction": "out"})
        assert r.status_code == 200
        data = r.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        assert len(results) >= 1

    def test_search_subject(self, admin_client, mail_account):
        client, _ = admin_client
        MailMessage.objects.create(
            account=mail_account,
            direction="in",
            from_address="a@b.c",
            subject="UniqueXYZSubject",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        r = client.get("/api/mail/messages/", {"search": "UniqueXYZ"})
        assert r.status_code == 200

    @patch("apps.mail.views.send_email")
    def test_send_message_uses_smtp_client(self, mock_send, admin_client, mail_account):
        client, _ = admin_client

        def _fake_send(**kwargs):
            return MailMessage.objects.create(
                account=kwargs["account"],
                direction="out",
                from_address=kwargs["account"].email_address,
                from_name=kwargs["account"].name,
                to_addresses=[{"email": e, "name": ""} for e in kwargs["to_addresses"]],
                cc_addresses=[{"email": e, "name": ""} for e in (kwargs.get("cc_addresses") or [])],
                bcc_addresses=[{"email": e, "name": ""} for e in (kwargs.get("bcc_addresses") or [])],
                subject=kwargs["subject"],
                body_text=kwargs.get("body_text") or "",
                body_html=kwargs.get("body_html") or "",
                status="read",
                folder="SENT",
                sent_at=timezone.now(),
            )

        mock_send.side_effect = _fake_send

        r = client.post(
            "/api/mail/messages/send/",
            {
                "account_id": str(mail_account.id),
                "to": ["dest@test.com"],
                "subject": "Hello",
                "body_text": "Body",
            },
            format="json",
        )
        assert r.status_code == 201
        mock_send.assert_called_once()

    @patch("apps.mail.views.fetch_new_emails", return_value=3)
    def test_fetch_now(self, mock_fetch, admin_client, mail_account):
        client, _ = admin_client
        r = client.post(f"/api/mail/accounts/{mail_account.id}/fetch_now/")
        assert r.status_code == 200
        assert r.json()["fetched"] == 3

    def test_link_protocol(self, admin_client, mail_account, protocol):
        client, _ = admin_client
        msg = MailMessage.objects.create(
            account=mail_account,
            direction="in",
            from_address="x@y.z",
            subject="L",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        r = client.post(
            f"/api/mail/messages/{msg.id}/link_protocol/",
            {"protocol_id": str(protocol.id)},
            format="json",
        )
        assert r.status_code == 200
        msg.refresh_from_db()
        assert msg.protocol_id == protocol.id

    def test_link_protocol_not_found(self, admin_client, mail_account):
        client, _ = admin_client
        msg = MailMessage.objects.create(
            account=mail_account,
            direction="in",
            from_address="x@y.z",
            subject="L",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        r = client.post(
            f"/api/mail/messages/{msg.id}/link_protocol/",
            {"protocol_id": "99999999-9999-9999-9999-999999999999"},
            format="json",
        )
        assert r.status_code == 400
