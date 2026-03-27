"""Test API strutture metadati."""
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.metadata.models import MetadataStructure, MetadataField, MetadataStructureOU
from apps.organizations.models import OrganizationalUnit
from apps.documents.models import Document, Folder

User = get_user_model()


class MetadataStructureAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.operator = User.objects.create_user(
            email="op@test.com",
            password="Op123!",
            first_name="Op",
            last_name="User",
            role="OPERATOR",
        )
        self.structure = MetadataStructure.objects.create(
            name="Contratto",
            description="Test",
            created_by=self.admin,
        )
        MetadataField.objects.create(
            structure=self.structure,
            name="fornitore",
            label="Fornitore",
            field_type="text",
            is_required=True,
            order=0,
        )

    def test_list_structures_authenticated(self):
        self.client.force_authenticate(user=self.operator)
        r = self.client.get("/api/metadata/structures/")
        self.assertEqual(r.status_code, 200)
        results = r.data.get("results", r.data) if isinstance(r.data, dict) else r.data
        self.assertIsInstance(results, list)

    def test_create_structure_admin_only(self):
        self.client.force_authenticate(user=self.operator)
        r = self.client.post(
            "/api/metadata/structures/",
            {"name": "Nuova", "description": "Desc", "fields": []},
            format="json",
        )
        self.assertEqual(r.status_code, 403)

    def test_create_structure_with_fields(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            "/api/metadata/structures/",
            {
                "name": "Fattura",
                "description": "Struttura fatture",
                "fields": [
                    {"name": "numero", "label": "Numero", "field_type": "text", "is_required": True, "order": 0},
                    {"name": "importo", "label": "Importo", "field_type": "number", "validation_rules": {"min": 0}, "order": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["name"], "Fattura")
        self.assertEqual(len(r.data["fields"]), 2)

    def test_validate_endpoint_required_missing(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            f"/api/metadata/structures/{self.structure.id}/validate/",
            {"values": {}},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["valid"])
        self.assertEqual(len(r.data["errors"]), 1)

    def test_validate_endpoint_valid_values(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            f"/api/metadata/structures/{self.structure.id}/validate/",
            {"values": {"fornitore": "Acme"}},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["valid"])
        self.assertEqual(len(r.data["errors"]), 0)

    def test_validate_endpoint_number_range(self):
        MetadataField.objects.create(
            structure=self.structure,
            name="valore",
            label="Valore",
            field_type="number",
            order=1,
            validation_rules={"min": 0, "max": 100},
        )
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            f"/api/metadata/structures/{self.structure.id}/validate/",
            {"values": {"fornitore": "Acme", "valore": -5}},
            format="json",
        )
        self.assertFalse(r.data["valid"])
        self.assertTrue(any(e["field"] == "valore" for e in r.data["errors"]))

    def test_usable_by_me_filter(self):
        ou = OrganizationalUnit.objects.create(name="OU1", code="OU1", created_by=self.admin)
        from apps.organizations.models import OrganizationalUnitMembership
        OrganizationalUnitMembership.objects.create(
            user=self.operator,
            organizational_unit=ou,
            role="OPERATOR",
        )
        struct2 = MetadataStructure.objects.create(name="SoloOU", created_by=self.admin)
        MetadataStructureOU.objects.create(structure=struct2, organizational_unit=ou)
        self.client.force_authenticate(user=self.operator)
        r = self.client.get("/api/metadata/structures/?usable_by_me=true")
        self.assertEqual(r.status_code, 200)
        results = r.data.get("results", r.data) if isinstance(r.data, dict) else r.data
        names = [s["name"] for s in results]
        self.assertIn("Contratto", names)  # no OU restriction = visible to all
        self.assertIn("SoloOU", names)  # operator is in ou

    def test_destroy_with_documents_returns_400(self):
        folder = Folder.objects.create(name="F", created_by=self.admin)
        Document.objects.create(
            title="Doc",
            folder=folder,
            metadata_structure=self.structure,
            created_by=self.admin,
        )
        self.client.force_authenticate(user=self.admin)
        r = self.client.delete(f"/api/metadata/structures/{self.structure.id}/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("documenti", r.data["detail"])

    def test_update_field_type_with_documents_returns_400(self):
        folder = Folder.objects.create(name="F", created_by=self.admin)
        Document.objects.create(
            title="Doc",
            folder=folder,
            metadata_structure=self.structure,
            created_by=self.admin,
        )
        self.client.force_authenticate(user=self.admin)
        fid = self.structure.fields.first().id
        r = self.client.patch(
            f"/api/metadata/structures/{self.structure.id}/",
            {"fields": [{"id": str(fid), "name": "fornitore", "label": "Fornitore", "field_type": "textarea", "is_required": True, "order": 0}]},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("tipo", r.data["detail"])

    def test_list_applicable_to_and_is_active_filters(self):
        MetadataStructure.objects.create(name="ApplicableDocOnly", created_by=self.admin)
        self.client.force_authenticate(user=self.operator)
        r = self.client.get("/api/metadata/structures/", {"applicable_to": "document", "is_active": "true"})
        self.assertEqual(r.status_code, 200)
        results = r.data.get("results", r.data) if isinstance(r.data, dict) else r.data
        names = {s["name"] for s in results}
        self.assertIn("Contratto", names)

    def test_documents_action_lists_linked_documents(self):
        folder = Folder.objects.create(name="FMetaDocs", created_by=self.admin)
        Document.objects.create(
            title="Linked meta doc",
            folder=folder,
            metadata_structure=self.structure,
            created_by=self.admin,
        )
        self.client.force_authenticate(user=self.operator)
        r = self.client.get(f"/api/metadata/structures/{self.structure.id}/documents/")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.data, list)
        self.assertGreaterEqual(len(r.data), 1)

    def test_destroy_without_linked_documents_soft_deletes(self):
        orphan = MetadataStructure.objects.create(name="OrphanStructure353", created_by=self.admin)
        self.client.force_authenticate(user=self.admin)
        r = self.client.delete(f"/api/metadata/structures/{orphan.id}/")
        self.assertEqual(r.status_code, 204)
        orphan.refresh_from_db()
        self.assertFalse(orphan.is_active)

    def test_patch_structure_without_linked_documents(self):
        s = MetadataStructure.objects.create(name="PatchOnly353", description="Old", created_by=self.admin)
        MetadataField.objects.create(
            structure=s, name="pf", label="Pf", field_type="text", is_required=False, order=0
        )
        self.client.force_authenticate(user=self.admin)
        r = self.client.patch(f"/api/metadata/structures/{s.id}/", {"description": "New desc"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data.get("description"), "New desc")
