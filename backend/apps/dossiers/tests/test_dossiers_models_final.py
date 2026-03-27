# FASE 35E.1 — Copertura: dossiers/models.py
import uuid

import pytest
from django.utils import timezone

from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit, Tenant


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="DM", code="DM", tenant=tenant)


@pytest.mark.django_db
class TestDossierEnsureIdentifierFinal:
    def test_generates_identifier_on_first_save(self, tenant, ou):
        d = Dossier(
            title="Nuovo",
            organizational_unit=ou,
            tenant=tenant,
        )
        d.save()
        assert d.identifier
        assert str(timezone.now().year) in d.identifier
        assert ou.code in d.identifier

    def test_increments_progressivo(self, tenant, ou):
        d1 = Dossier(title="A", organizational_unit=ou, tenant=tenant)
        d1.save()
        d2 = Dossier(title="B", organizational_unit=ou, tenant=tenant)
        d2.save()
        n1 = int(d1.identifier.split("/")[-1])
        n2 = int(d2.identifier.split("/")[-1])
        assert n2 == n1 + 1

    def test_skips_malformed_existing_identifiers(self, tenant, ou):
        prefix = f"{timezone.now().year}/{ou.code}/"
        Dossier.objects.create(
            title="Bad",
            identifier=f"{prefix}not-a-number",
            organizational_unit=ou,
            tenant=tenant,
        )
        Dossier.objects.create(
            title="Bad2",
            identifier="weird",
            organizational_unit=ou,
            tenant=tenant,
        )
        d = Dossier(title="Ok", organizational_unit=ou, tenant=tenant)
        d.save()
        assert d.identifier.startswith(prefix)

    def test_ou_from_id_only(self, tenant, ou):
        d = Dossier(title="IdOu", organizational_unit_id=ou.id, tenant=tenant)
        d.save()
        assert d.identifier and ou.code in d.identifier
