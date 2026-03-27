"""Copertura ramificazioni validate_metadata_values / _validate_field."""
import uuid

import pytest

from apps.metadata.models import MetadataField, MetadataStructure
from apps.metadata.validators import _looks_like_date, validate_metadata_values


@pytest.fixture
def structure(db):
    return MetadataStructure.objects.create(name=f"val-{uuid.uuid4().hex[:6]}")


@pytest.mark.django_db
class TestValidateMetadataValues:
    def test_empty_values_dict(self, structure):
        assert validate_metadata_values(structure, {}) == []

    def test_none_values_normalized(self, structure):
        assert validate_metadata_values(structure, None) == []

    def test_required_missing(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="r",
            label="R",
            field_type="text",
            is_required=True,
            order=0,
        )
        errs = validate_metadata_values(structure, {})
        assert any(e["field"] == "r" for e in errs)

    def test_required_empty_list_multiselect(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="m",
            label="M",
            field_type="multiselect",
            is_required=True,
            options=[{"value": "a", "label": "A"}],
            order=0,
        )
        errs = validate_metadata_values(structure, {"m": []})
        assert errs

    def test_number_invalid(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="n",
            label="N",
            field_type="number",
            order=0,
        )
        assert validate_metadata_values(structure, {"n": "x"})[0]["message"] == "Valore non numerico."

    def test_number_min_max(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="n",
            label="N",
            field_type="number",
            validation_rules={"min": 2, "max": 5},
            order=0,
        )
        assert "minimo" in validate_metadata_values(structure, {"n": 1})[0]["message"].lower()
        assert "massimo" in validate_metadata_values(structure, {"n": 9})[0]["message"].lower()

    def test_text_min_max_regex(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="t",
            label="T",
            field_type="text",
            validation_rules={"min_length": 5, "max_length": 10, "regex": r"^[A-Z]+$"},
            order=0,
        )
        assert validate_metadata_values(structure, {"t": "ab"})[0]["field"] == "t"
        assert validate_metadata_values(structure, {"t": "ABCDEFGHIJK"})[0]["field"] == "t"
        assert validate_metadata_values(structure, {"t": "Abcde"})[0]["message"] == "Formato non valido."

    def test_regex_invalid_pattern_skipped(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="t",
            label="T",
            field_type="text",
            validation_rules={"regex": "["},
            order=0,
        )
        assert validate_metadata_values(structure, {"t": "anything"}) == []

    def test_email_field_invalid(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="e",
            label="E",
            field_type="email",
            order=0,
        )
        assert validate_metadata_values(structure, {"e": "bad"})[0]["message"] == "Email non valida."

    def test_select_not_in_options(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="s",
            label="S",
            field_type="select",
            options=[{"value": "a", "label": "A"}],
            order=0,
        )
        assert validate_metadata_values(structure, {"s": "z"})[0]["message"] == "Valore non consentito."

    def test_multiselect_invalid_item(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="m",
            label="M",
            field_type="multiselect",
            options=[{"value": "a", "label": "A"}],
            order=0,
        )
        assert validate_metadata_values(structure, {"m": ["a", "z"]})[0]["message"].startswith("Uno")

    def test_multiselect_coerces_non_list(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="m",
            label="M",
            field_type="multiselect",
            options=[{"value": "a", "label": "A"}],
            order=0,
        )
        assert validate_metadata_values(structure, {"m": "a"}) == []

    def test_boolean_invalid(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="b",
            label="B",
            field_type="boolean",
            order=0,
        )
        assert validate_metadata_values(structure, {"b": "maybe"})[0]["message"].startswith("Valore booleano")

    def test_date_invalid(self, structure):
        MetadataField.objects.create(
            structure=structure,
            name="d",
            label="D",
            field_type="date",
            order=0,
        )
        assert validate_metadata_values(structure, {"d": "notadate"})[0]["message"] == "Data non valida."


def test_looks_like_date():
    assert _looks_like_date("")
    assert _looks_like_date("2024-01-01")
    assert _looks_like_date("nodash") is False
