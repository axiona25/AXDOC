"""Test client SMTP (FASE 33B)."""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from apps.mail.models import MailAccount
from apps.mail.smtp_client import send_email

User = get_user_model()


@pytest.fixture
def smtp_account(db):
    u = User.objects.create_user(email="smtp-owner@test.com", password="x", role="ADMIN")
    return MailAccount.objects.create(
        name="SMTP Test",
        email_address="from@test.com",
        imap_host="i",
        imap_port=993,
        imap_use_ssl=True,
        imap_username="i",
        imap_password="p",
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_use_ssl=True,
        smtp_use_tls=False,
        smtp_username="su",
        smtp_password="sp",
        created_by=u,
    )


@pytest.mark.django_db
class TestSendEmail:
    @patch("apps.mail.smtp_client.smtplib.SMTP_SSL")
    def test_send_ssl(self, mock_ssl, smtp_account):
        instance = MagicMock()
        mock_ssl.return_value = instance
        msg = send_email(
            smtp_account,
            to_addresses=["to@test.com"],
            subject="Sub",
            body_text="Hello",
        )
        instance.login.assert_called_once()
        instance.sendmail.assert_called_once()
        instance.quit.assert_called_once()
        assert msg.folder == "SENT"
        assert msg.direction == "out"

    @patch("apps.mail.smtp_client.smtplib.SMTP")
    def test_send_tls(self, mock_smtp, smtp_account):
        smtp_account.smtp_use_ssl = False
        smtp_account.smtp_use_tls = True
        smtp_account.save(update_fields=["smtp_use_ssl", "smtp_use_tls"])
        instance = MagicMock()
        mock_smtp.return_value = instance
        send_email(smtp_account, to_addresses=["a@b.c"], subject="S", body_text="T")
        instance.starttls.assert_called_once()
        instance.login.assert_called_once()
        instance.sendmail.assert_called_once()

    @patch("apps.mail.smtp_client.smtplib.SMTP_SSL")
    def test_send_html_and_attachment(self, mock_ssl, smtp_account):
        instance = MagicMock()
        mock_ssl.return_value = instance
        send_email(
            smtp_account,
            to_addresses=["t@test.com"],
            subject="S",
            body_text="Plain",
            body_html="<p>Hi</p>",
            cc_addresses=["cc@test.com"],
            bcc_addresses=["bcc@test.com"],
            attachments=[{"filename": "a.bin", "content_type": "application/octet-stream", "data": b"xyz"}],
        )
        instance.sendmail.assert_called_once()
