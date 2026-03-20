"""Test modelli e validazione metadati."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.metadata.models import MetadataStructure, MetadataField
from apps.metadata.validators import validate_metadata_values

User = get_user_model()


class MetadataStructureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="Test123!",
            first_name="Admin",
            last_name="User",
            role="ADMIN",
        )
        self.structure = MetadataStructure.objects.create(
            name="Contratto",
            description="Struttura contratti",
            created_by=self.user,
        )
        MetadataField.objects.create(
            structure=self.structure,
            name="fornitore",
            label="Fornitore",
            field_type="text",
            is_required=True,
            order=0,
        )
        MetadataField.objects.create(
            structure=self.structure,
            name="valore",
            label="Valore",
            field_type="number",
            is_required=False,
            order=1,
            validation_rules={"min": 0, "max": 1000000},
        )
        MetadataField.objects.create(
            structure=self.structure,
            name="tipologia",
            label="Tipologia",
            field_type="select",
            order=2,
            options=[{"value": "A", "label": "Opzione A"}, {"value": "B", "label": "Opzione B"}],
        )

    def test_validate_required_missing(self):
        errors = validate_metadata_values(self.structure, {})
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["field"], "fornitore")
        self.assertIn("obbligatorio", errors[0]["message"].lower())

    def test_validate_select_invalid_value(self):
        errors = validate_metadata_values(
            self.structure,
            {"fornitore": "Acme", "tipologia": "X"},
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["field"], "tipologia")

    def test_validate_number_out_of_range(self):
        errors = validate_metadata_values(
            self.structure,
            {"fornitore": "Acme", "valore": -10},
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["field"], "valore")

    def test_validate_valid_values(self):
        errors = validate_metadata_values(
            self.structure,
            {"fornitore": "Acme", "valore": 100, "tipologia": "A"},
        )
        self.assertEqual(len(errors), 0)

    def test_structure_validate_metadata_method(self):
        errors = self.structure.validate_metadata({"fornitore": ""})
        self.assertEqual(len(errors), 1)
