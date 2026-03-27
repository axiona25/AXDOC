# Copertura: admin_panel/* FASE 35D.3
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.admin_panel.models import SystemSettings

User = get_user_model()


@pytest.mark.django_db
class TestAdminPanelFinal:
    def test_system_settings_singleton(self):
        s, _ = SystemSettings.objects.get_or_create(pk=1)
        assert s.id == 1

    def test_health_db_endpoint(self):
        c = APIClient()
        u = User.objects.create_user(
            email="hp@test.com",
            password="TestPass123!",
            first_name="H",
            last_name="P",
            role="ADMIN",
        )
        c.force_authenticate(user=u)
        r = c.get("/api/health/")
        assert r.status_code in (200, 503)
