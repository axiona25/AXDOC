# FASE 35E.1 — Copertura: metadata/serializers.py
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.metadata.models import MetadataField, MetadataStructure, MetadataStructureOU
from apps.metadata.serializers import MetadataStructureCreateSerializer
from apps.organizations.models import OrganizationalUnit, Tenant

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def admin(db, tenant):
    u = User.objects.create_user(
        email="msf-adm@test.com",
        password="TestPass123!",
        first_name="A",
        last_name="D",
        role="ADMIN",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    return u


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="MSOU", code="MSO", tenant=tenant)


@pytest.mark.django_db
class TestMetadataStructureCreateSerializerFinal:
    def test_validate_name_empty_and_duplicate(self, admin):
        MetadataStructure.objects.create(name="UniqueName")
        ser = MetadataStructureCreateSerializer(
            data={"name": "   ", "description": "x"},
            context={"request": type("R", (), {"user": admin})()},
        )
        assert ser.is_valid() is False
        ser2 = MetadataStructureCreateSerializer(
            data={"name": "uniquename", "description": "y"},
            context={"request": type("R", (), {"user": admin})()},
        )
        assert ser2.is_valid() is False

    def test_create_with_ous_signers_fields(self, admin, ou):
        factory = APIRequestFactory()
        req = factory.post("/")
        req.user = admin
        u2 = User.objects.create_user(
            email="msf2@test.com",
            password="TestPass123!",
            first_name="B",
            last_name="C",
            role="APPROVER",
        )
        ser = MetadataStructureCreateSerializer(
            data={
                "name": f"Struct-{uuid.uuid4().hex[:8]}",
                "description": "d",
                "allowed_organizational_units": [str(ou.id)],
                "allowed_signers": [str(u2.id)],
                "fields": [
                    {
                        "name": "campo1",
                        "label": "L1",
                        "field_type": "text",
                    }
                ],
            },
            context={"request": req},
        )
        assert ser.is_valid(), ser.errors
        s = ser.save()
        assert s.fields.count() == 1
        assert s.allowed_signers.filter(id=u2.id).exists()
        assert MetadataStructureOU.objects.filter(structure=s, organizational_unit=ou).exists()

    def test_update_fields_replace_and_patch_existing(self, admin, ou):
        factory = APIRequestFactory()
        req = factory.patch("/")
        req.user = admin
        s = MetadataStructure.objects.create(name=f"Up-{uuid.uuid4().hex[:8]}")
        f1 = MetadataField.objects.create(
            structure=s,
            name="f1",
            label="F1",
            field_type="text",
            order=0,
        )
        ser = MetadataStructureCreateSerializer(
            instance=s,
            data={
                "name": s.name,
                "allowed_organizational_units": [str(ou.id)],
                "fields": [
                    {
                        "id": str(f1.id),
                        "name": "f1",
                        "label": "F1b",
                        "field_type": "text",
                        "is_required": True,
                    },
                ],
            },
            partial=True,
            context={"request": req},
        )
        assert ser.is_valid(), ser.errors
        ser.save()
        f1.refresh_from_db()
        assert f1.label == "F1b"
        assert MetadataStructureOU.objects.filter(structure=s, organizational_unit=ou).exists()

    def test_update_adds_new_field_only(self, admin):
        factory = APIRequestFactory()
        req = factory.patch("/")
        req.user = admin
        s = MetadataStructure.objects.create(name=f"Up2-{uuid.uuid4().hex[:8]}")
        ser = MetadataStructureCreateSerializer(
            instance=s,
            data={
                "fields": [
                    {
                        "name": "nf",
                        "label": "NF",
                        "field_type": "text",
                    },
                ],
            },
            partial=True,
            context={"request": req},
        )
        assert ser.is_valid(), ser.errors
        ser.save()
        assert s.fields.filter(name="nf").exists()
