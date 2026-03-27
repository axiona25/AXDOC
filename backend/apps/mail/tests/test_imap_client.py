"""Test IMAP fetch con mock imaplib (FASE 33D)."""
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from unittest.mock import MagicMock, patch

import pytest

from apps.mail.imap_client import _decode_header_value, _parse_addresses, fetch_new_emails
from apps.mail.models import MailAccount, MailMessage


def _raw_simple_plain() -> bytes:
    return (
        b"From: Alice <alice@test.com>\r\n"
        b"To: Bob <bob@test.com>\r\n"
        b"Cc: cc@example.com\r\n"
        b"Subject: =?UTF-8?B?U3ViamVjdA==?=\r\n"
        b"Message-ID: <msg-1@test>\r\n"
        b"In-Reply-To: <parent@test>\r\n"
        b"Date: Mon, 01 Jan 2025 10:00:00 +0000\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Hello body\r\n"
    )


def _raw_multipart_attachment() -> bytes:
    msg = MIMEMultipart()
    msg["From"] = "Sender <s@test.com>"
    msg["To"] = "r@test.com"
    msg["Subject"] = "With file"
    msg.attach(MIMEText("plain part", "plain", "utf-8"))
    part = MIMEBase("application", "octet-stream")
    part.set_payload(b"attachment-bytes")
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename="doc.bin")
    msg.attach(part)
    return msg.as_bytes()


@pytest.fixture
def mail_account(db):
    return MailAccount.objects.create(
        name="Test IMAP",
        email_address="imap-acc-test@example.com",
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
    )


def _make_conn_mock(raw_email: bytes):
    conn = MagicMock()
    conn.login.return_value = ("OK", [b"logged in"])
    conn.select.return_value = ("OK", [b"1"])

    def uid_side_effect(cmd, *args):
        if cmd.upper() == "SEARCH":
            return ("OK", [b"42"])
        if cmd.upper() == "FETCH":
            return ("OK", [(b"42 (RFC822 {100}", raw_email), b")"])
        return ("BAD", [b""])

    conn.uid.side_effect = uid_side_effect
    conn.logout.return_value = ("BYE", [b"bye"])
    return conn


@pytest.mark.django_db
class TestIMAPHelpers:
    def test_decode_header_value_empty(self):
        assert _decode_header_value("") == ""

    def test_decode_header_value_mime_encoded(self):
        s = _decode_header_value("=?UTF-8?B?VGVzdA==?=")
        assert "Test" in s or s == "Test"

    def test_parse_addresses_empty(self):
        assert _parse_addresses("") == []

    def test_parse_addresses_two(self):
        addrs = _parse_addresses("A <a@x.com>, b@y.com")
        emails = {a["email"] for a in addrs}
        assert emails == {"a@x.com", "b@y.com"}


