"""Modello Tenant."""
import pytest
from django.core.management import call_command

from apps.organizations.models import Tenant, OrganizationalUnit


@pytest.mark.django_db
def test_create_tenant():
    t = Tenant.objects.create(name="Comune X", slug="comune-x", plan="professional")
    assert t.pk
    assert str(t) == "Comune X"


@pytest.mark.django_db
def test_tenant_slug_unique():
    Tenant.objects.create(name="A", slug="unique-slug", plan="starter")
    with pytest.raises(Exception):
        Tenant.objects.create(name="B", slug="unique-slug", plan="starter")


@pytest.mark.django_db
def test_default_tenant_command():
    OrganizationalUnit.objects.create(name="UO", code="UO1")
    call_command("create_default_tenant")
    t = Tenant.objects.get(slug="default")
    assert OrganizationalUnit.objects.filter(tenant=t).exists()
