# Copertura: audit/* FASE 35D.3
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.audit.models import SecurityIncident

User = get_user_model()


@pytest.mark.django_db
class TestAuditFinal:
    def test_security_incident_str(self):
        u = User.objects.create_user(
            email="aud@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="U",
        )
        ev = SecurityIncident.objects.create(
            title="Test incident",
            description="Desc",
            severity="low",
            category="other",
            detected_at=timezone.now(),
            reported_by=u,
        )
        assert "Test incident" in str(ev)
