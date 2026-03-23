"""
Permessi custom per l'app users.
"""
from rest_framework import permissions


class IsAdminRole(permissions.BasePermission):
    """Consente accesso solo se l'utente ha role ADMIN."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "ADMIN"
        )


class IsAdminOrSelf(permissions.BasePermission):
    """
    Consente accesso se l'utente è ADMIN oppure sta agendo su se stesso.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == "ADMIN":
            return True
        return obj == request.user


def get_user_ou_ids(user):
    """Ritorna il set di UO ID a cui l'utente appartiene (membership attive)."""
    if not user or not user.is_authenticated:
        return set()
    from apps.organizations.models import OrganizationalUnitMembership

    return set(
        OrganizationalUnitMembership.objects.filter(user=user, is_active=True).values_list(
            "organizational_unit_id", flat=True
        )
    )


def is_admin_user(user):
    """Verifica se l'utente è ADMIN."""
    return user and user.is_authenticated and getattr(user, "role", None) == "ADMIN"
