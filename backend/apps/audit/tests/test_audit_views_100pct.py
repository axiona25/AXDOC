"""Rami audit: filtro tenant, export detail non JSON, attività documento, target_id."""
import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.http import QueryDict
from rest_framework.test import APIClient

from apps.audit.views import _audit_export_queryset, _filter_audit_logs_by_tenant
from apps.authentication.models import AuditLog
from apps.documents.models import Document, Folder
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(
        slug="default",
        defaults={"name": "Organizzazione Default", "plan": "enterprise"},
    )
    return t


@pytest.mark.django_db
class TestAuditTenantFilterHelper:
    def test_superuser_no_filter(self, tenant):
        admin = User.objects.create_user(
            email=f"au-{uuid.uuid4().hex[:8]}@t.com",
            password="x",
            role="ADMIN",
            is_superuser=True,
        )
        qs = AuditLog.objects.all()
        req = SimpleNamespace(user=admin, tenant=tenant)
        out = _filter_audit_logs_by_tenant(qs, req)
        assert out is qs

    def test_no_tenant_returns_queryset_unchanged(self, tenant):
        u = User.objects.create_user(email=f"nt-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        u.is_superuser = False
        qs = AuditLog.objects.all()
        req = SimpleNamespace(user=u, tenant=None)
        assert _filter_audit_logs_by_tenant(qs, req) is qs

    def test_default_slug_includes_null_tenant_logs(self, tenant):
        assert tenant.slug == "default"
        other = Tenant.objects.create(name="Oth", slug=f"o-{uuid.uuid4().hex[:6]}", plan="starter")
        admin = User.objects.create_user(email=f"df-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        admin.is_superuser = False
        a_def = AuditLog.objects.create(user=admin, action="LOGIN", detail={}, tenant=tenant)
        a_null = AuditLog.objects.create(user=admin, action="LOGOUT", detail={}, tenant=None)
        a_other = AuditLog.objects.create(user=admin, action="USER_CREATED", detail={}, tenant=other)
        req = SimpleNamespace(user=admin, tenant=tenant)
        filt = _filter_audit_logs_by_tenant(AuditLog.objects.all(), req)
        assert set(filt.values_list("id", flat=True)) == {a_def.id, a_null.id}
        assert a_other.id not in filt.values_list("id", flat=True)

    def test_non_default_tenant_strict(self, tenant):
        other = Tenant.objects.create(name="Strict", slug=f"s-{uuid.uuid4().hex[:6]}", plan="starter")
        admin = User.objects.create_user(email=f"st-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        admin.is_superuser = False
        a_ok = AuditLog.objects.create(user=admin, action="LOGIN", detail={}, tenant=other)
        a_bad = AuditLog.objects.create(user=admin, action="LOGOUT", detail={}, tenant=tenant)
        req = SimpleNamespace(user=admin, tenant=other)
        filt = _filter_audit_logs_by_tenant(AuditLog.objects.all(), req)
        assert set(filt.values_list("id", flat=True)) == {a_ok.id}


@pytest.mark.django_db
def test_audit_export_queryset_non_admin_empty():
    op = User.objects.create_user(email=f"aeq-{uuid.uuid4().hex[:8]}@t.com", password="x", role="OPERATOR")
    req = SimpleNamespace(user=op, query_params=QueryDict())
    assert _audit_export_queryset(req).count() == 0


@pytest.mark.django_db
class TestAuditListAndExport:
    def test_list_target_id_filter(self, tenant):
        admin = User.objects.create_user(email=f"tid-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        ou = OrganizationalUnit.objects.create(name="AOU", code=f"A{uuid.uuid4().hex[:4]}", tenant=tenant)
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        folder = Folder.objects.create(name="AF", tenant=tenant, created_by=admin)
        doc = Document.objects.create(title="AD", tenant=tenant, folder=folder, created_by=admin, owner=admin)
        AuditLog.objects.create(
            user=admin,
            action="DOCUMENT_CREATED",
            detail={"document_id": str(doc.id)},
            tenant=tenant,
        )
        AuditLog.objects.create(user=admin, action="LOGIN", detail={}, tenant=tenant)
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get("/api/audit/", {"target_id": str(doc.id)})
        assert r.status_code == 200
        for row in r.json().get("results", []):
            assert row.get("detail", {}).get("document_id") == str(doc.id)

    def test_operator_sees_own_audit_list(self, tenant):
        op = User.objects.create_user(email=f"op-{uuid.uuid4().hex[:8]}@t.com", password="x", role="OPERATOR")
        op.tenant = tenant
        op.save(update_fields=["tenant"])
        AuditLog.objects.create(user=op, action="LOGIN", detail={}, tenant=tenant)
        c = APIClient()
        c.force_authenticate(user=op)
        r = c.get("/api/audit/")
        assert r.status_code == 200
        assert r.json().get("count", 0) >= 1

    def test_export_excel_detail_json_fallback(self, tenant):
        admin = User.objects.create_user(email=f"ex-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        ou = OrganizationalUnit.objects.create(name="EOU", code=f"E{uuid.uuid4().hex[:4]}", tenant=tenant)
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        AuditLog.objects.create(
            user=admin,
            action="LOGIN",
            detail={"trigger_bad": True, "ok": 1},
            tenant=tenant,
        )

        real = json.dumps

        def dumps_selective(obj, **kwargs):
            if isinstance(obj, dict) and obj.get("trigger_bad"):
                raise TypeError("not serializable")
            return real(obj, **kwargs)

        c = APIClient()
        c.force_authenticate(user=admin)
        with patch("apps.audit.views.json.dumps", side_effect=dumps_selective):
            r = c.get("/api/audit/export_excel/")
            assert r.status_code == 200

    def test_export_excel_with_query_filters(self, tenant):
        admin = User.objects.create_user(email=f"ef-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        ou = OrganizationalUnit.objects.create(name="FOU", code=f"F{uuid.uuid4().hex[:4]}", tenant=tenant)
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        other = User.objects.create_user(email=f"eo-{uuid.uuid4().hex[:8]}@t.com", password="x", role="OPERATOR")
        from django.utils import timezone

        day = timezone.now().date().isoformat()
        AuditLog.objects.create(user=other, action="LOGIN", detail={}, tenant=tenant)
        AuditLog.objects.create(user=admin, action="LOGOUT", detail={}, tenant=tenant)
        c = APIClient()
        c.force_authenticate(user=admin)
        r = c.get(
            "/api/audit/export_excel/",
            {"user_id": str(other.id), "action": "LOGIN", "date_from": day, "date_to": day},
        )
        assert r.status_code == 200

    def test_export_pdf_detail_json_fallback(self, tenant):
        admin = User.objects.create_user(email=f"pdf-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        ou = OrganizationalUnit.objects.create(name="POU", code=f"P{uuid.uuid4().hex[:4]}", tenant=tenant)
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        AuditLog.objects.create(
            user=admin,
            action="LOGIN",
            detail={"trigger_bad": True},
            tenant=tenant,
        )
        real = json.dumps

        def dumps_selective(obj, **kwargs):
            if isinstance(obj, dict) and obj.get("trigger_bad"):
                raise TypeError("x")
            return real(obj, **kwargs)

        c = APIClient()
        c.force_authenticate(user=admin)
        with patch("apps.audit.views.json.dumps", side_effect=dumps_selective):
            r = c.get("/api/audit/export_pdf/")
            assert r.status_code == 200


@pytest.mark.django_db
class TestDocumentActivityCoverage:
    def test_forbidden_without_document_access(self, tenant):
        admin = User.objects.create_user(email=f"own-{uuid.uuid4().hex[:8]}@t.com", password="x", role="ADMIN")
        admin.tenant = tenant
        admin.save(update_fields=["tenant"])
        op = User.objects.create_user(email=f"nop-{uuid.uuid4().hex[:8]}@t.com", password="x", role="OPERATOR")
        op.tenant = tenant
        op.save(update_fields=["tenant"])
        ou = OrganizationalUnit.objects.create(name="DOU", code=f"D{uuid.uuid4().hex[:4]}", tenant=tenant)
        OrganizationalUnitMembership.objects.create(user=admin, organizational_unit=ou, role="ADMIN")
        OrganizationalUnitMembership.objects.create(user=op, organizational_unit=ou, role="OPERATOR")
        folder = Folder.objects.create(name="Sec", tenant=tenant, created_by=admin)
        doc = Document.objects.create(
            title="Private",
            tenant=tenant,
            folder=folder,
            created_by=admin,
            owner=admin,
        )
        c = APIClient()
        c.force_authenticate(user=op)
        r = c.get(f"/api/audit/document/{doc.id}/")
        assert r.status_code == 403
