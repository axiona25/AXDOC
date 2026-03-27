# Copertura: dossiers/* FASE 35D.2
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document, Folder
from apps.dossiers.models import Dossier, DossierDocument, DossierPermission, DossierProtocol
from apps.dossiers.serializers import DossierCreateSerializer
from apps.metadata.models import MetadataField, MetadataStructure
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol, ProtocolCounter

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="DOU", code="DOU", tenant=tenant)


@pytest.fixture
def admin(db, tenant, ou):
    u = User.objects.create_user(
        email="dosfin-adm@test.com",
        password="TestPass123!",
        first_name="A",
        last_name="D",
        role="ADMIN",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    return u


@pytest.fixture
def operator(db, tenant, ou):
    u = User.objects.create_user(
        email="dosfin-op@test.com",
        password="TestPass123!",
        first_name="O",
        last_name="P",
        role="OPERATOR",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.mark.django_db
class TestDossierModelsFinal:
    def test_dossier_str_validate_and_identifier(self, admin, ou):
        d = Dossier.objects.create(
            title="T",
            identifier="ID-1",
            created_by=admin,
            responsible=admin,
            organizational_unit=ou,
        )
        assert "ID-1" in str(d)
        assert d.validate_metadata({}) == []
        ms = MetadataStructure.objects.create(
            name=f"DS-{uuid.uuid4().hex[:8]}",
            applicable_to=["dossier"],
            tenant=admin.tenant,
        )
        MetadataField.objects.create(
            structure=ms,
            name="f",
            label="F",
            field_type="text",
            is_required=False,
            order=0,
        )
        d.metadata_structure = ms
        d.save(update_fields=["metadata_structure"])
        assert isinstance(d.validate_metadata({"f": "x"}), list)
        folder = Folder.objects.create(name="DF", tenant=admin.tenant, created_by=admin)
        doc = Document.objects.create(title="D", folder=folder, created_by=admin, owner=admin)
        DossierDocument.objects.create(dossier=d, document=doc, added_by=admin)
        assert d.get_documents().filter(id=doc.id).exists()
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
        )
        DossierProtocol.objects.create(dossier=d, protocol=p, added_by=admin)
        assert d.get_protocols().filter(id=p.id).exists()

@pytest.mark.django_db
class TestDossierSerializersFinal:
    def test_validate_identifier_update_exclude(self, admin, ou):
        d1 = Dossier.objects.create(
            title="A",
            identifier="UQ-1",
            created_by=admin,
            responsible=admin,
        )
        d2 = Dossier.objects.create(
            title="B",
            identifier="UQ-2",
            created_by=admin,
            responsible=admin,
        )
        ser = DossierCreateSerializer(
            instance=d2,
            data={"identifier": "UQ-1", "title": "B2"},
            partial=True,
        )
        assert ser.is_valid() is False
        ser2 = DossierCreateSerializer(instance=d2, data={"identifier": "  ", "title": "B2"}, partial=True)
        assert ser2.is_valid(), ser2.errors


@pytest.mark.django_db
class TestDossierViewsFinal:
    def test_update_forbidden_readonly_user(self, operator, admin, ou):
        d = Dossier.objects.create(
            title="RO",
            identifier="RO-1",
            created_by=admin,
            responsible=admin,
        )
        DossierPermission.objects.create(dossier=d, user=operator, can_read=True, can_write=False)
        c = APIClient()
        c.force_authenticate(user=operator)
        r = c.patch(f"/api/dossiers/{d.id}/", {"title": "X"}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_update_metadata_json_invalid_string(self, admin, ou):
        d = Dossier.objects.create(
            title="M",
            identifier="M-1",
            created_by=admin,
            responsible=admin,
        )
        ms = MetadataStructure.objects.create(
            name=f"M2-{uuid.uuid4().hex[:8]}",
            applicable_to=["dossier"],
            tenant=admin.tenant,
        )
        MetadataField.objects.create(
            structure=ms,
            name="f",
            label="F",
            field_type="text",
            is_required=True,
            order=0,
        )
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.patch(
            f"/api/dossiers/{d.id}/",
            {
                "title": "M",
                "metadata_structure_id": str(ms.id),
                "metadata_values": "{bad json",
            },
            format="json",
        )
        assert r.status_code in (200, 400)

    def test_update_metadata_validation_error(self, admin, ou):
        d = Dossier.objects.create(
            title="MV",
            identifier="MV-1",
            created_by=admin,
            responsible=admin,
        )
        ms = MetadataStructure.objects.create(
            name=f"MVs-{uuid.uuid4().hex[:8]}",
            applicable_to=["dossier"],
            tenant=admin.tenant,
        )
        MetadataField.objects.create(
            structure=ms,
            name="f",
            label="F",
            field_type="text",
            is_required=True,
            order=0,
        )
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.patch(
            f"/api/dossiers/{d.id}/",
            {
                "metadata_structure_id": str(ms.id),
                "metadata_values": {},
            },
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_protocol_duplicate_and_remove_missing(self, admin, ou, tenant):
        d = Dossier.objects.create(
            title="P",
            identifier="P-1",
            created_by=admin,
            responsible=admin,
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
        )
        c = APIClient()
        c.force_authenticate(user=admin)
        c.post(f"/api/dossiers/{d.id}/add_protocol/", {"protocol_id": str(p.id)}, format="json")
        r2 = c.post(f"/api/dossiers/{d.id}/add_protocol/", {"protocol_id": str(p.id)}, format="json")
        assert r2.status_code == status.HTTP_400_BAD_REQUEST
        rid = uuid.uuid4()
        r3 = c.delete(f"/api/dossiers/{d.id}/remove_protocol/{rid}/")
        assert r3.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_folder_forbidden(self, operator, admin, ou):
        d = Dossier.objects.create(
            title="RF",
            identifier="RF-1",
            created_by=admin,
            responsible=admin,
        )
        DossierPermission.objects.create(dossier=d, user=operator, can_read=True, can_write=False)
        c = APIClient()
        c.force_authenticate(user=operator)
        r = c.post(f"/api/dossiers/{d.id}/remove_folder/", {"folder_id": str(uuid.uuid4())}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN
