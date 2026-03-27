# FASE 35F — Copertura dossiers/models.py (Dossier._ensure_identifier e rami collegati)
import pytest
from django.utils import timezone

from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit, Tenant
from apps.users.models import User


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Default", "plan": "enterprise"},
    )
    return t


@pytest.mark.django_db
class TestDossierEnsureIdentifier:
    def test_create_with_organizational_unit_id_only(self, tenant):
        u = User.objects.create_user(
            email="dm100-u@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="OU", code="OU1", tenant=tenant)
        d = Dossier(
            title="T",
            created_by=u,
            tenant=tenant,
            organizational_unit_id=ou.pk,
        )
        d.save()
        assert d.identifier
        assert str(ou.code) in d.identifier

    def test_skips_malformed_existing_identifiers_in_max(self, tenant):
        u = User.objects.create_user(
            email="dm101-u@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="OU2", code="OU2", tenant=tenant)
        y = timezone.now().year
        prefix = f"{y}/{ou.code}/"
        Dossier.objects.create(
            title="Bad",
            identifier=f"{prefix}\u0664",
            organizational_unit=ou,
            created_by=u,
            tenant=tenant,
        )
        d2 = Dossier(title="Good", organizational_unit=ou, created_by=u, tenant=tenant)
        d2.save()
        assert d2.identifier.startswith(prefix)
        assert d2.identifier.split("/")[-1].isdigit()

    def test_update_does_not_regenerate_identifier(self, tenant):
        u = User.objects.create_user(
            email="dm102-u@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="OU3", code="OU3", tenant=tenant)
        d = Dossier.objects.create(
            title="X",
            identifier="KEEP-ID",
            organizational_unit=ou,
            created_by=u,
            tenant=tenant,
        )
        d.title = "Y"
        d.save()
        assert d.identifier == "KEEP-ID"

    def test_no_generation_when_ou_has_no_code(self, tenant):
        u = User.objects.create_user(
            email="dm103-u@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou = OrganizationalUnit.objects.create(name="Nocode", code="", tenant=tenant)
        d = Dossier(title="Z", organizational_unit=ou, created_by=u, tenant=tenant)
        d.save()
        assert not (d.identifier or "").strip()
        d.title = "Z2"
        d.save()
