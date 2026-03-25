"""Claim tenant_id nei JWT."""
import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.authentication.token_utils import issue_refresh_for_user


@pytest.mark.django_db
def test_jwt_token_contains_tenant_id(user_factory):
    from apps.organizations.models import Tenant

    t = Tenant.objects.create(name="JT", slug="jwt-t", plan="starter")
    u = user_factory(email="jwt@test.com", tenant=t)
    refresh = issue_refresh_for_user(u)
    access = AccessToken(str(refresh.access_token))
    assert access["tenant_id"] == str(t.id)


@pytest.mark.django_db
def test_jwt_token_without_tenant(user_factory):
    u = user_factory(email="nt@test.com")
    u.tenant = None
    u.save(update_fields=["tenant"])
    refresh = issue_refresh_for_user(u)
    access = AccessToken(str(refresh.access_token))
    assert "tenant_id" not in access or not access.get("tenant_id")
