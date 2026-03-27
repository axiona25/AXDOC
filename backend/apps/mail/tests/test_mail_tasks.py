"""Task Celery mail: fetch_all_accounts, fetch_single_account."""
import uuid
from unittest.mock import patch

import pytest

from apps.mail.models import MailAccount
from apps.mail.tasks import fetch_all_accounts, fetch_single_account


@pytest.mark.django_db
class TestMailTasks:
    def test_fetch_all_accounts_empty(self):
        assert fetch_all_accounts() == 0

    def test_fetch_all_accounts_counts_and_logs(self):
        acc = MailAccount.objects.create(
            name="A",
            email_address=f"t{uuid.uuid4().hex[:6]}@imap.test",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="s",
            smtp_username="u",
            smtp_password="p",
        )
        with patch("apps.mail.imap_client.fetch_new_emails", return_value=2) as mock_fetch:
            total = fetch_all_accounts()
        assert total == 2
        mock_fetch.assert_called_once_with(acc)

    def test_fetch_all_accounts_skips_inactive(self):
        MailAccount.objects.create(
            name="Off",
            email_address=f"off{uuid.uuid4().hex[:6]}@x.it",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="s",
            smtp_username="u",
            smtp_password="p",
            is_active=False,
        )
        with patch("apps.mail.imap_client.fetch_new_emails") as mock_fetch:
            fetch_all_accounts()
        mock_fetch.assert_not_called()

    def test_fetch_all_accounts_exception_per_account(self):
        MailAccount.objects.create(
            name="E1",
            email_address=f"e1{uuid.uuid4().hex[:6]}@x.it",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="s",
            smtp_username="u",
            smtp_password="p",
        )
        with patch("apps.mail.imap_client.fetch_new_emails", side_effect=RuntimeError("imap down")):
            assert fetch_all_accounts() == 0

    def test_fetch_all_accounts_zero_new_no_extra_print_path(self):
        acc = MailAccount.objects.create(
            name="Z",
            email_address=f"z{uuid.uuid4().hex[:6]}@x.it",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="s",
            smtp_username="u",
            smtp_password="p",
        )
        with patch("apps.mail.imap_client.fetch_new_emails", return_value=0):
            assert fetch_all_accounts() == 0

    def test_fetch_single_account_returns_count(self):
        acc = MailAccount.objects.create(
            name="S",
            email_address=f"s{uuid.uuid4().hex[:6]}@x.it",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="s",
            smtp_username="u",
            smtp_password="p",
        )
        with patch("apps.mail.imap_client.fetch_new_emails", return_value=5) as mock_fetch:
            n = fetch_single_account(str(acc.id))
        assert n == 5
        mock_fetch.assert_called_once_with(acc)

    def test_fetch_single_account_missing_returns_zero(self):
        assert fetch_single_account(str(uuid.uuid4())) == 0

    def test_fetch_single_account_inactive_returns_zero(self):
        acc = MailAccount.objects.create(
            name="I",
            email_address=f"i{uuid.uuid4().hex[:6]}@x.it",
            imap_host="h",
            imap_username="u",
            imap_password="p",
            smtp_host="s",
            smtp_username="u",
            smtp_password="p",
            is_active=False,
        )
        with patch("apps.mail.imap_client.fetch_new_emails") as mock_fetch:
            assert fetch_single_account(str(acc.id)) == 0
        mock_fetch.assert_not_called()
