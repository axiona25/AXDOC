"""Test token_utils JWT + refresh tenant (FASE 33B)."""
from unittest.mock import patch

import pytest
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.authentication.token_utils import AxdocTokenRefreshSerializer, issue_refresh_for_user
from apps.organizations.models import Tenant


@pytest.mark.django_db
def test_issue_refresh_calls_session_limit(user_factory):
    with patch("apps.authentication.session_limit.limit_concurrent_refresh_sessions") as m:
        u = user_factory(email="tu-limit@test.com")
        issue_refresh_for_user(u)
        m.assert_called_once_with(u)


@pytest.mark.django_db
def test_axdoc_refresh_serializer_propagates_tenant_id(user_factory):
    t = Tenant.objects.create(name="TokT", slug="tok-t", plan="starter")
    u = user_factory(email="tu-ser@test.com", tenant=t)
    refresh = RefreshToken.for_user(u)
    refresh["tenant_id"] = str(t.id)
    ser = AxdocTokenRefreshSerializer(data={"refresh": str(refresh)})
    assert ser.is_valid(), ser.errors
    access = AccessToken(ser.validated_data["access"])
    assert access["tenant_id"] == str(t.id)
