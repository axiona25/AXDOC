"""Campo tenant sui modelli documenti/protocolli."""
import pytest

from apps.documents.models import Document, Folder
from apps.organizations.models import Tenant


@pytest.mark.django_db
def test_document_has_tenant_field(user_factory):
    t = Tenant.objects.create(name="T", slug="doc-t", plan="starter")
    u = user_factory(email="d@test.com", tenant=t)
    d = Document.objects.create(title="X", created_by=u, owner=u, tenant=t)
    assert d.tenant_id == t.id


@pytest.mark.django_db
def test_folder_has_tenant_field(user_factory):
    t = Tenant.objects.create(name="T", slug="fold-t", plan="starter")
    u = user_factory(email="f@test.com", tenant=t)
    f = Folder.objects.create(name="Root", created_by=u, tenant=t)
    assert f.tenant_id == t.id
