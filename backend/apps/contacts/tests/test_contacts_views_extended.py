"""Test estesi rubrica contatti (FASE 33B)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.mail.models import MailAccount, MailMessage
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin(api):
    u = User.objects.create_user(email="c-admin@test.com", password="Test123!", role="ADMIN")
    api.force_authenticate(user=u)
    return u


@pytest.fixture
def operator(api):
    u = User.objects.create_user(email="c-op@test.com", password="Test123!", role="OPERATOR")
    api.force_authenticate(user=u)
    return u


@pytest.mark.django_db
class TestContactFiltersAndCrud:
    def test_filter_by_type_company(self, api, admin):
        Contact.objects.create(
            contact_type="company",
            company_name="Acme SpA",
            created_by=admin,
            is_shared=True,
        )
        r = api.get("/api/contacts/", {"type": "company"})
        assert r.status_code == 200
        rows = r.data if isinstance(r.data, list) else r.data.get("results", [])
        assert any(x.get("contact_type") == "company" and "Acme" in (x.get("company_name") or "") for x in rows)

    def test_search_by_name_not_email_field(self, api, admin):
        Contact.objects.create(
            contact_type="person",
            first_name="Mario",
            last_name="Bianchi",
            created_by=admin,
            is_shared=True,
        )
        r = api.get("/api/contacts/", {"search": "Mario"})
        assert r.status_code == 200

    def test_patch_partial(self, api, admin):
        c = Contact.objects.create(
            contact_type="person",
            first_name="Old",
            last_name="Name",
            created_by=admin,
            is_shared=True,
        )
        r = api.patch(f"/api/contacts/{c.id}/", {"first_name": "New"}, format="json")
        assert r.status_code == 200
        c.refresh_from_db()
        assert c.first_name == "New"

    def test_delete_contact(self, api, admin):
        c = Contact.objects.create(
            contact_type="person",
            first_name="Del",
            created_by=admin,
            is_shared=True,
        )
        r = api.delete(f"/api/contacts/{c.id}/")
        assert r.status_code in (status.HTTP_204_NO_CONTENT, 204)
        assert not Contact.objects.filter(id=c.id).exists()

    def test_operator_sees_only_shared_or_own(self, api, admin, operator):
        Contact.objects.create(
            contact_type="person",
            first_name="Private",
            created_by=admin,
            is_shared=False,
        )
        api.force_authenticate(user=operator)
        r = api.get("/api/contacts/")
        assert r.status_code == 200
        rows = r.data if isinstance(r.data, list) else r.data.get("results", [])
        ids = {x["id"] for x in rows}
        priv = Contact.objects.get(first_name="Private")
        assert str(priv.id) not in ids

    def test_import_from_mail_creates_contact(self, api, admin):
        acc = MailAccount.objects.create(
            name="M",
            email_address="mailacc@test.com",
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
        )
        MailMessage.objects.create(
            account=acc,
            direction="in",
            from_address="imported_ext@external.com",
            from_name="Ext User",
            subject="Hi",
            status="read",
            folder="INBOX",
            sent_at=timezone.now(),
        )
        r = api.post("/api/contacts/import_from_mail/", {}, format="json")
        assert r.status_code == 200
        body = r.json()
        assert body.get("created", 0) >= 1
        assert Contact.objects.filter(source="mail_import").exists()
