# FASE 35F — Copertura protocols (views, serializers, models)
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol, ProtocolCounter
from apps.protocols.serializers import ProtocolCreateSerializer
from apps.protocols.views import _normalize_protocol_direction_param
from apps.users.models import User


def test_normalize_direction_returns_none():
    assert _normalize_protocol_direction_param("  ???  ") is None
    assert _normalize_protocol_direction_param("  in  ") == "in"


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Default", "plan": "enterprise"},
    )
    return t


@pytest.mark.django_db
class TestProtocolModels100pct:
    def test_str_and_direction_display_legacy(self, tenant, db):
        ou = OrganizationalUnit.objects.create(name="O", code="LEG", tenant=tenant)
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        u = User.objects.create_user(
            email="p100-u@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
            role="ADMIN",
        )
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id="",
            protocol_number="",
            direction=Protocol.DIRECTION_IN_LEGACY,
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=u,
            status="active",
            created_by=u,
            tenant=tenant,
        )
        assert str(p.id) in str(p)
        assert "entrata" in p.get_direction_display().lower() or "in" in p.get_direction_display().lower()

    def test_direction_out_legacy_display(self, tenant):
        ou = OrganizationalUnit.objects.create(name="O", code="OUT", tenant=tenant)
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        u = User.objects.create_user(
            email="p100-out@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
            role="ADMIN",
        )
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="OUT",
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=u,
            status="active",
            created_by=u,
            tenant=tenant,
        )
        assert "uscita" in p.get_direction_display().lower()


@pytest.mark.django_db
class TestProtocolSerializers100pct:
    def test_validate_organizational_unit_and_subject(self, tenant):
        ser = ProtocolCreateSerializer(data={"direction": "in", "subject": "   "})
        assert ser.is_valid() is False
        assert "subject" in ser.errors
        ou = OrganizationalUnit.objects.create(name="O", code="V", tenant=tenant)
        ser2 = ProtocolCreateSerializer(
            data={"direction": "in", "subject": " OK ", "organizational_unit": str(ou.id)}
        )
        assert ser2.is_valid(), ser2.errors


@pytest.mark.django_db
class TestProtocolViewsStampedDocument100pct:
    def test_stamped_document_coverpage_when_no_input_file(self, tenant):
        admin = User.objects.create_user(
            email="p100-adm@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
            role="ADMIN",
        )
        ou = OrganizationalUnit.objects.create(name="O2", code="ST", tenant=tenant)
        OrganizationalUnitMembership.objects.create(
            user=admin, organizational_unit=ou, role="OPERATOR", is_active=True
        )
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="in",
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=admin,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=admin,
            tenant=tenant,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        with patch("apps.protocols.views.AGIDConverter.generate_protocol_coverpage") as cov:
            cov.return_value = None
            r = client.get(f"/api/protocols/{p.id}/stamped_document/")
        assert r.status_code == 200

    def test_stamped_document_document_file_path_not_on_disk(self, tenant):
        from django.core.files.base import ContentFile

        admin = User.objects.create_user(
            email="p100-adm2@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
            role="ADMIN",
        )
        ou = OrganizationalUnit.objects.create(name="O3", code="S3", tenant=tenant)
        OrganizationalUnitMembership.objects.create(
            user=admin, organizational_unit=ou, role="OPERATOR", is_active=True
        )
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="in",
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=admin,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=admin,
            tenant=tenant,
            document_file=ContentFile(b"%PDF", name="x.pdf"),
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        with patch("apps.protocols.views.os.path.isfile", return_value=False):
            with patch("apps.protocols.views.AGIDConverter.generate_protocol_coverpage"):
                r = client.get(f"/api/protocols/{p.id}/stamped_document/")
        assert r.status_code == 200
