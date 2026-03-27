# FASE 35E.1 — Copertura: admin_panel/models.py
from unittest.mock import patch

import pytest

from apps.admin_panel.models import SystemLicense, SystemSettings
from apps.organizations.models import Tenant


@pytest.mark.django_db
class TestAdminModelsFinal:
    def test_system_license_str_and_feature(self):
        lic, _ = SystemLicense.objects.update_or_create(
            pk=1,
            defaults={"organization_name": "Org Test", "features_enabled": {"mfa": True}},
        )
        assert "Org" in str(lic)
        assert SystemLicense.is_feature_enabled("mfa") is True
        assert SystemLicense.is_feature_enabled("missing") is False

    @patch("apps.organizations.middleware.get_current_tenant")
    def test_get_settings_with_tenant(self, mock_gt):
        t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
        mock_gt.return_value = t
        s = SystemSettings.get_settings()
        assert s is not None
