"""Cifra retroattivamente i campi sensibili dei contatti (plaintext → Fernet)."""
from django.core.management.base import BaseCommand
from django.db import connection

from apps.contacts.models import Contact


def _pk_param(contact) -> str:
    if connection.vendor == "mysql":
        return str(contact.pk).replace("-", "").lower()
    return str(contact.pk)


def _is_fernet_token(s: str) -> bool:
    return isinstance(s, str) and s.startswith("gAAAAA")


class Command(BaseCommand):
    help = "Cifra i dati sensibili dei contatti ancora salvati in chiaro nel DB."

    def handle(self, *args, **options):
        table = Contact._meta.db_table
        fields = ["email", "phone", "pec", "mobile", "tax_code"]
        count = 0

        for contact in Contact.objects.all():
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT {', '.join(fields)} FROM {table} WHERE id = %s",
                    [_pk_param(contact)],
                )
                row = cursor.fetchone()
            if not row:
                continue
            needs_save = False
            for raw in row:
                if raw and isinstance(raw, str) and not _is_fernet_token(raw):
                    needs_save = True
                    break
            if needs_save:
                contact.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Contatti aggiornati (cifratura): {count}"))
