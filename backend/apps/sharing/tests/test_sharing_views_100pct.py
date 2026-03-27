"""Rami aggiuntivi views condivisione (IP, revoca, paginazione, pubblico, download)."""
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.documents.models import Document, DocumentPermission, DocumentVersion, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.protocols.models import Protocol
from apps.sharing.models import ShareAccessLog, ShareLink
from apps.sharing.views import ShareLinkViewSet

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
    return OrganizationalUnit.objects.create(name="Sh100 OU", code=f"S{uuid.uuid4().hex[:5]}", tenant=tenant)


@pytest.fixture
def owner_and_peer(db, tenant, ou):
    owner = User.objects.create_user(
        email=f"shr-own-{uuid.uuid4().hex[:8]}@t.com",
        password="Test123!",
        role="OPERATOR",
        first_name="O",
        last_name="W",
    )
    owner.tenant = tenant
    owner.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=owner, organizational_unit=ou, role="OPERATOR")
    peer = User.objects.create_user(
        email=f"shr-peer-{uuid.uuid4().hex[:8]}@t.com",
        password="Test123!",
        role="OPERATOR",
        first_name="P",
        last_name="R",
    )
    peer.tenant = tenant
    peer.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=peer, organizational_unit=ou, role="OPERATOR")
    return owner, peer


@pytest.fixture
def folder_doc(db, tenant, owner_and_peer):
    owner, _ = owner_and_peer
    folder = Folder.objects.create(name="ShF", tenant=tenant, created_by=owner)
    doc = Document.objects.create(
        title="Sh doc",
        tenant=tenant,
        folder=folder,
        created_by=owner,
        owner=owner,
    )
    return folder, doc


