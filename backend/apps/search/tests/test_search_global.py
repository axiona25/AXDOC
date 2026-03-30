"""Ricerca globale multi-tipo (FASE 37)."""
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.documents.models import Document, Folder
from apps.dossiers.models import Dossier, DossierEmail
from apps.organizations.models import OrganizationalUnit, Tenant
from apps.protocols.models import Protocol

User = get_user_model()


def _xh(tenant):
    return {"HTTP_X_TENANT_ID": str(tenant.id)}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="SG Test Tenant",
        slug=f"sg-{uuid.uuid4().hex[:12]}",
        plan="enterprise",
    )


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="SG OU", code="SG", tenant=tenant)


@pytest.fixture
def internal_user(db, tenant, ou):
    u = User.objects.create_user(
        email=f"sg-int-{uuid.uuid4().hex[:8]}@test.com", password="test", user_type="internal"
    )
    u.tenant_id = tenant.id
    u.save(update_fields=["tenant_id"])
    return u


@pytest.fixture
def guest_user(db, tenant):
    u = User.objects.create_user(email=f"sg-guest-{uuid.uuid4().hex[:8]}@test.com", password="test", user_type="guest")
    u.tenant_id = tenant.id
    u.save(update_fields=["tenant_id", "user_type"])
    return u


@pytest.fixture
def folder(db, tenant, internal_user):
    return Folder.objects.create(name="SGF", tenant=tenant, created_by=internal_user)


@pytest.mark.django_db
class TestSearchGlobal:
    def test_search_all_returns_documents_and_protocols(
        self, api_client, internal_user, tenant, ou, folder
    ):
        doc = Document.objects.create(
            title="Fattura SG alpha",
            folder=folder,
            created_by=internal_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        now = timezone.now()
        proto = Protocol.objects.create(
            tenant=tenant,
            protocol_id="2026/SG/0001",
            subject="Fattura fornitore",
            direction="in",
            status="active",
            created_by=internal_user,
            organizational_unit=ou,
            registered_at=now,
            year=2026,
            number=1,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "Fattura", "type": "all"}, **_xh(tenant))
        assert r.status_code == 200
        data = r.json()
        types = {x.get("type") for x in data["results"]}
        assert "document" in types
        assert "protocol" in types
        assert data["facets"].get("documents", 0) >= 1
        assert data["facets"].get("protocols", 0) >= 1
        assert any(x["id"] == str(doc.id) for x in data["results"] if x.get("type") == "document")
        assert any(x["id"] == str(proto.id) for x in data["results"] if x.get("type") == "protocol")

    def test_search_protocols_by_subject(self, api_client, internal_user, tenant, ou):
        Protocol.objects.create(
            tenant=tenant,
            protocol_id="2026/SG/0002",
            subject="Oggetto unico XYZSG",
            direction="in",
            status="active",
            created_by=internal_user,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2026,
            number=2,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "unico XYZSG", "type": "protocols"}, **_xh(tenant))
        assert r.status_code == 200
        data = r.json()
        assert data["total_count"] >= 1
        assert any("unico" in (x.get("title") or "").lower() for x in data["results"])

    def test_search_protocols_by_protocol_id(self, api_client, internal_user, tenant, ou):
        Protocol.objects.create(
            tenant=tenant,
            protocol_id="SG-PROTO-999",
            subject="",
            direction="in",
            status="active",
            created_by=internal_user,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2026,
            number=3,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "SG-PROTO-999", "type": "protocols"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    def test_search_dossiers_by_title(self, api_client, internal_user, tenant, ou):
        Dossier.objects.create(
            tenant=tenant,
            title="Pratica edilizia SG",
            identifier="2026/SG/0001",
            created_by=internal_user,
            organizational_unit=ou,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "edilizia", "type": "dossiers"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    def test_search_dossiers_by_identifier(self, api_client, internal_user, tenant, ou):
        Dossier.objects.create(
            tenant=tenant,
            title="Tit",
            identifier="ID-SG-777",
            created_by=internal_user,
            organizational_unit=ou,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "ID-SG-777", "type": "dossiers"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    def test_search_contacts_by_name(self, api_client, internal_user, tenant):
        Contact.objects.create(
            first_name="Mario",
            last_name="RossiSG",
            company_name="Acme",
            is_shared=True,
            created_by=internal_user,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "RossiSG", "type": "contacts"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    def test_search_empty_query_returns_documents_only(self, api_client, internal_user, folder, tenant):
        Document.objects.create(
            title="Solo doc SG",
            folder=folder,
            created_by=internal_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        Protocol.objects.create(
            tenant=tenant,
            protocol_id="2026/SG/8888",
            subject="Altro",
            direction="in",
            status="active",
            created_by=internal_user,
            registered_at=timezone.now(),
            year=2026,
            number=88,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "", "type": "all"}, **_xh(tenant))
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "all"
        assert data["total_count"] >= 1
        for row in data["results"]:
            assert "id" in row
            assert "title" in row

    def test_search_guest_cannot_search_protocols(self, api_client, guest_user, tenant, ou):
        Protocol.objects.create(
            tenant=tenant,
            protocol_id="2026/SG/0009",
            subject="Segreto guest",
            direction="in",
            status="active",
            created_by=guest_user,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2026,
            number=9,
        )
        api_client.force_authenticate(user=guest_user)
        r = api_client.get("/api/search/", {"q": "Segreto", "type": "protocols"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] == 0

    def test_facets_show_counts_per_type(self, api_client, internal_user, tenant, ou, folder):
        Document.objects.create(
            title="Doc facet SG",
            folder=folder,
            created_by=internal_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        Protocol.objects.create(
            tenant=tenant,
            protocol_id="2026/SG/0010",
            subject="Proto facet SG",
            direction="in",
            status="active",
            created_by=internal_user,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2026,
            number=10,
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "facet SG", "type": "all"}, **_xh(tenant))
        assert r.status_code == 200
        f = r.json()["facets"]
        assert "documents" in f
        assert "protocols" in f
        assert "dossiers" in f
        assert "contacts" in f

    def test_search_dossier_finds_by_email_subject(self, api_client, internal_user, tenant, ou):
        d = Dossier.objects.create(
            tenant=tenant,
            title="No match in title",
            identifier="EM-SG-1",
            created_by=internal_user,
            organizational_unit=ou,
        )
        DossierEmail.objects.create(
            dossier=d,
            email_type="email",
            from_address="x@y.it",
            subject="ParolaSegretaEmailSG",
            body="",
            received_at=timezone.now(),
        )
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "ParolaSegretaEmailSG", "type": "dossiers"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    def test_search_protocol_finds_by_attachment_index(
        self, api_client, internal_user, tenant, ou, folder
    ):
        from apps.protocols.models import ProtocolAttachment
        from apps.search.models import DocumentIndex

        doc = Document.objects.create(
            title="Attachment title SG",
            folder=folder,
            created_by=internal_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        DocumentIndex.objects.create(document=doc, content="testo allegato XYZSG unico")
        p = Protocol.objects.create(
            tenant=tenant,
            protocol_id="2026/SG/0111",
            subject="No keyword here",
            direction="in",
            status="active",
            created_by=internal_user,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2026,
            number=111,
        )
        ProtocolAttachment.objects.create(protocol=p, document=doc)
        api_client.force_authenticate(user=internal_user)
        r = api_client.get("/api/search/", {"q": "XYZSG", "type": "protocols"}, **_xh(tenant))
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()["results"]]
        assert str(p.id) in ids
