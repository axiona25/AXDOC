# Copertura: metadata/* FASE 35D.3
import uuid

import pytest

from apps.metadata.models import MetadataStructure
from apps.metadata.validators import validate_metadata_values


@pytest.mark.django_db
class TestMetadataFinal:
    def test_metadata_structure_str(self):
        ms = MetadataStructure.objects.create(name=f"Meta-{uuid.uuid4().hex[:8]}")
        assert str(ms) == ms.name

    def test_validate_empty(self):
        ms = MetadataStructure.objects.create(name=f"V-{uuid.uuid4().hex[:8]}")
        assert validate_metadata_values(ms, {}) == []
