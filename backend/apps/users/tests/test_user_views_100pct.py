# FASE 35.1 — Copertura users/views.py ≥95%
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.test import APIClient

from apps.documents.models import Document, DocumentPermission, Folder
from apps.dossiers.models import Dossier
from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.users.importers import UserImporter
from apps.users.models import ConsentRecord
from apps.users.views import UserViewSet

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="U100", code="U100", tenant=tenant)


@pytest.fixture
def admin_user(db, tenant, ou):
    u = User.objects.create_user(
        email="u100-adm@test.com",
        password="Admin123!",
        role="ADMIN",
        first_name="A",
        last_name="D",
        user_type="internal",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="ADMIN")
    return u


@pytest.fixture
def operator_user(db, tenant, ou):
    u = User.objects.create_user(
        email="u100-op@test.com",
        password="Op123456!",
        role="OPERATOR",
        first_name="O",
        last_name="P",
        user_type="internal",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, role="OPERATOR")
    return u


@pytest.fixture
def guest_user(db, tenant):
    u = User.objects.create_user(
        email="u100-guest@test.com",
        password="Guest123!",
        role="OPERATOR",
        first_name="G",
        last_name="U",
        user_type="guest",
    )
    u.tenant = tenant
    u.save(update_fields=["tenant"])
    return u


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def operator_client(operator_user):
    c = APIClient()
    c.force_authenticate(user=operator_user)
    return c


@pytest.fixture
def folder(db, tenant, admin_user):
    return Folder.objects.create(name="U100F", tenant=tenant, created_by=admin_user)


@pytest.mark.django_db
def test_get_import_permissions_helper():
    # Copre righe: 364-365
    v = UserViewSet()
    p = v._get_import_permissions()
    assert len(p) == 2


@pytest.mark.django_db
class TestUserViewsListFiltersAndSerializer:
    # Copre righe: 68-69, 104-107, 111-141, 146-153
    def test_list_filters_role_type_active_search_ou_unassigned(self, admin_client, admin_user, operator_user, ou):
        operator_user.first_name = "ZetaSearch"
        operator_user.save(update_fields=["first_name"])
        r = admin_client.get("/api/users/", {"role": "OPERATOR"})
        assert r.status_code == 200
        payload = r.json()
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
        if isinstance(rows, dict):
            rows = []
        assert any(str(operator_user.id) == str(x.get("id")) for x in rows) or "ZetaSearch" in str(payload)
        r2 = admin_client.get("/api/users/", {"user_type": "internal"})
        assert r2.status_code == 200
        r3 = admin_client.get("/api/users/", {"is_active": "true"})
        assert r3.status_code == 200
        r4 = admin_client.get("/api/users/", {"search": "ZetaSearch"})
        assert r4.status_code == 200
        r5 = admin_client.get("/api/users/", {"ou": str(ou.id)})
        assert r5.status_code == 200
        lone = User.objects.create_user(
            email="u100-lone@test.com",
            password="Lone123!",
            role="OPERATOR",
            first_name="L",
            last_name="One",
            user_type="internal",
        )
        lone.tenant = admin_user.tenant
        lone.save(update_fields=["tenant"])
        r6 = admin_client.get("/api/users/", {"unassigned": "true"})
        assert r6.status_code == 200

    def test_partial_update_second_get_object_not_found_uses_update_serializer(self, admin_client, admin_user, operator_user):
        state = {"n": 0}

        def _dual_get(view_self):
            state["n"] += 1
            if state["n"] == 1:
                return operator_user
            raise NotFound()

        with patch.object(UserViewSet, "get_object", _dual_get):
            r = admin_client.patch(
                f"/api/users/{operator_user.id}/",
                {"first_name": "X"},
                format="json",
            )
            assert r.status_code == 200

    def test_operator_self_patch_uses_profile_serializer_path(self, operator_client, operator_user):
        r = operator_client.patch(
            f"/api/users/{operator_user.id}/",
            {"first_name": "SelfProf"},
            format="json",
        )
        assert r.status_code == 200
        operator_user.refresh_from_db()
        assert operator_user.first_name == "SelfProf"

    def test_update_clears_prefetch_cache(self, admin_client, operator_user):
        real_perform = UserViewSet.perform_update

        def perform_with_prefetch(view_self, serializer):
            serializer.instance._prefetched_objects_cache = {"k": True}
            return real_perform(view_self, serializer)

        with patch.object(UserViewSet, "perform_update", perform_with_prefetch):
            r = admin_client.patch(
                f"/api/users/{operator_user.id}/",
                {"first_name": "Prefetch"},
                format="json",
            )
            assert r.status_code == 200


