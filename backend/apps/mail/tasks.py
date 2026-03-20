"""
Task Celery per il polling IMAP periodico.
"""
from celery import shared_task


@shared_task(name="apps.mail.tasks.fetch_all_accounts")
def fetch_all_accounts():
    """Scarica nuove email da tutti gli account attivi."""
    from .imap_client import fetch_new_emails
    from .models import MailAccount

    accounts = MailAccount.objects.filter(is_active=True)
    total = 0
    for account in accounts:
        try:
            count = fetch_new_emails(account)
            total += count
            if count > 0:
                print(f"[MAIL] {account.email_address}: {count} nuove email")
        except Exception as e:
            print(f"[MAIL] Errore {account.email_address}: {e}")
    return total


@shared_task(name="apps.mail.tasks.fetch_single_account")
def fetch_single_account(account_id: str):
    """Scarica nuove email da un singolo account (trigger manuale)."""
    from .imap_client import fetch_new_emails
    from .models import MailAccount

    try:
        account = MailAccount.objects.get(pk=account_id, is_active=True)
        return fetch_new_emails(account)
    except MailAccount.DoesNotExist:
        return 0
