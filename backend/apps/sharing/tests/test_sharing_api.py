"""
Test API condivisione FASE 11.
"""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from apps.sharing.models import ShareLink
from apps.documents.models import Document, DocumentPermission, DocumentVersion, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership
from apps.protocols.models import Protocol

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ou(db):
    return OrganizationalUnit.objects.create(name="IT", code="IT")


@pytest.fixture
def user_sharer(db, ou):
    u = User.objects.create_user(email="sharer@test.com", password="test")
    u.role = "OPERATOR"
    u.save()
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def user_recipient(db, ou):
    u = User.objects.create_user(email="recipient@test.com", password="test")
    u.role = "OPERATOR"
    u.save()
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def doc(user_sharer, db):
    f = Folder.objects.create(name="F")
    return Document.objects.create(
        title="Doc condiviso",
        folder=f,
        created_by=user_sharer,
        status=Document.STATUS_APPROVED,
    )


@pytest.fixture
def doc_version(doc, user_sharer):
    return DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        created_by=user_sharer,
        is_current=True,
    )


@pytest.fixture
def protocol(ou, user_sharer, db):
    return Protocol.objects.create(
        organizational_unit=ou,
        direction="out",
        subject="Protocollo test",
        registered_by=user_sharer,
        created_by=user_sharer,
    )


@pytest.mark.django_db
class TestDocumentShare:
    def test_share_document_internal_creates_permission(self, api_client, user_sharer, user_recipient, doc):
        api_client.force_authenticate(user=user_sharer)
        r = api_client.post(
            f"/api/documents/{doc.id}/share/",
            {
                "recipient_type": "internal",
                "recipient_user_id": str(user_recipient.id),
                "can_download": True,
                "expires_in_days": 7,
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        data = r.json()
        assert "share_link_id" in data
        assert "token" in data
        assert "url" in data
        assert DocumentPermission.objects.filter(document=doc, user=user_recipient, can_read=True).exists()
        share = ShareLink.objects.get(id=data["share_link_id"])
        assert share.recipient_type == "internal"
        assert share.recipient_user_id == user_recipient.id

    @patch("apps.sharing.emails.send_mail")
    def test_share_document_external_sends_email(self, mock_send, api_client, user_sharer, doc):
        api_client.force_authenticate(user=user_sharer)
        r = api_client.post(
            f"/api/documents/{doc.id}/share/",
            {
                "recipient_type": "external",
                "recipient_email": "external@example.com",
                "recipient_name": "Mario Rossi",
                "can_download": True,
                "expires_in_days": 1,
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        data = r.json()
        assert data["token"]
        share = ShareLink.objects.get(token=data["token"])
        assert share.recipient_email == "external@example.com"
        assert share.recipient_name == "Mario Rossi"
        mock_send.assert_called_once()

    def test_shares_list_document(self, api_client, user_sharer, user_recipient, doc):
        api_client.force_authenticate(user=user_sharer)
        ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="internal",
            recipient_user=user_recipient,
        )
        r = api_client.get(f"/api/documents/{doc.id}/shares/")
        assert r.status_code == 200
        assert len(r.json()) >= 1


@pytest.mark.django_db
class TestProtocolShare:
    @patch("apps.sharing.emails.send_mail")
    def test_share_protocol_external(self, mock_send, api_client, user_sharer, protocol):
        api_client.force_authenticate(user=user_sharer)
        r = api_client.post(
            f"/api/protocols/{protocol.id}/share/",
            {
                "recipient_type": "external",
                "recipient_email": "proto@ext.com",
                "can_download": True,
            },
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED
        share = ShareLink.objects.get(protocol=protocol)
        assert share.target_type == "protocol"


@pytest.mark.django_db
class TestPublicShareAccess:
    def test_public_share_valid_returns_data(self, api_client, user_sharer, doc):
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            password_protected=False,
        )
        r = api_client.get(f"/api/public/share/{share.token}/")
        assert r.status_code == 200
        data = r.json()
        assert data["document"]["title"] == doc.title
        assert data["shared_by"]["email"] == user_sharer.email
        assert data["can_download"] is True
        share.refresh_from_db()
        assert share.access_count == 1

    def test_public_share_expired_returns_410(self, api_client, user_sharer, doc):
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            expires_at=timezone.now() - timedelta(days=1),
        )
        r = api_client.get(f"/api/public/share/{share.token}/")
        assert r.status_code == status.HTTP_410_GONE
        assert "non è più valido" in (r.json().get("detail") or "")

    def test_public_share_revoked_returns_410(self, api_client, user_sharer, doc):
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            is_active=False,
        )
        r = api_client.get(f"/api/public/share/{share.token}/")
        assert r.status_code == status.HTTP_410_GONE

    def test_public_share_max_accesses_returns_410(self, api_client, user_sharer, doc):
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            max_accesses=1,
            access_count=1,
        )
        r = api_client.get(f"/api/public/share/{share.token}/")
        assert r.status_code == status.HTTP_410_GONE

    def test_public_share_password_required_returns_401(self, api_client, user_sharer, doc):
        from django.contrib.auth.hashers import make_password
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            password_protected=True,
            access_password=make_password("secret123"),
        )
        r = api_client.get(f"/api/public/share/{share.token}/")
        assert r.status_code == status.HTTP_401_UNAUTHORIZED
        assert r.json().get("requires_password") is True

    def test_verify_password_wrong_returns_401(self, api_client, user_sharer, doc):
        from django.contrib.auth.hashers import make_password
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            password_protected=True,
            access_password=make_password("secret123"),
        )
        r = api_client.post(
            f"/api/public/share/{share.token}/verify_password/",
            {"password": "wrong"},
            format="json",
        )
        assert r.status_code == status.HTTP_401_UNAUTHORIZED
        assert r.json().get("valid") is False

    def test_verify_password_correct_returns_data(self, api_client, user_sharer, doc):
        from django.contrib.auth.hashers import make_password
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            password_protected=True,
            access_password=make_password("secret123"),
        )
        r = api_client.post(
            f"/api/public/share/{share.token}/verify_password/",
            {"password": "secret123"},
            format="json",
        )
        assert r.status_code == 200
        assert r.json().get("valid") is True
        assert "data" in r.json()

    def test_download_without_can_download_returns_403(self, api_client, user_sharer, doc):
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="external",
            recipient_email="x@y.com",
            can_download=False,
        )
        r = api_client.get(f"/api/public/share/{share.token}/download/")
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_revoke_share(self, api_client, user_sharer, user_recipient, doc):
        share = ShareLink.objects.create(
            target_type="document",
            document=doc,
            shared_by=user_sharer,
            recipient_type="internal",
            recipient_user=user_recipient,
        )
        DocumentPermission.objects.create(document=doc, user=user_recipient, can_read=True)
        api_client.force_authenticate(user=user_sharer)
        r = api_client.post(f"/api/sharing/{share.id}/revoke/")
        assert r.status_code == 200
        share.refresh_from_db()
        assert share.is_active is False
        assert not DocumentPermission.objects.filter(document=doc, user=user_recipient).exists()
