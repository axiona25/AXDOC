"""
Copertura 100% apps.search.views.SearchView e apps.search.extractors.extract_text.
"""
import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from django.utils import timezone
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.documents.models import Document, Folder
from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol
from apps.search.models import DocumentIndex

User = get_user_model()


def _xh(tenant):
    return {"HTTP_X_TENANT_ID": str(tenant.id)}


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant(db):
    # Copre uso tenant default in combinazione con middleware
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Default Org", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="S100 OU", code="S1", tenant=tenant)


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(
        email=f"op-{uuid.uuid4().hex[:8]}@s100.test",
        password="test",
        role="OPERATOR",
        user_type="internal",
    )
    u.tenant_id = tenant.id
    u.save(update_fields=["tenant_id"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email=f"adm-{uuid.uuid4().hex[:8]}@s100.test",
        password="test",
        role="ADMIN",
        user_type="internal",
    )
    u.tenant_id = tenant.id
    u.save(update_fields=["tenant_id"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def guest_user(db, tenant):
    u = User.objects.create_user(
        email=f"gst-{uuid.uuid4().hex[:8]}@s100.test",
        password="test",
        role="OPERATOR",
        user_type="guest",
    )
    u.tenant_id = tenant.id
    u.save(update_fields=["tenant_id", "user_type"])
    return u


@pytest.fixture
def superuser(db, tenant):
    u = User.objects.create_superuser(
        email=f"su-{uuid.uuid4().hex[:8]}@s100.test",
        password="test",
    )
    u.tenant_id = tenant.id
    u.save(update_fields=["tenant_id"])
    return u


@pytest.fixture
def folder(db, tenant, operator_user):
    return Folder.objects.create(name="S100F", tenant=tenant, created_by=operator_user)


@pytest.mark.django_db
class TestSearchView100:
    # Copre righe: 33-34, 148-150 — page<1; snippet documenti con q vuoto
    def test_page_clamped_below_one(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="PageClamp",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "", "type": "all", "page": "-3"},
            **_xh(tenant),
        )
        assert r.status_code == 200

    # Copre righe: 36-37 — tipo ricerca non valido
    def test_invalid_search_type_returns_empty(self, api_client, operator_user, tenant):
        api_client.force_authenticate(user=operator_user)
        r = api_client.get("/api/search/", {"q": "x", "type": "folders"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["results"] == []

    # Copre righe: 58-71 — branch type=documents → _response_documents_only(..., response_type="documents")
    def test_type_documents_explicit(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="DocTipoExplicit",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "TipoExplicit", "type": "documents"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert r.json()["type"] == "documents"
        assert r.json()["total_count"] >= 1

    # Copre righe: 103-114, 118-119 — filtri documento
    def test_documents_advanced_filters(
        self, api_client, operator_user, tenant, folder, admin_user
    ):
        from apps.metadata.models import MetadataStructure

        ms = MetadataStructure.objects.create(name="S100 Meta")
        d = Document.objects.create(
            title="MetaDoc",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
            metadata_structure=ms,
            metadata_values={"ref_code": "RC-XYZ-99"},
        )
        day = date.today().isoformat()
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {
                "q": "MetaDoc",
                "type": "documents",
                "folder_id": str(folder.id),
                "metadata_structure_id": str(ms.id),
                "status": Document.STATUS_DRAFT,
                "created_by": str(operator_user.id),
                "date_from": day,
                "date_to": day,
                "metadata_ref_code": "RC-XYZ",
            },
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert any(x["id"] == str(d.id) for x in r.json()["results"])

    # Copre righe: 126-127 — order_by=relevance con q
    def test_order_by_relevance(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="RelQ",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "RelQ", "type": "documents", "order_by": "relevance"},
            **_xh(tenant),
        )
        assert r.status_code == 200

    # Copre righe: 128-129 — ordinamento valido
    def test_order_by_title(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="ZetaOrder",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "Zeta", "type": "documents", "order_by": "title"},
            **_xh(tenant),
        )
        assert r.status_code == 200

    # Copre righe: 130-131 — order_by non valido → else
    def test_order_by_invalid_fallback(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="GammaFB",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "GammaFB", "type": "documents", "order_by": "not-a-real-field"},
            **_xh(tenant),
        )
        assert r.status_code == 200

    # Copre righe: 138-143 — snippet da indice full-text
    def test_snippet_from_search_index(self, api_client, operator_user, tenant, folder):
        doc = Document.objects.create(
            title="NoMatchTitle",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        DocumentIndex.objects.create(document=doc, content="testo lungo " * 20 + "NEEDLE998" + " fine")
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "NEEDLE998", "type": "documents"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        rows = r.json()["results"]
        assert any("NEEDLE998" in (x.get("snippet") or "") for x in rows)

    # Copre righe: 144-147 — snippet solo titolo; score 1 se titolo contiene q
    def test_snippet_from_title_only_score_one(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="TitoloUnicoS100",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "TitoloUnicoS100", "type": "documents"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        row = next(x for x in r.json()["results"] if "TitoloUnico" in x.get("title", ""))
        assert row.get("score") == 1

    # Copre righe: 146-147 — score 0 quando match solo da indice (titolo non contiene q)
    def test_score_zero_when_match_only_in_index(self, api_client, operator_user, tenant, folder):
        doc = Document.objects.create(
            title="AltroTitolo",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        DocumentIndex.objects.create(document=doc, content="parolaSEGRETAidx")
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "parolaSEGRETAidx", "type": "documents"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        row = next(x for x in r.json()["results"] if x["id"] == str(doc.id))
        assert row.get("score") == 0

    # Copre righe: 159-160 — except su facet status
    def test_facets_status_exception_swallowed(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="FacetEx",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        _orig_values = QuerySet.values

        def _values(self, *fields, **kwargs):
            if fields == ("status",):
                raise RuntimeError("facet boom")
            return _orig_values(self, *fields, **kwargs)

        with patch.object(QuerySet, "values", _values):
            r = api_client.get("/api/search/", {"q": "", "type": "all"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json().get("facets") == {}

    # Copre righe: 233 — superuser: queryset protocolli senza filtro tenant
    def test_superuser_protocol_queryset_all(self, api_client, superuser, tenant, ou):
        other_t, _ = Tenant.objects.get_or_create(
            slug=f"other-{uuid.uuid4().hex[:6]}",
            defaults={"name": "Other", "plan": "enterprise"},
        )
        p = Protocol.objects.create(
            tenant=other_t,
            protocol_id="EXT/P/1",
            subject="SuperProto",
            direction="in",
            status="active",
            created_by=superuser,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2099,
            number=501,
        )
        api_client.force_authenticate(user=superuser)
        r = api_client.get(
            "/api/search/",
            {"q": "SuperProto", "type": "protocols"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert any(x["id"] == str(p.id) for x in r.json()["results"])

    # Copre righe: 298 — superuser: queryset fascicoli senza filtro tenant
    def test_superuser_dossier_queryset_all(self, api_client, superuser, tenant, ou):
        other_t, _ = Tenant.objects.get_or_create(
            slug=f"oth2-{uuid.uuid4().hex[:6]}",
            defaults={"name": "Other2", "plan": "enterprise"},
        )
        d = Dossier.objects.create(
            tenant=other_t,
            title="SuperDossier",
            identifier="S100-D-999",
            created_by=superuser,
            organizational_unit=ou,
        )
        api_client.force_authenticate(user=superuser)
        r = api_client.get(
            "/api/search/",
            {"q": "SuperDossier", "type": "dossiers"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert any(x["id"] == str(d.id) for x in r.json()["results"])

    # Copre righe: 245-246 — guest su slice protocolli
    def test_guest_protocol_search_empty(self, api_client, guest_user, tenant, ou):
        Protocol.objects.create(
            tenant=tenant,
            protocol_id="2026/S1/700",
            subject="GuestHidden",
            direction="in",
            status="active",
            created_by=guest_user,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2026,
            number=700,
        )
        api_client.force_authenticate(user=guest_user)
        r = api_client.get(
            "/api/search/",
            {"q": "GuestHidden", "type": "all", "page_size": "5"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert r.json()["facets"].get("protocols", 0) == 0

    # Copre righe: 349 — sottotitolo fascicolo da responsabile
    def test_dossier_subtitle_from_responsible(self, api_client, operator_user, tenant, ou, admin_user):
        d = Dossier.objects.create(
            tenant=tenant,
            title="FascResp",
            identifier="FR-001",
            created_by=operator_user,
            organizational_unit=ou,
            responsible=admin_user,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "FascResp", "type": "dossiers"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        row = r.json()["results"][0]
        assert admin_user.get_full_name() in (row.get("subtitle") or "") or admin_user.email in (row.get("subtitle") or "")

    # Copre righe: 405-406 — type=protocols senza q
    def test_single_protocols_empty_query(self, api_client, operator_user, tenant):
        api_client.force_authenticate(user=operator_user)
        r = api_client.get("/api/search/", {"q": "", "type": "protocols"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] == 0

    # Copre righe: 418-420 — type=dossiers senza q
    def test_single_dossiers_empty_query(self, api_client, operator_user, tenant):
        api_client.force_authenticate(user=operator_user)
        r = api_client.get("/api/search/", {"q": "", "type": "dossiers"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] == 0

    # Copre righe: 431-432 — type=contacts senza q
    def test_single_contacts_empty_query(self, api_client, operator_user, tenant):
        api_client.force_authenticate(user=operator_user)
        r = api_client.get("/api/search/", {"q": "", "type": "contacts"}, **_xh(tenant))
        assert r.status_code == 200
        assert r.json()["total_count"] == 0

    # Copre righe: 407-414 — paginazione protocolli (offset > 0)
    def test_protocols_pagination_offset(self, api_client, operator_user, tenant, ou):
        for i in range(3):
            Protocol.objects.create(
                tenant=tenant,
                protocol_id=f"2026/S1/P{i}",
                subject=f"PagProto {i}",
                direction="in",
                status="active",
                created_by=operator_user,
                organizational_unit=ou,
                registered_at=timezone.now(),
                year=2026,
                number=800 + i,
            )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "PagProto", "type": "protocols", "page": "2", "page_size": "1"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    # Copre righe: 274-276 — titolo protocollo da protocol_id+subject vuoti → str(id)
    def test_protocol_title_fallback_id(self, api_client, operator_user, tenant, ou):
        p = Protocol.objects.create(
            tenant=tenant,
            protocol_id="",
            subject="",
            notes="MARKEMPTYTITLE999",
            direction="in",
            status="active",
            created_by=operator_user,
            organizational_unit=ou,
            registered_at=timezone.now(),
            year=2026,
            number=920,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "MARKEMPTYTITLE999", "type": "protocols"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        row = next(x for x in r.json()["results"] if x["id"] == str(p.id))
        assert row["title"] == str(p.id)

    # Copre righe: 370-371 — contatto non visibile a non-admin se non è shared o creato da user
    def test_contact_non_admin_visibility(self, api_client, operator_user, tenant, admin_user):
        Contact.objects.create(
            first_name="Nascosto",
            last_name="X",
            is_shared=False,
            created_by=admin_user,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "Nascosto", "type": "contacts"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert r.json()["total_count"] == 0

    # Copre righe: 169-189 — _response_all_types
    def test_all_types_with_q(self, api_client, operator_user, tenant, folder):
        Document.objects.create(
            title="AllT",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "AllT", "type": "all"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert r.json()["type"] == "all"

    # Copre righe: 209-212 — snippet da indice in _search_documents_slice (type=all)
    def test_all_types_slice_snippet_from_index(self, api_client, operator_user, tenant, folder):
        doc = Document.objects.create(
            title="NoTitleHitSlice",
            folder=folder,
            created_by=operator_user,
            status=Document.STATUS_DRAFT,
            tenant=tenant,
        )
        DocumentIndex.objects.create(document=doc, content="contenuto SLICEIDX999 unico")
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "SLICEIDX999", "type": "all"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        doc_rows = [x for x in r.json()["results"] if x.get("type") == "document"]
        assert any("SLICEIDX999" in (x.get("snippet") or "") for x in doc_rows)

    # Copre righe: 238-239 — tenant slug ≠ default: filtro stretto su protocol.tenant
    def test_protocol_queryset_non_default_tenant_slug(self, api_client, operator_user, tenant):
        nd, _ = Tenant.objects.get_or_create(
            slug=f"nd-{uuid.uuid4().hex[:8]}",
            defaults={"name": "ND", "plan": "enterprise"},
        )
        nd_ou = OrganizationalUnit.objects.create(name="ND OU", code="N1", tenant=nd)
        operator_user.tenant_id = nd.id
        operator_user.save(update_fields=["tenant_id"])
        OrganizationalUnitMembership.objects.create(
            user=operator_user, organizational_unit=nd_ou, role="OPERATOR"
        )
        Protocol.objects.create(
            tenant=nd,
            protocol_id="ND/P/1",
            subject="ProtoNDSlug",
            direction="in",
            status="active",
            created_by=operator_user,
            organizational_unit=nd_ou,
            registered_at=timezone.now(),
            year=2031,
            number=1,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "ProtoNDSlug", "type": "protocols"},
            **_xh(nd),
        )
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    # Copre righe: 303-304 — tenant slug ≠ default: filtro stretto su dossier.tenant
    def test_dossier_queryset_non_default_tenant_slug(self, api_client, operator_user, tenant):
        nd, _ = Tenant.objects.get_or_create(
            slug=f"nd2-{uuid.uuid4().hex[:8]}",
            defaults={"name": "ND2", "plan": "enterprise"},
        )
        nd_ou = OrganizationalUnit.objects.create(name="ND2 OU", code="N2", tenant=nd)
        operator_user.tenant_id = nd.id
        operator_user.save(update_fields=["tenant_id"])
        Dossier.objects.create(
            tenant=nd,
            title="DossNDSlug",
            identifier="ND-DS-1",
            created_by=operator_user,
            organizational_unit=nd_ou,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "DossNDSlug", "type": "dossiers"},
            **_xh(nd),
        )
        assert r.status_code == 200
        assert r.json()["total_count"] >= 1

    # Copre righe: 386-399 — risultato contatto in slice
    def test_contact_result_row(self, api_client, operator_user, tenant):
        Contact.objects.create(
            first_name="Luigi",
            last_name="ContRow",
            company_name="AcmeS100",
            is_shared=True,
            created_by=operator_user,
        )
        api_client.force_authenticate(user=operator_user)
        r = api_client.get(
            "/api/search/",
            {"q": "ContRow", "type": "contacts"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        row = r.json()["results"][0]
        assert row["type"] == "contact"
        assert "/contacts/" in row["url"]

    # Copre righe: 403-404 — guest su type=protocols
    def test_guest_single_protocols_blocked(self, api_client, guest_user, tenant):
        api_client.force_authenticate(user=guest_user)
        r = api_client.get(
            "/api/search/",
            {"q": "anything", "type": "protocols"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert r.json()["total_count"] == 0

    # Copre righe: 417-418 — guest su type=dossiers
    def test_guest_single_dossiers_blocked(self, api_client, guest_user, tenant):
        api_client.force_authenticate(user=guest_user)
        r = api_client.get(
            "/api/search/",
            {"q": "anything", "type": "dossiers"},
            **_xh(tenant),
        )
        assert r.status_code == 200
        assert r.json()["total_count"] == 0


@pytest.mark.django_db
class TestExtractors100:
    # Copre righe: 62-64 — limite 5000 righe CSV (break a i>=5000)
    def test_csv_row_limit_break(self, tmp_path):
        from apps.search.extractors import extract_text

        p = tmp_path / "big.csv"
        lines = ["a,b"] + [f"{i},{i}" for i in range(5001)]
        lines[-1] = "LAST,SHOULD_NOT_APPEAR_IN_OUTPUT"
        p.write_text("\n".join(lines), encoding="utf-8")
        out = extract_text(str(p), "text/csv")
        assert "SHOULD_NOT_APPEAR_IN_OUTPUT" not in out
        assert "0 0" in out and "1 1" in out