@pytest.mark.django_db
class TestFetchNewEmails:
    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_fetch_ssl_creates_message(self, mock_ssl, mail_account, db):
        conn = _make_conn_mock(_raw_simple_plain())
        mock_ssl.return_value = conn
        n = fetch_new_emails(mail_account, max_messages=50)
        assert n == 1
        assert MailMessage.objects.filter(account=mail_account, imap_uid="42").exists()
        mm = MailMessage.objects.get(account=mail_account, imap_uid="42")
        assert mm.subject
        assert mm.from_address
        assert len(mm.to_addresses) >= 1
        conn.login.assert_called_once()
        conn.logout.assert_called_once()

    @patch("apps.mail.imap_client.imaplib.IMAP4")
    def test_fetch_non_ssl(self, mock_imap4, mail_account):
        mail_account.imap_use_ssl = False
        mail_account.save(update_fields=["imap_use_ssl"])
        conn = _make_conn_mock(_raw_simple_plain())
        mock_imap4.return_value = conn
        assert fetch_new_emails(mail_account) == 1

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_search_not_ok_returns_zero(self, mock_ssl, mail_account):
        conn = MagicMock()
        conn.login.return_value = ("OK", [])
        conn.select.return_value = ("OK", [])
        conn.uid.return_value = ("NO", [b""])
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 0

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_empty_uid_list(self, mock_ssl, mail_account):
        conn = MagicMock()
        conn.login.return_value = ("OK", [])
        conn.select.return_value = ("OK", [])

        def uid(cmd, *args):
            if cmd.upper() == "SEARCH":
                return ("OK", [b""])
            return ("BAD", [])

        conn.uid.side_effect = uid
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 0

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_search_ok_but_no_uids_after_split(self, mock_ssl, mail_account):
        """data[0] truthy ma split() vuoto → early return dopo il loop SEARCH."""
        conn = MagicMock()
        conn.login.return_value = ("OK", [])
        conn.select.return_value = ("OK", [])

        def uid(cmd, *args):
            if cmd.upper() == "SEARCH":
                return ("OK", [b"  "])
            return ("BAD", [])

        conn.uid.side_effect = uid
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 0

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_uid_range_search_when_last_fetch_numeric(self, mock_ssl, mail_account):
        mail_account.last_fetch_uid = "5"
        mail_account.save(update_fields=["last_fetch_uid"])
        conn = MagicMock()
        conn.login.return_value = ("OK", [])
        conn.select.return_value = ("OK", [])
        raw = _raw_simple_plain()

        def uid(cmd, *args):
            if cmd.upper() == "SEARCH":
                return ("OK", [b"6"])
            if cmd.upper() == "FETCH":
                return ("OK", [(b"6 (RFC822 {100}", raw), b")"])
            return ("BAD", [])

        conn.uid.side_effect = uid
        conn.logout.return_value = ("BYE", [])
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account, max_messages=50) == 1

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_naive_date_header_triggers_make_aware(self, mock_ssl, mail_account):
        raw = (
            b"From: a@test.com\r\n"
            b"To: b@test.com\r\n"
            b"Subject: Naive date\r\n"
            b"Date: Mon, 01 Jan 2025 10:00:00\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"Hi\r\n"
        )
        conn = _make_conn_mock(raw)
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 1

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_last_fetch_uid_invalid_falls_back_all(self, mock_ssl, mail_account):
        mail_account.last_fetch_uid = "not-a-number"
        mail_account.save(update_fields=["last_fetch_uid"])
        conn = _make_conn_mock(_raw_simple_plain())
        calls = []

        def uid(cmd, *args):
            calls.append((cmd, args))
            if cmd.upper() == "SEARCH":
                return ("OK", [b"99"])
            if cmd.upper() == "FETCH":
                return ("OK", [(b"99 (RFC822 {10}", _raw_simple_plain()), b")"])
            return ("BAD", [])

        conn.uid.side_effect = uid
        conn.login.return_value = ("OK", [])
        conn.select.return_value = ("OK", [])
        mock_ssl.return_value = conn
        fetch_new_emails(mail_account)
        search_calls = [c for c in calls if c[0].upper() == "SEARCH"]
        assert search_calls
        assert any("ALL" in str(c) for c in search_calls)

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_skip_existing_imap_uid(self, mock_ssl, mail_account):
        MailMessage.objects.create(
            account=mail_account,
            direction="in",
            from_address="x@y.z",
            subject="old",
            body_text="",
            body_html="",
            status="unread",
            folder="INBOX",
            imap_uid="42",
        )
        conn = _make_conn_mock(_raw_simple_plain())
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 0

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_multipart_with_attachment(self, mock_ssl, mail_account):
        conn = _make_conn_mock(_raw_multipart_attachment())
        mock_ssl.return_value = conn
        n = fetch_new_emails(mail_account)
        assert n == 1
        mm = MailMessage.objects.get(account=mail_account, imap_uid="42")
        assert mm.has_attachments is True
        assert mm.attachments.count() == 1

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_fetch_returns_zero_on_exception(self, mock_ssl, mail_account):
        mock_ssl.side_effect = OSError("network down")
        with patch("builtins.print"):
            assert fetch_new_emails(mail_account) == 0

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_multipart_html_body(self, mock_ssl, mail_account):
        raw = (
            b"From: h@h.com\r\n"
            b"To: t@t.com\r\n"
            b"Subject: HTML only\r\n"
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/alternative; boundary="b"\r\n'
            b"\r\n"
            b"--b\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"\r\n"
            b"<p>Hi</p>\r\n"
            b"--b--\r\n"
        )
        conn = _make_conn_mock(raw)
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 1
        mm = MailMessage.objects.get(account=mail_account)
        assert "<p>" in (mm.body_html or "")

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_malformed_date_header_uses_now(self, mock_ssl, mail_account):
        raw = (
            b"From: a@test.com\r\n"
            b"To: b@test.com\r\n"
            b"Subject: Bad date\r\n"
            b"Date: not-a-valid-date\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"Hi\r\n"
        )
        conn = _make_conn_mock(raw)
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 1

    @patch("apps.mail.imap_client.imaplib.IMAP4_SSL")
    def test_fetch_uid_returns_bad_skips_message(self, mock_ssl, mail_account):
        conn = MagicMock()
        conn.login.return_value = ("OK", [])
        conn.select.return_value = ("OK", [])

        def uid(cmd, *args):
            if cmd.upper() == "SEARCH":
                return ("OK", [b"1"])
            return ("NO", [b"fail"])

        conn.uid.side_effect = uid
        mock_ssl.return_value = conn
        assert fetch_new_emails(mail_account) == 0
