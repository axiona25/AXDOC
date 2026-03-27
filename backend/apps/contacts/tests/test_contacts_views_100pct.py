"""Copertura ramificazioni views contatti (ricerca, filtri, import mail, preferiti)."""
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.mail.models import MailAccount, MailMessage
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant

User = get_user_model()


def _list_payload(resp):
    j = resp.json()
    if isinstance(j, dict) and "results" in j:
        return j["results"]
    return j


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def admin_client(db, tenant):
    u = User.objects.create_user(
        email=f"ct100-{uuid.uuid4().hex[:8]}@test.com",
        password="Test123!",
        role="ADMIN",
        first_name="A",
        last_name="D",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    ou = OrganizationalUnit.objects.create(name="CT OU", code=f"CT{uuid.uuid4().hex[:4]}", tenant=tenant)
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    c = APIClient()
    c.force_authenticate(user=u)
    return c, u


@pytest.mark.django_db
class TestContactsViewsCoverage:
    def test_list_filter_type_tag_favorites_search_at(self, admin_client):
        client, _ = admin_client
        Contact.objects.create(
            contact_type="company",
            company_name="Acme",
            email=f"pec-{uuid.uuid4().hex[:8]}@pec.it",
            tags=["fornitore"],
            is_favorite=True,
            is_shared=True,
        )
        r = client.get("/api/contacts/", {"type": "company"})
        assert r.status_code == 200
        assert any(x.get("company_name") == "Acme" for x in _list_payload(r))

        r2 = client.get("/api/contacts/", {"tag": "fornitore"})
        assert r2.status_code == 200

        r3 = client.get("/api/contacts/", {"favorites": "true"})
        assert r3.status_code == 200

        acme = Contact.objects.filter(company_name="Acme").first()
        r4 = client.get("/api/contacts/", {"search": acme.email})
        assert r4.status_code == 200

    def test_search_action_short_q_returns_empty(self, admin_client):
        client, _ = admin_client
        r = client.get("/api/contacts/search/", {"q": "a"})
        assert r.status_code == 200
        assert r.json() == []

    def test_search_action_q_contains_at_branch(self, admin_client):
        client, _ = admin_client
        # Con email/PEC cifrati il filtro ORM email= non è applicabile in SQL; il ramo @ resta eseguito.
        r = client.get("/api/contacts/search/", {"q": "zz@unused.example"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_import_from_mail_dict_str_and_skips(self, admin_client):
        client, admin = admin_client
        ext = uuid.uuid4().hex[:8]
        new_em = f"imported-{ext}@external.org"
        internal_em = f"internal-{ext}@test.com"
        User.objects.create_user(email=internal_em, password="x", role="OPERATOR")

        acc = MailAccount.objects.create(
            name="Acc CT",
            email_address=f"acc-{ext}@srv.local",
            imap_host="i",
            imap_username="i",
            imap_password="p",
            smtp_host="s",
            smtp_username="s",
            smtp_password="p",
        )
        MailMessage.objects.create(
            account=acc,
            from_address=f"from-{ext}@ext.com",
            from_name="From Name",
            to_addresses=[
                {"email": new_em, "name": "Nuovo Contatto"},
                "plainaddr@list.com",
                999,
            ],
            cc_addresses=[{"email": f"cc-{ext}@cc.org", "name": "CC Person"}],
            direction="in",
        )
        Contact.objects.create(
            contact_type="person",
            first_name="E",
            last_name="X",
            email="plainaddr@list.com",
            is_shared=True,
        )

        r = client.post("/api/contacts/import_from_mail/", {}, format="json")
        assert r.status_code == 200
        body = r.json()
        assert body["created"] >= 1
        assert Contact.objects.filter(source="mail_import", last_name="Contatto").exists()

    def test_import_skips_non_email_and_internal(self, admin_client):
        client, admin = admin_client
        ext = uuid.uuid4().hex[:8]
        internal_match = f"skip-{ext}@test.com"
        User.objects.create_user(email=internal_match, password="x", role="OPERATOR")
        acc = MailAccount.objects.create(
            name="Acc2",
            email_address=f"acc2-{ext}@srv.local",
            imap_host="i",
            imap_username="i",
            imap_password="p",
            smtp_host="s",
            smtp_username="s",
            smtp_password="p",
        )
        MailMessage.objects.create(
            account=acc,
            from_address=f"ext-{ext}@out.it",
            to_addresses=[
                {"email": "badlocal", "name": "X"},
                {"email": internal_match, "name": "Int"},
            ],
            direction="in",
        )
        r = client.post("/api/contacts/import_from_mail/", {}, format="json")
        assert r.status_code == 200
        body = r.json()
        assert body["internal_skipped"] >= 1

    def test_toggle_favorite(self, admin_client):
        client, _ = admin_client
        cr = client.post(
            "/api/contacts/",
            {"first_name": "Fav", "last_name": "One", "contact_type": "person"},
            format="json",
        )
        assert cr.status_code == 201
        cid = cr.json()["id"]
        r = client.post(f"/api/contacts/{cid}/toggle_favorite/")
        assert r.status_code == 200
        assert r.json().get("is_favorite") is True
        r2 = client.post(f"/api/contacts/{cid}/toggle_favorite/")
        assert r2.json().get("is_favorite") is False