@pytest.mark.django_db
class TestSharingViewsCoverage:
    def test_public_view_logs_x_forwarded_for_ip(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="x@y.z",
            token=f"xff-{uuid.uuid4().hex}",
        )
        c = APIClient()
        r = c.get(
            f"/api/public/share/{sl.token}/",
            HTTP_X_FORWARDED_FOR="203.0.113.9, 10.0.0.1",
        )
        assert r.status_code == 200
        log = ShareAccessLog.objects.filter(share_link=sl).order_by("-id").first()
        assert log and log.ip_address == "203.0.113.9"

    def test_revoke_forbidden_non_owner_when_queryset_allows_object(self, owner_and_peer, tenant, folder_doc):
        owner, peer = owner_and_peer
        _, doc = folder_doc
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="ext@e.e",
        )
        c = APIClient()
        c.force_authenticate(user=peer)
        with patch.object(
            ShareLinkViewSet,
            "get_queryset",
            return_value=ShareLink.objects.filter(pk=sl.pk),
        ):
            r = c.post(f"/api/sharing/{sl.id}/revoke/")
        assert r.status_code == 403

    def test_revoke_internal_deletes_document_permission(self, owner_and_peer, tenant, folder_doc):
        owner, peer = owner_and_peer
        _, doc = folder_doc
        DocumentPermission.objects.create(document=doc, user=peer, can_read=True)
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="internal",
            recipient_user=peer,
        )
        c = APIClient()
        c.force_authenticate(user=owner)
        r = c.post(f"/api/sharing/{sl.id}/revoke/")
        assert r.status_code == 200
        assert not DocumentPermission.objects.filter(document=doc, user=peer).exists()

    def test_my_shared_paginated_branch(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="pag@e.e",
        )
        factory = APIRequestFactory()
        request = factory.get("/api/sharing/my_shared/")
        force_authenticate(request, user=owner)
        with patch.object(ShareLinkViewSet, "paginate_queryset", return_value=[sl]):
            with patch.object(
                ShareLinkViewSet,
                "get_paginated_response",
                return_value=Response({"count": 1, "results": []}),
            ):
                view = ShareLinkViewSet.as_view(actions={"get": "my_shared"})
                resp = view(request)
                assert resp.status_code == 200

    def test_public_get_password_required(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="pw@e.e",
            token=f"pp-{uuid.uuid4().hex}",
            password_protected=True,
            access_password="hashed",
        )
        r = APIClient().get(f"/api/public/share/{sl.token}/")
        assert r.status_code == 401
        assert r.json().get("requires_password") is True

    def test_public_download_forbidden_when_can_download_false(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="nodl@e.e",
            token=f"ndl-{uuid.uuid4().hex}",
            can_download=False,
        )
        r = APIClient().get(f"/api/public/share/{sl.token}/download/")
        assert r.status_code == 403

    def test_public_download_file_open_oserror(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="x.txt",
            file_type="text/plain",
            file_size=1,
            created_by=owner,
            is_current=True,
        )
        v.file.save("x.txt", SimpleUploadedFile("x.txt", b"x", content_type="text/plain"), save=True)
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="err@e.e",
            token=f"err-{uuid.uuid4().hex}",
        )
        with patch.object(FieldFile, "open", side_effect=OSError("no file")):
            r = APIClient().get(f"/api/public/share/{sl.token}/download/")
            assert r.status_code == 404

    def test_public_download_protocol_via_document_version(self, owner_and_peer, tenant, folder_doc, ou):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_name="p.txt",
            file_type="text/plain",
            file_size=2,
            created_by=owner,
            is_current=True,
        )
        v.file.save("p.txt", SimpleUploadedFile("p.txt", b"ab", content_type="text/plain"), save=True)
        proto = Protocol.objects.create(
            tenant=tenant,
            organizational_unit=ou,
            document=doc,
            direction="in",
            created_by=owner,
        )
        sl = ShareLink.objects.create(
            target_type="protocol",
            protocol=proto,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="prot@e.e",
            token=f"pr-{uuid.uuid4().hex}",
        )
        r = APIClient().get(f"/api/public/share/{sl.token}/download/")
        assert r.status_code == 200

    def test_my_shared_real_pagination(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        for i in range(3):
            ShareLink.objects.create(
                target_type="document",
                document=doc,
                tenant=tenant,
                shared_by=owner,
                recipient_type="external",
                recipient_email=f"p{i}@e.e",
            )
        c = APIClient()
        c.force_authenticate(user=owner)
        r = c.get("/api/sharing/my_shared/", {"page_size": 1})
        assert r.status_code == 200
        body = r.json()
        assert "results" in body and len(body["results"]) == 1

    def test_my_shared_without_pagination_returns_plain_list(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="plain@e.e",
        )
        c = APIClient()
        c.force_authenticate(user=owner)
        with patch.object(ShareLinkViewSet, "paginate_queryset", return_value=None):
            r = c.get("/api/sharing/my_shared/")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list) and len(body) >= 1

    def test_verify_password_not_found_and_gone(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        c = APIClient()
        assert c.post("/api/public/share/bad-token/verify_password/", {"password": "x"}, format="json").status_code == 404
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="gone2@e.e",
            token=f"vg-{uuid.uuid4().hex}",
            is_active=False,
        )
        assert c.post(
            f"/api/public/share/{sl.token}/verify_password/",
            {"password": "x"},
            format="json",
        ).status_code == 410

    def test_public_download_not_found_gone_password(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        c = APIClient()
        assert c.get("/api/public/share/missing-tok/download/").status_code == 404
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="g3@e.e",
            token=f"dlg-{uuid.uuid4().hex}",
            is_active=False,
        )
        assert c.get(f"/api/public/share/{sl.token}/download/").status_code == 410
        sl2 = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="pwd@e.e",
            token=f"dlp-{uuid.uuid4().hex}",
            password_protected=True,
            access_password="x",
            can_download=True,
        )
        assert c.get(f"/api/public/share/{sl2.token}/download/").status_code == 401

    def test_public_download_document_without_file(self, owner_and_peer, tenant, folder_doc):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        DocumentVersion.objects.filter(document=doc, is_current=True).delete()
        sl = ShareLink.objects.create(
            target_type="document",
            document=doc,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="nof@e.e",
            token=f"nf-{uuid.uuid4().hex}",
        )
        assert APIClient().get(f"/api/public/share/{sl.token}/download/").status_code == 404

    def test_public_download_protocol_file_open_fails(self, owner_and_peer, tenant, folder_doc, ou):
        owner, _ = owner_and_peer
        _, doc = folder_doc
        v = DocumentVersion.objects.create(
            document=doc,
            version_number=99,
            file_name="pf.txt",
            file_type="text/plain",
            file_size=2,
            created_by=owner,
            is_current=True,
        )
        v.file.save("pf.txt", SimpleUploadedFile("pf.txt", b"ab", content_type="text/plain"), save=True)
        proto = Protocol.objects.create(
            tenant=tenant,
            organizational_unit=ou,
            document=doc,
            direction="in",
            created_by=owner,
        )
        sl = ShareLink.objects.create(
            target_type="protocol",
            protocol=proto,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="pe@e.e",
            token=f"pfe-{uuid.uuid4().hex}",
        )
        with patch.object(FieldFile, "open", side_effect=OSError("fail")):
            r = APIClient().get(f"/api/public/share/{sl.token}/download/")
            assert r.status_code == 404

    def test_public_download_no_document_nor_protocol(self, owner_and_peer, tenant):
        owner, _ = owner_and_peer
        sl = ShareLink.objects.create(
            target_type="document",
            document=None,
            protocol=None,
            tenant=tenant,
            shared_by=owner,
            recipient_type="external",
            recipient_email="orph@e.e",
            token=f"or-{uuid.uuid4().hex}",
        )
        assert APIClient().get(f"/api/public/share/{sl.token}/download/").status_code == 404
