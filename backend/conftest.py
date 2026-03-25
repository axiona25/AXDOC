import pytest
from rest_framework.test import APIClient
from apps.users.models import User


@pytest.fixture(autouse=True)
def default_tenant(db):
    from apps.organizations.models import Tenant

    Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    """Factory per creare utenti di test."""

    def _create_user(
        email="user@test.com",
        password="TestPass123!",
        first_name="Test",
        last_name="User",
        role="OPERATOR",
        must_change_password=False,
        **kwargs,
    ):
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            must_change_password=must_change_password,
            **kwargs,
        )
        return user

    return _create_user
