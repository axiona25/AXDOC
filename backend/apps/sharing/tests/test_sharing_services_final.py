# FASE 35E.1 — Copertura: sharing/services.py
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.documents.models import Document, Folder
from apps.organizations.models import Tenant
from apps.sharing.services import check_share_password, create_share_link
from apps.protocols.models import Protocol, ProtocolCounter
from apps.organizations.models import OrganizationalUnit

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.mark.django_db
class TestSharingServicesFinal:
    def test_create_internal_notifies_and_audit(self, tenant):
        u1 = User.objects.create_user(
            email="ssf1@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        u2 = User.objects.create_user(
            email="ssf2@test.com",
            password="TestPass123!",
            first_name="C",
            last_name="D",
        )
        folder = Folder.objects.create(name="F", tenant=tenant, created_by=u1)
        doc = Document.objects.create(title="D", folder=folder, created_by=u1, owner=u1)
        req = MagicMock()
        req.user = u1
        req.tenant = tenant
        req.META = {"REMOTE_ADDR": "127.0.0.1"}
        with patch("apps.notifications.services.NotificationService.notify_document_shared") as n:
            sl, err = create_share_link(
                req,
                target_type="document",
                document=doc,
                recipient_type="internal",
                recipient_user=u2,
            )
        assert err is None
        assert n.called
        assert sl.id

    def test_create_external_email_error(self, tenant):
        u = User.objects.create_user(
            email="ssf3@test.com",
            password="TestPass123!",
            first_name="E",
            last_name="F",
        )
        ou = OrganizationalUnit.objects.create(name="O", code="O", tenant=tenant)
        y = timezone.now().year
        n = ProtocolCounter.get_next_number(ou, y)
        pid = f"{y}/{ou.code}/{n:04d}"
        p = Protocol.objects.create(
            number=n,
            year=y,
            organizational_unit=ou,
            protocol_id=pid,
            direction="in",
            subject="S",
            sender_receiver="SR",
            registered_at=timezone.now(),
            registered_by=u,
            status="active",
            protocol_number=pid,
            protocol_date=timezone.now(),
            created_by=u,
            tenant=tenant,
        )
        req = MagicMock()
        req.user = u
        req.tenant = None
        with patch("apps.sharing.services.send_share_email", side_effect=RuntimeError("mail")):
            sl, err = create_share_link(
                req,
                target_type="protocol",
                protocol=p,
                recipient_type="external",
                recipient_email="ext@test.com",
            )
        assert err is not None

    def test_create_tenant_from_document_when_no_request_tenant(self, tenant):
        u = User.objects.create_user(
            email="ssf4@test.com",
            password="TestPass123!",
            first_name="G",
            last_name="H",
        )
        folder = Folder.objects.create(name="F2", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="D2", folder=folder, created_by=u, owner=u, tenant=tenant)
        req = MagicMock()
        req.user = u
        req.tenant = None
        req.META = {"REMOTE_ADDR": "127.0.0.1"}
        with patch("apps.sharing.services.send_share_email"):
            sl, err = create_share_link(
                req,
                target_type="document",
                document=doc,
                recipient_type="external",
                recipient_email="x@y.com",
            )
        assert sl.tenant_id == tenant.id
        assert err is None

    def test_check_share_password(self, tenant):
        u = User.objects.create_user(
            email="ssf5@test.com",
            password="TestPass123!",
            first_name="I",
            last_name="J",
        )
        folder = Folder.objects.create(name="F3", tenant=tenant, created_by=u)
        doc = Document.objects.create(title="D3", folder=folder, created_by=u, owner=u)
        from apps.sharing.models import ShareLink

        sl = ShareLink.objects.create(
            tenant=tenant,
            target_type="document",
            document=doc,
            shared_by=u,
            recipient_type="external",
            recipient_email="z@z.com",
            password_protected=True,
        )
        from django.contrib.auth.hashers import make_password

        sl.access_password = make_password("secret12")
        sl.save(update_fields=["access_password"])
        assert check_share_password(sl, "secret12") is True
        assert check_share_password(sl, "wrong") is False
