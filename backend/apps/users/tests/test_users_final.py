# Copertura: users/* FASE 35D.2
import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from rest_framework import serializers

from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership, Tenant
from apps.users.guest_permissions import IsInternalUser
from apps.users.importers import UserImporter
from apps.users.models import ConsentRecord, UserGroup, UserGroupMembership
from apps.users.serializers import (
    ChangePasswordSerializer,
    UserCreateManualSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.users.views import UserGroupViewSet, UserViewSet

User = get_user_model()


@pytest.fixture
def tenant(db):
    t, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default", "plan": "enterprise"})
    return t


@pytest.fixture
def ou(db, tenant):
    return OrganizationalUnit.objects.create(name="UOU", code="UOU", tenant=tenant)


@pytest.mark.django_db
class TestUsersModelsFinal:
    def test_str_and_properties(self, ou):
        u = User.objects.create_user(
            email="stru@test.com",
            password="TestPass123!",
            first_name="F",
            last_name="L",
            role="OPERATOR",
        )
        assert u.email in str(u) and "F" in str(u)
        assert u.is_guest is False
        assert u.is_internal is True
        ug = UserGroup.objects.create(name="G1")
        assert str(ug) == "G1"
        m = UserGroupMembership.objects.create(group=ug, user=u)
        assert u.email in str(m) and "G1" in str(m)
        cr = ConsentRecord.objects.create(user=u, consent_type="privacy_policy", version="1", granted=True)
        assert "granted" in str(cr).lower() or "privacy" in str(cr).lower()


@pytest.mark.django_db
class TestUsersSerializersFinal:
    def test_create_duplicate_email(self):
        User.objects.create_user(
            email="dup@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ser = UserCreateSerializer(data={"email": "DUP@test.com", "first_name": "x", "last_name": "y", "role": "OPERATOR"})
        assert ser.is_valid() is False
        ser2 = UserCreateSerializer(data={"email": "dup@test.com", "first_name": "x", "last_name": "y", "role": "OPERATOR"})
        assert ser2.is_valid() is False

    def test_update_organizational_unit(self, ou):
        u = User.objects.create_user(
            email="upd@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        ou2 = OrganizationalUnit.objects.create(name="O2", code="O2", tenant=ou.tenant)
        ser = UserUpdateSerializer(
            u,
            data={"first_name": "N", "organizational_unit_id": str(ou2.id)},
            partial=True,
        )
        assert ser.is_valid(), ser.errors
        ser.save()
        assert OrganizationalUnitMembership.objects.filter(user=u, organizational_unit=ou2, is_active=True).exists()

    def test_create_manual_guest_and_password(self, ou):
        ser = UserCreateManualSerializer(
            data={
                "email": "guestfin@test.com",
                "first_name": "G",
                "last_name": "U",
                "user_type": "guest",
                "password": "Abcd1234!",
            }
        )
        assert ser.is_valid(), ser.errors
        user = ser.save()
        assert user.role == "OPERATOR"
        ser2 = UserCreateManualSerializer(
            data={
                "email": "intfin@test.com",
                "first_name": "I",
                "last_name": "N",
                "user_type": "internal",
                "organizational_unit_id": str(ou.id),
            }
        )
        assert ser2.is_valid(), ser2.errors
        u2 = ser2.save()
        assert OrganizationalUnitMembership.objects.filter(user=u2, organizational_unit=ou).exists()

    def test_create_manual_invalid_ou(self):
        import uuid

        ser = UserCreateManualSerializer(
            data={
                "email": "nou@test.com",
                "first_name": "a",
                "last_name": "b",
                "organizational_unit_id": str(uuid.uuid4()),
            }
        )
        assert ser.is_valid() is False

    def test_change_password_mismatch(self):
        ser = ChangePasswordSerializer(
            data={
                "old_password": "x",
                "new_password": "Abcd1234!",
                "new_password_confirm": "Abcd1234!!",
            }
        )
        assert ser.is_valid() is False

    def test_change_password_weak(self):
        ser = ChangePasswordSerializer(
            data={
                "old_password": "x",
                "new_password": "short",
                "new_password_confirm": "short",
            }
        )
        assert ser.is_valid() is False
        ser = ChangePasswordSerializer(
            data={
                "old_password": "x",
                "new_password": "abcdefgh",
                "new_password_confirm": "abcdefgh",
            }
        )
        assert ser.is_valid() is False
        ser2 = ChangePasswordSerializer(
            data={
                "old_password": "x",
                "new_password": "Abcdefgh",
                "new_password_confirm": "Abcdefgh",
            }
        )
        assert ser2.is_valid() is False

    def test_change_password_ok(self):
        ser = ChangePasswordSerializer(
            data={
                "old_password": "Oldpass1!",
                "new_password": "Abcd1234!",
                "new_password_confirm": "Abcd1234!",
            }
        )
        assert ser.is_valid(), ser.errors

    def test_create_manual_duplicate_email(self):
        User.objects.create_user(
            email="dupm@test.com",
            password="TestPass123!",
            first_name="a",
            last_name="b",
        )
        ser = UserCreateManualSerializer(
            data={"email": "DUPM@test.com", "first_name": "x", "last_name": "y"}
        )
        assert ser.is_valid() is False

    def test_create_manual_inactive_ou(self, ou):
        ou.is_active = False
        ou.save(update_fields=["is_active"])
        ser = UserCreateManualSerializer(
            data={
                "email": "inou@test.com",
                "first_name": "a",
                "last_name": "b",
                "organizational_unit_id": str(ou.id),
            }
        )
        assert ser.is_valid() is False

    def test_create_manual_ou_none_explicit(self):
        ser = UserCreateManualSerializer(
            data={
                "email": "ounone@test.com",
                "first_name": "a",
                "last_name": "b",
                "organizational_unit_id": None,
            }
        )
        assert ser.is_valid(), ser.errors

    def test_user_serializer_ou_none(self, ou):
        u = User.objects.create_user(
            email="nouo@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="B",
        )
        data = UserSerializer(u).data
        assert data.get("organizational_unit") is None


@pytest.mark.django_db
class TestUserImporterFinal:
    def test_parse_invalid_type(self):
        imp = UserImporter()
        with pytest.raises(ValueError):
            imp.parse_file(io.BytesIO(b"x"), "txt")

    def test_validate_row_errors(self, ou):
        imp = UserImporter()
        assert imp.validate_row({"email": "bad"}, 1)
        assert imp.validate_row({"email": "a@b.c", "first_name": "x", "last_name": "y", "role": "BAD"}, 1)
        assert imp.validate_row(
            {"email": "ok@test.it", "first_name": "x", "last_name": "y", "role": "OPERATOR", "organizational_unit_code": "NOCODE"},
            1,
        )

    def test_import_skips_duplicate(self):
        User.objects.create_user(
            email="skip@test.com",
            password="TestPass123!",
            first_name="S",
            last_name="K",
        )
        imp = UserImporter()
        rows = [
            {
                "email": "skip@test.com",
                "first_name": "S",
                "last_name": "K",
                "role": "OPERATOR",
            }
        ]
        out = imp.import_users(rows, send_invite=False)
        assert out["skipped"] == 1

    def test_import_rows_with_validation_errors(self):
        imp = UserImporter()
        rows = [{"email": "not-an-email", "first_name": "a", "last_name": "b", "role": "OPERATOR"}]
        out = imp.import_users(rows, send_invite=False)
        assert out["errors"]

    def test_import_creates_with_ou(self, ou):
        imp = UserImporter()
        rows = [
            {
                "email": "newimp@test.com",
                "first_name": "N",
                "last_name": "W",
                "role": "OPERATOR",
                "organizational_unit_code": ou.code,
                "ou_role": "REVIEWER",
            }
        ]
        out = imp.import_users(rows, send_invite=False)
        assert out["created"] == 1


@pytest.mark.django_db
class TestGuestPermissionsFinal:
    def test_is_internal_user_denies_guest(self):
        u = User.objects.create_user(
            email="gstperm@test.com",
            password="TestPass123!",
            first_name="G",
            last_name="U",
            user_type="guest",
        )
        factory = RequestFactory()
        req = factory.get("/")
        req.user = u
        assert IsInternalUser().has_permission(req, None) is False

    def test_is_internal_user_anonymous(self):
        factory = RequestFactory()
        req = factory.get("/")
        req.user = AnonymousUser()
        assert IsInternalUser().has_permission(req, None) is False

    def test_is_internal_user_allows_internal(self):
        u = User.objects.create_user(
            email="intperm@test.com",
            password="TestPass123!",
            first_name="I",
            last_name="N",
            user_type="internal",
        )
        factory = RequestFactory()
        req = factory.get("/")
        req.user = u
        assert IsInternalUser().has_permission(req, None) is True


@pytest.mark.django_db
class TestUserManagerFinal:
    def test_create_user_requires_email(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_superuser(self):
        su = User.objects.create_superuser(
            email="su@test.com",
            password="TestPass123!",
            first_name="S",
            last_name="U",
        )
        assert su.is_superuser and su.role == "ADMIN"


@pytest.mark.django_db
@pytest.mark.django_db
class TestUsersPermissionsHelpersFinal:
    def test_is_admin_role_and_ou_ids(self, ou):
        from apps.users.permissions import IsAdminRole, get_user_ou_ids, is_admin_user

        u = User.objects.create_user(
            email="permh@test.com",
            password="TestPass123!",
            first_name="P",
            last_name="H",
            role="ADMIN",
        )
        factory = RequestFactory()
        req = factory.get("/")
        req.user = u
        assert IsAdminRole().has_permission(req, None) is True
        OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, is_active=True)
        assert ou.id in get_user_ou_ids(u)
        assert is_admin_user(u) is True
        assert is_admin_user(AnonymousUser()) is False
        assert get_user_ou_ids(None) == set()
        req_anon = factory.get("/")
        req_anon.user = AnonymousUser()
        assert IsAdminRole().has_permission(req_anon, None) is False

    def test_is_admin_or_self(self):
        from apps.users.permissions import IsAdminOrSelf

        u = User.objects.create_user(
            email="selfp@test.com",
            password="TestPass123!",
            first_name="S",
            last_name="E",
            role="OPERATOR",
        )
        adm = User.objects.create_user(
            email="adm@test.com",
            password="TestPass123!",
            first_name="A",
            last_name="D",
            role="ADMIN",
        )
        factory = RequestFactory()
        req = factory.get("/")
        req.user = adm
        assert IsAdminOrSelf().has_object_permission(req, None, u) is True
        req.user = u
        assert IsAdminOrSelf().has_object_permission(req, None, u) is True


class TestUserModelHelpersFinal:
    def test_get_primary_ou_name(self, ou):
        u = User.objects.create_user(
            email="pou@test.com",
            password="TestPass123!",
            first_name="P",
            last_name="O",
        )
        OrganizationalUnitMembership.objects.create(user=u, organizational_unit=ou, is_active=True)
        assert ou.name in u.get_primary_ou_name()


@pytest.mark.django_db
@pytest.mark.django_db
class TestUserViewSetSerializerRoutingFinal:
    def test_get_serializer_class_default(self, rf, admin_user):
        view = UserViewSet()
        view.request = rf.get("/api/users/")
        view.request.user = admin_user
        view.action = "list"
        assert view.get_serializer_class().__name__ == "UserSerializer"
        view.action = "destroy"
        assert view.get_serializer_class().__name__ == "UserSerializer"

    def test_user_group_retrieve_detail_serializer(self, rf, admin_user):
        view = UserGroupViewSet()
        view.request = rf.get("/api/groups/")
        view.request.user = admin_user
        view.action = "retrieve"
        assert view.get_serializer_class().__name__ == "UserGroupDetailSerializer"


class TestUserImporterEdgeFinal:
    def test_parse_xlsx_empty_headers(self):
        imp = UserImporter()
        with pytest.raises(Exception):
            imp._parse_xlsx(b"not-a-real-xlsx")

    def test_validate_row_str_too_long(self):
        imp = UserImporter()
        errs = imp.validate_row(
            {
                "email": "long@test.com",
                "first_name": "x" * 200,
                "last_name": "y",
                "role": "OPERATOR",
            },
            1,
        )
        assert any("massimo" in e.lower() or "150" in e for e in errs)

