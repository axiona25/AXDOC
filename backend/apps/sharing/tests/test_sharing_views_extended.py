"""Test estesi condivisione e URL pubbliche (FASE 33D)."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentVersion, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.sharing.models import ShareAccessLog, ShareLink

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="Shr OU", code="SHR", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="shr-ext-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="S",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="Shr F", tenant=tenant, created_by=admin_user)


@pytest.fixture
def document(db, tenant, admin_user, folder):
    return Document.objects.create(
        title="Share ext doc",
        tenant=tenant,
        folder=folder,
        created_by=admin_user,
        owner=admin_user,
    )


@pytest.mark.django_db
class TestSharingExtended:
    @patch("apps.sharing.services.send_share_email")
    def test_create_share_with_expiry(self, _mock_mail, admin_client, document):
        r = admin_client.post(
            f"/api/documents/{document.id}/share/",
            {
                "recipient_type": "external",
                "recipient_email": "e1@example.com",
                "expires_in_days": 7,
            },
            format="json",
        )
        assert r.status_code == 201

    @patch("apps.sharing.services.send_share_email")
    def test_create_share_with_password(self, _mock_mail, admin_client, document):
        r = admin_client.post(
            f"/api/documents/{document.id}/share/",
            {
                "recipient_type": "external",
                "recipient_email": "e2@example.com",
                "password": "secret123",
            },
            format="json",
        )
        assert r.status_code == 201

    def test_list_sharing_api(self, admin_client, admin_user, tenant, document):
        ShareLink.objects.create(
            target_type="document",
            document=document,
            tenant=tenant,
            shared_by=admin_user,
            recipient_type="external",
            recipient_email="x@y.z",
            token="list-token-abc",
        )
        r = admin_client.get("/api/sharing/")
        assert r.status_code == 200

    def test_my_shared(self, admin_client, admin_user, tenant, document):
        ShareLink.objects.create(
            target_type="document",
            document=document,
            tenant=tenant,
            shared_by=admin_user,
            recipient_type="external",
            recipient_email="my@shared.it",
        )
        r = admin_client.get("/api/sharing/my_shared/")
        assert r.status_code == 200

    def test_revoke_share(self, admin_client, admin_user, tenant, document):
        sl = ShareLink.objects.create(
            target_type="document",
            document=document,
            tenant=tenant,
            shared_by=admin_user,
            recipient_type="external",
            recipient_email="rev@oke.it",
        )
        r = admin_client.post(f"/api/sharing/{sl.id}/revoke/")
        assert r.status_code == 200
        sl.refresh_from_db()
        assert sl.is_active is False

    def test_access_share_public(self, admin_client, admin_user, tenant, document):
        sl = ShareLink.objects.create(
            target_type="document",
            document=document,
            tenant=tenant,
            shared_by=admin_user,
            recipient_type="external",
            recipient_email="pub@lic.it",
            token="public-token-xyz",
            password_protected=False,
        )
        c = APIClient()
        r = c.get("/api/public/share/public-token-xyz/")
        assert r.status_code == 200
        sl.refresh_from_db()
        assert sl.access_count >= 1
        assert ShareAccessLog.objects.filter(share_link=sl, action="view").exists()

    def test_public_share_not_found(self):
        r = APIClient().get("/api/public/share/does-not-exist/")
        assert r.status_code == 404

    def test_public_share_inactive_gone(self, admin_user, tenant, document):
        sl = ShareLink.objects.create(
            target_type="document",
            document=document,
            tenant=tenant,
            shared_by=admin_user,
            recipient_type="external",
            recipient_email="gone@it.it",
            token="gone-token-410",
            is_active=False,
        )
        r = APIClient().get(f"/api/public/share/{sl.token}/")
        assert r.status_code == 410

    def test_verify_password_wrong(self, admin_user, tenant, document):
        with patch("apps.sharing.services.send_share_email"):
            c = APIClient()
            c.force_authenticate(user=admin_user)
            c.post(
                f"/api/documents/{document.id}/share/",
                {
                    "recipient_type": "external",
                    "recipient_email": "vpw@it.it",
                    "password": "secret99",
                },
                format="json",
            )
        sl = ShareLink.objects.get(document=document, recipient_email="vpw@it.it")
        r = APIClient().post(
            f"/api/public/share/{sl.token}/verify_password/",
            {"password": "wrong"},
            format="json",
        )
        assert r.status_code == 401
        assert r.json().get("valid") is False

    @patch("apps.sharing.services.send_share_email")
    def test_verify_password_public(self, _mock_mail, admin_user, tenant, document):
        r_api = APIClient()
        r_api.force_authenticate(user=admin_user)
        r_api.post(
            f"/api/documents/{document.id}/share/",
            {
                "recipient_type": "external",
                "recipient_email": "pw@user.it",
                "password": "rightpass",
            },
            format="json",
        )
        sl = ShareLink.objects.get(document=document, recipient_email="pw@user.it")
        r = APIClient().post(
            f"/api/public/share/{sl.token}/verify_password/",
            {"password": "rightpass"},
            format="json",
        )
        assert r.status_code == 200
        assert r.json().get("valid") is True

    def test_list_shares_for_document(self, admin_client, document):
        r = admin_client.get(f"/api/documents/{document.id}/shares/")
        assert r.status_code == 200

    def test_public_download_with_file(self, admin_user, tenant, document):
        v = DocumentVersion.objects.create(
            document=document,
            version_number=1,
            file_name="s.txt",
            file_type="text/plain",
            file_size=3,
            created_by=admin_user,
            is_current=True,
        )
        v.file.save("s.txt", SimpleUploadedFile("s.txt", b"abc", content_type="text/plain"), save=True)
        sl = ShareLink.objects.create(
            target_type="document",
            document=document,
            tenant=tenant,
            shared_by=admin_user,
            recipient_type="external",
            recipient_email="dl@it.it",
            token="dl-token-1",
            can_download=True,
        )
        r = APIClient().get(f"/api/public/share/dl-token-1/download/")
        assert r.status_code == 200