@pytest.mark.django_db
class TestUserViewsConsentsExportDestroy:
    # Copre righe: 161-193, 195-236, 144-153
    def test_my_consents_get_post_privacy_and_export(self, operator_client, operator_user):
        ConsentRecord.objects.create(
            user=operator_user,
            consent_type="privacy_policy",
            version="1",
            granted=True,
            ip_address="1.1.1.1",
        )
        r = operator_client.get("/api/users/my_consents/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        operator_client.credentials(HTTP_X_FORWARDED_FOR="203.0.113.1")
        r2 = operator_client.post(
            "/api/users/my_consents/",
            {"consent_type": "marketing", "version": "1", "granted": False},
            format="json",
        )
        assert r2.status_code == 201
        r3 = operator_client.get("/api/users/export_my_data/")
        assert r3.status_code == 200
        assert "attachment" in r3.get("Content-Disposition", "").lower()
        assert operator_user.email in r3.content.decode("utf-8")

    def test_destroy_soft_delete(self, admin_client, tenant):
        victim = User.objects.create_user(
            email=f"del-{uuid.uuid4().hex[:8]}@test.com",
            password="Del12345!",
            role="OPERATOR",
            user_type="internal",
        )
        victim.tenant = tenant
        victim.save(update_fields=["tenant"])
        oid = victim.id
        r = admin_client.delete(f"/api/users/{oid}/")
        assert r.status_code == 204
        victim.refresh_from_db()
        assert victim.is_deleted is True
        assert ".deleted_" in victim.email


@pytest.mark.django_db
class TestUserViewsAnonymizeCreateManualChangeType:
    # Copre righe: 238-266, 268-304, 306-323
    def test_change_type_guest_and_invalid(self, admin_client, operator_user):
        r = admin_client.post(f"/api/users/{operator_user.id}/change_type/", {"user_type": "guest"}, format="json")
        assert r.status_code == 200
        operator_user.refresh_from_db()
        assert operator_user.user_type == "guest"
        r2 = admin_client.post(f"/api/users/{operator_user.id}/change_type/", {"user_type": "bad"}, format="json")
        assert r2.status_code == 400

    def test_anonymize_self_400_and_target_ok(self, admin_client, admin_user, operator_user):
        r = admin_client.post(f"/api/users/{admin_user.id}/anonymize/", {}, format="json")
        assert r.status_code == 400
        anon_tgt = User.objects.create_user(
            email=f"anon-{uuid.uuid4().hex[:8]}@test.com",
            password="An123456!",
            role="OPERATOR",
            user_type="internal",
        )
        anon_tgt.tenant = admin_user.tenant
        anon_tgt.save(update_fields=["tenant"])
        r2 = admin_client.post(f"/api/users/{anon_tgt.id}/anonymize/", {}, format="json")
        assert r2.status_code == 200
        anon_tgt.refresh_from_db()
        assert "anonymized_" in anon_tgt.email

    def test_anonymize_non_admin_inside_view(self, db, tenant, ou):
        su = User.objects.create_user(
            email="u100-su@test.com",
            password="Su123456!",
            role="OPERATOR",
            is_superuser=True,
            user_type="internal",
        )
        su.tenant = tenant
        su.save(update_fields=["tenant"])
        op = User.objects.create_user(
            email="u100-victim@test.com",
            password="V123456!",
            role="OPERATOR",
            user_type="internal",
        )
        op.tenant = tenant
        op.save(update_fields=["tenant"])
        c = APIClient()
        c.force_authenticate(user=su)
        r = c.post(f"/api/users/{op.id}/anonymize/", {}, format="json")
        assert r.status_code == 403

    def test_create_manual_generated_and_provided_password_guest_internal_ou(self, admin_client, ou):
        em = f"manual-{uuid.uuid4().hex[:8]}@test.com"
        r = admin_client.post(
            "/api/users/create_manual/",
            {
                "email": em,
                "first_name": "M",
                "last_name": "N",
                "user_type": "internal",
                "role": "APPROVER",
                "organizational_unit_id": str(ou.id),
                "send_welcome_email": True,
            },
            format="json",
        )
        assert r.status_code == 201
        body = r.json()
        assert body.get("generated_password") is not None
        em2 = f"manual2-{uuid.uuid4().hex[:8]}@test.com"
        r2 = admin_client.post(
            "/api/users/create_manual/",
            {
                "email": em2,
                "first_name": "A",
                "last_name": "B",
                "user_type": "guest",
                "password": "Provided1A!",
                "send_welcome_email": False,
            },
            format="json",
        )
        assert r2.status_code == 201
        assert r2.json().get("generated_password") is None


@pytest.mark.django_db
class TestUserViewsResetDeactivateImport:
    # Copre righe: 325-345, 347-361, 367-387, 389-438, 440-480
    def test_reset_password_superuser_non_admin_role_403(self, db, tenant, operator_user):
        su = User.objects.create_user(
            email="u100-rp@test.com",
            password="Rp123456!",
            role="OPERATOR",
            is_superuser=True,
            user_type="internal",
        )
        su.tenant = tenant
        su.save(update_fields=["tenant"])
        c = APIClient()
        c.force_authenticate(user=su)
        r = c.post(f"/api/users/{operator_user.id}/reset_password/", {}, format="json")
        assert r.status_code == 403

    def test_reset_password_admin_ok(self, admin_client, operator_user):
        r = admin_client.post(f"/api/users/{operator_user.id}/reset_password/", {}, format="json")
        assert r.status_code == 200
        assert "generated_password" in r.json()

    def test_deactivate_reactivate(self, admin_client, operator_user):
        assert admin_client.post(f"/api/users/{operator_user.id}/deactivate/", {}, format="json").status_code == 204
        operator_user.refresh_from_db()
        assert operator_user.is_active is False
        assert admin_client.post(f"/api/users/{operator_user.id}/reactivate/", {}, format="json").status_code == 204
        operator_user.refresh_from_db()
        assert operator_user.is_active is True

    def test_import_template_csv_xlsx_bad_format(self, admin_client):
        assert admin_client.get("/api/users/import/template/?file_format=csv").status_code == 200
        assert admin_client.get("/api/users/import/template/?file_format=xlsx").status_code == 200
        assert admin_client.get("/api/users/import/template/?file_format=xml").status_code == 400

    def test_import_preview_and_import_users_branches(self, admin_client):
        csv_content = b"email,first_name,last_name,role\nx@y.com,A,B,OPERATOR\n"
        f = SimpleUploadedFile("t.csv", csv_content, content_type="text/csv")
        r = admin_client.post("/api/users/import/preview/", {"file": f}, format="multipart")
        assert r.status_code == 200
        assert "preview" in r.json()
        assert admin_client.post("/api/users/import/preview/", {}, format="multipart").status_code == 400
        bad = SimpleUploadedFile("t.bin", b"x", content_type="application/octet-stream")
        assert admin_client.post("/api/users/import/preview/", {"file": bad}, format="multipart").status_code == 400
        junk = SimpleUploadedFile("bad.xlsx", b"not-a-real-xlsx", content_type="application/vnd.ms-excel")
        r_err = admin_client.post("/api/users/import/preview/", {"file": junk}, format="multipart")
        assert r_err.status_code == 400
        f2 = SimpleUploadedFile("u.csv", csv_content, content_type="text/csv")
        r_imp = admin_client.post(
            "/api/users/import/",
            {"file": f2, "send_invite": "false"},
            format="multipart",
        )
        assert r_imp.status_code == 200

    def test_import_users_missing_file_bad_ext_parse_error(self, admin_client):
        assert admin_client.post("/api/users/import/", {}, format="multipart").status_code == 400
        assert (
            admin_client.post(
                "/api/users/import/",
                {"file": SimpleUploadedFile("n.pdf", b"x", content_type="application/pdf")},
                format="multipart",
            ).status_code
            == 400
        )
        with patch("apps.users.views.UserImporter.parse_file", side_effect=RuntimeError("read")):
            f = SimpleUploadedFile("z.csv", b"a,b\n", content_type="text/csv")
            r = admin_client.post("/api/users/import/", {"file": f}, format="multipart")
            assert r.status_code == 400
        xlsx_bytes = UserImporter().get_template_xlsx()
        fx = SimpleUploadedFile("bulk.xlsx", xlsx_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        r_x = admin_client.post("/api/users/import/", {"file": fx}, format="multipart")
        assert r_x.status_code == 200


@pytest.mark.django_db
class TestUserViewsPermissionsAndGroups:
    # Copre righe: 482-513, 515-578, 594-646
    def test_permissions_detail_and_set_permission_document_dossier(self, admin_client, admin_user, operator_user, folder):
        doc = Document.objects.create(
            title="P",
            tenant=folder.tenant,
            folder=folder,
            created_by=admin_user,
            owner=admin_user,
        )
        dos = Dossier.objects.create(
            title="D",
            identifier=f"ID-{uuid.uuid4().hex[:8]}",
            tenant=folder.tenant,
            created_by=admin_user,
            organizational_unit=None,
        )
        r = admin_client.get(f"/api/users/{operator_user.id}/permissions/")
        assert r.status_code == 200
        r2 = admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {"type": "document", "target_id": str(doc.id), "can_read": True, "can_write": True, "can_delete": True},
            format="json",
        )
        assert r2.status_code == 200
        r3 = admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {"type": "dossier", "target_id": str(dos.id), "can_read": True, "can_write": False},
            format="json",
        )
        assert r3.status_code == 200
        r4 = admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {"type": "document", "target_id": str(doc.id), "remove": True},
            format="json",
        )
        assert r4.status_code == 200
        assert admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {"type": "document", "target_id": str(uuid.uuid4()), "can_read": True},
            format="json",
        ).status_code == 400
        assert admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {},
            format="json",
        ).status_code == 400
        assert admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {"type": "other", "target_id": str(doc.id)},
            format="json",
        ).status_code == 400
        assert admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {"type": "dossier", "target_id": str(uuid.uuid4()), "can_read": True},
            format="json",
        ).status_code == 400
        assert admin_client.post(
            f"/api/users/{operator_user.id}/set_permission/",
            {"type": "dossier", "target_id": str(dos.id), "remove": True},
            format="json",
        ).status_code == 200

    def test_user_group_search_ou_members_add_remove(self, admin_client, admin_user, operator_user, ou):
        gname = f"grp-{uuid.uuid4().hex[:8]}"
        r = admin_client.post(
            "/api/groups/",
            {
                "name": gname,
                "description": "d",
                "organizational_unit": str(ou.id),
            },
            format="json",
        )
        assert r.status_code == 201
        gid = r.json()["id"]
        assert admin_client.get("/api/groups/", {"search": gname[:5]}).status_code == 200
        assert admin_client.get("/api/groups/", {"ou": str(ou.id)}).status_code == 200
        assert admin_client.post(f"/api/groups/{gid}/add_members/", {"user_ids": "bad"}, format="json").status_code == 400
        assert admin_client.post(
            f"/api/groups/{gid}/add_members/",
            {"user_ids": [str(operator_user.id), str(uuid.uuid4())]},
            format="json",
        ).status_code == 200
        assert admin_client.get(f"/api/groups/{gid}/members/").status_code == 200
        assert admin_client.delete(f"/api/groups/{gid}/remove_member/{operator_user.id}/").status_code == 204
        assert admin_client.delete(f"/api/groups/{gid}/remove_member/{uuid.uuid4()}/").status_code == 404
        assert admin_client.delete(f"/api/groups/{gid}/").status_code == 204
