"""Test cifratura campi contatti (FASE 32)."""
from django.db import connection
from django.test import TestCase

from apps.contacts.models import Contact


def _pk_for_raw_sql(contact):
    """Adatta la PK al formato nativo del backend (MySQL UUID senza trattini)."""
    if connection.vendor == "mysql":
        return str(contact.pk).replace("-", "").lower()
    return str(contact.pk)


class ContactEncryptionTests(TestCase):
    def test_contact_email_encrypted_in_db(self):
        c = Contact.objects.create(
            email="plain@example.com",
            last_name="L",
            first_name="F",
            contact_type="person",
        )
        table = Contact._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT email FROM `{table}` WHERE id = %s",
                [_pk_for_raw_sql(c)],
            )
            row = cursor.fetchone()
        self.assertIsNotNone(row)
        raw = row[0]
        self.assertNotEqual(raw, "plain@example.com")
        self.assertTrue(str(raw).startswith("gAAAAA"))

    def test_contact_email_decrypted_on_read(self):
        c = Contact.objects.create(
            email="x@test.com",
            last_name="A",
            first_name="B",
            contact_type="person",
        )
        c2 = Contact.objects.get(pk=c.pk)
        self.assertEqual(c2.email, "x@test.com")

    def test_empty_fields_not_encrypted(self):
        c = Contact.objects.create(
            email="",
            phone="",
            pec="",
            mobile="",
            tax_code="",
            last_name="Z",
            first_name="Y",
            contact_type="person",
        )
        table = Contact._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT email, phone FROM `{table}` WHERE id = %s",
                [_pk_for_raw_sql(c)],
            )
            row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIn(row[0], ("", None))
        self.assertIn(row[1], ("", None))
        c2 = Contact.objects.get(pk=c.pk)
        self.assertEqual(c2.email, "")
        self.assertEqual(c2.phone, "")

    def test_fallback_for_unencrypted_data(self):
        c = Contact.objects.create(
            email="will@override.com",
            last_name="L",
            first_name="F",
            contact_type="person",
        )
        table = Contact._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE `{table}` SET email = %s WHERE id = %s",
                ["legacy_plain@test.com", _pk_for_raw_sql(c)],
            )
        fresh = Contact.objects.get(pk=c.pk)
        self.assertEqual(fresh.email, "legacy_plain@test.com")
