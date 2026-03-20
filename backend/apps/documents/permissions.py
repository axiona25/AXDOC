"""
Permessi documenti e cartelle (FASE 05).
"""
from django.db.models import Q
from rest_framework import permissions


def _documents_queryset_filter(user):
    """Restituisce un Q per filtrare Document che l'utente può vedere (per list)."""
    if not user or not user.is_authenticated:
        return Q(pk__in=[])
    # Utenti ospiti: solo documenti con DocumentPermission esplicita (FASE 17)
    if getattr(user, "user_type", "internal") == "guest":
        return Q(user_permissions__user=user, user_permissions__can_read=True)
    if getattr(user, "role", None) == "ADMIN":
        return Q()
    from apps.organizations.models import OrganizationalUnitMembership
    user_ou_ids = list(
        OrganizationalUnitMembership.objects.filter(user=user).values_list("organizational_unit_id", flat=True)
    )
    return Q(created_by=user) | Q(user_permissions__user=user, user_permissions__can_read=True) | Q(
        ou_permissions__organizational_unit_id__in=user_ou_ids, ou_permissions__can_read=True
    )


class CanAccessDocument(permissions.BasePermission):
    """
    L'utente può accedere al documento se:
    - è in DocumentPermission (can_read) O
    - appartiene a una UO in DocumentOUPermission (can_read) O
    - è ADMIN O
    - ha creato il documento (created_by).
    """

    def has_object_permission(self, request, view, obj):
        from .models import Document

        if not isinstance(obj, Document):
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "role", None) == "ADMIN":
            return True
        # Utenti ospiti: solo documenti con permesso esplicito (FASE 17)
        if getattr(user, "user_type", "internal") == "guest":
            return obj.user_permissions.filter(user=user, can_read=True).exists()
        if obj.created_by_id == user.id:
            return True
        if obj.user_permissions.filter(user=user, can_read=True).exists():
            return True
        from apps.organizations.models import OrganizationalUnitMembership
        user_ou_ids = OrganizationalUnitMembership.objects.filter(user=user).values_list("organizational_unit_id", flat=True)
        if obj.ou_permissions.filter(organizational_unit_id__in=user_ou_ids, can_read=True).exists():
            return True
        return False
