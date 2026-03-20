"""Test modelli UO e membership."""
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.organizations.models import OrganizationalUnit, OrganizationalUnitMembership

User = get_user_model()


class OrganizationalUnitModelTest(TestCase):
    def setUp(self):
        self.root = OrganizationalUnit.objects.create(
            name="Direzione", code="DIR", description="Root"
        )
        self.child = OrganizationalUnit.objects.create(
            name="IT", code="IT", parent=self.root
        )
        self.grandchild = OrganizationalUnit.objects.create(
            name="Dev", code="DEV", parent=self.child
        )

    def test_get_ancestors(self):
        self.assertEqual(list(self.child.get_ancestors()), [self.root])
        self.assertEqual(list(self.grandchild.get_ancestors()), [self.child, self.root])
        self.assertEqual(list(self.root.get_ancestors()), [])

    def test_get_descendants(self):
        desc = self.root.get_descendants()
        self.assertIn(self.child, desc)
        self.assertIn(self.grandchild, desc)
        self.assertEqual(len(desc), 2)

    def test_get_all_members_includes_children(self):
        user = User.objects.create_user(
            email="m@test.com", password="Test1!", first_name="M", last_name="User"
        )
        OrganizationalUnitMembership.objects.create(
            user=user, organizational_unit=self.child, role="OPERATOR"
        )
        members = self.root.get_all_members()
        self.assertIn(user, members)

    def test_code_unique(self):
        with self.assertRaises(Exception):
            OrganizationalUnit.objects.create(name="X", code="DIR")
