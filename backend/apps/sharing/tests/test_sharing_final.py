# Copertura: sharing/* FASE 35D.3
import pytest
from django.contrib.auth import get_user_model

from apps.documents.models import Document, Folder
from apps.organizations.models import Tenant
from apps.sharing.models import ShareLink

User = get_user_model()


@pytest.mark.django_db
class TestSharingFinal:
    def test_share_link_str(self):
        t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "D", "plan": "enterprise"})
        u = User.objects.create_user(
            email="sh@test.com",
            password="TestPass123!",
            first_name="S",
            last_name="H",
        )
        u.tenant = t
        u.save(update_fields=["tenant"])
        folder = Folder.objects.create(name="SF", tenant=t, created_by=u)
        doc = Document.objects.create(title="D", folder=folder, created_by=u, owner=u)
        sl = ShareLink.objects.create(
            tenant=t,
            target_type="document",
            document=doc,
            shared_by=u,
            recipient_type="internal",
            recipient_user=u,
        )
        assert "document" in str(sl).lower()
