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
