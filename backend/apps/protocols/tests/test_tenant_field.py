import pytest

from apps.organizations.models import Tenant
from apps.protocols.models import Protocol


@pytest.mark.django_db
def test_protocol_has_tenant_field():
    t = Tenant.objects.create(name="T", slug="prot-t", plan="starter")
    p = Protocol.objects.create(tenant=t, subject="S")
    assert p.tenant_id == t.id
