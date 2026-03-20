"""
Test metadati su Folder, Dossier, filtro applicable_to, AGID metadata. FASE 18.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.documents.models import Folder
from apps.dossiers.models import Dossier
from apps.metadata.models import MetadataStructure, MetadataField
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.metadata.agid_metadata import (
    get_agid_metadata_for_document,
    get_agid_metadata_for_dossier,
    AGID_DOCUMENT_METADATA,
    AGID_DOSSIER_METADATA,
)


class FolderMetadataTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.admin.is_staff = True
        self.admin.save()

    def test_folder_can_have_metadata_structure(self):
        folder = Folder.objects.create(name="Test Folder", created_by=self.admin)
        self.assertIsNone(folder.metadata_structure_id)
        self.assertEqual(folder.metadata_values, {})
        self.assertEqual(folder.validate_metadata({}), [])

    def test_folder_metadata_patch_api(self):
        folder = Folder.objects.create(name="Test", created_by=self.admin)
        structure = MetadataStructure.objects.create(
            name="Struttura Cartelle",
            is_active=True,
            applicable_to=["folder"],
        )
        MetadataField.objects.create(
            structure=structure,
            name="note",
            label="Note",
            field_type="text",
            is_required=False,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/folders/{folder.id}/metadata/",
            {"metadata_structure_id": str(structure.id), "metadata_values": {"note": "Una nota"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        folder.refresh_from_db()
        self.assertEqual(folder.metadata_structure_id, structure.id)
        self.assertEqual(folder.metadata_values.get("note"), "Una nota")


class DossierMetadataTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.admin.is_staff = True
        self.admin.save()

    def test_dossier_can_have_metadata_structure(self):
        dossier = Dossier.objects.create(
            title="Test Dossier",
            identifier="DOS-001",
            created_by=self.admin,
        )
        self.assertIsNone(dossier.metadata_structure_id)
        self.assertEqual(dossier.metadata_values, {})
        self.assertEqual(dossier.validate_metadata({}), [])

    def test_dossier_metadata_patch_api(self):
        dossier = Dossier.objects.create(
            title="Test Dossier",
            identifier="DOS-002",
            created_by=self.admin,
        )
        structure = MetadataStructure.objects.create(
            name="Struttura Fascicoli",
            is_active=True,
            applicable_to=["dossier"],
        )
        MetadataField.objects.create(
            structure=structure,
            name="rif",
            label="Riferimento",
            field_type="text",
            is_required=False,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/dossiers/{dossier.id}/metadata/",
            {"metadata_structure_id": str(structure.id), "metadata_values": {"rif": "RIF-001"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dossier.refresh_from_db()
        self.assertEqual(dossier.metadata_structure_id, structure.id)
        self.assertEqual(dossier.metadata_values.get("rif"), "RIF-001")


class ApplicableToFilterTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.client.force_authenticate(user=self.admin)

    def test_applicable_to_filter_documents_only(self):
        MetadataStructure.objects.create(name="Solo Documenti", is_active=True, applicable_to=["document"])
        MetadataStructure.objects.create(name="Solo Fascicoli", is_active=True, applicable_to=["dossier"])
        response = self.client.get("/api/metadata/structures/?applicable_to=document")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        names = [s["name"] for s in results]
        self.assertIn("Solo Documenti", names)
        self.assertNotIn("Solo Fascicoli", names)

    def test_applicable_to_filter_dossiers_only(self):
        MetadataStructure.objects.create(name="Solo Doc", is_active=True, applicable_to=["document"])
        MetadataStructure.objects.create(name="Solo Doss", is_active=True, applicable_to=["dossier"])
        response = self.client.get("/api/metadata/structures/?applicable_to=dossier")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        names = [s["name"] for s in results]
        self.assertIn("Solo Doss", names)
        self.assertNotIn("Solo Doc", names)


class AGIDMetadataTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.admin.save()

    def test_agid_metadata_document_has_required_fields(self):
        from apps.documents.models import Document
        doc = Document.objects.create(
            title="Doc AGID",
            created_by=self.admin,
            status="DRAFT",
        )
        meta = get_agid_metadata_for_document(doc)
        for key in ("identificativo", "data_creazione", "autore", "oggetto", "stato"):
            self.assertIn(key, meta, f"AGID document metadata deve contenere {key}")
        self.assertIn("identificativo", AGID_DOCUMENT_METADATA)

    def test_agid_metadata_dossier_has_required_fields(self):
        dossier = Dossier.objects.create(
            title="Fascicolo AGID",
            identifier="F-001",
            created_by=self.admin,
            responsible=self.admin,
        )
        meta = get_agid_metadata_for_dossier(dossier)
        for key in ("identificativo", "oggetto", "data_apertura", "responsabile", "stato", "indice_documenti"):
            self.assertIn(key, meta, f"AGID dossier metadata deve contenere {key}")
        self.assertIn("identificativo", AGID_DOSSIER_METADATA)
