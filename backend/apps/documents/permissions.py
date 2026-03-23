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
    from apps.users.permissions import get_user_ou_ids
    from .models import Document, DocumentPermission, DocumentOUPermission

    user_ou_ids = get_user_ou_ids(user)
    user_ou_member_ids = list(
        OrganizationalUnitMembership.objects.filter(
            organizational_unit_id__in=user_ou_ids, is_active=True
        )
        .values_list("user_id", flat=True)
        .distinct()
    )
    explicit_doc_ids = set(
        DocumentPermission.objects.filter(user=user, can_read=True).values_list("document_id", flat=True)
    )
    ou_doc_ids = set(
        DocumentOUPermission.objects.filter(
            organizational_unit_id__in=user_ou_ids, can_read=True
        ).values_list("document_id", flat=True)
    )
    allowed_ids = explicit_doc_ids | ou_doc_ids
    return (
        Q(owner=user)
        | Q(created_by=user)
        | Q(visibility=Document.VISIBILITY_OFFICE, owner_id__in=user_ou_member_ids)
        | Q(visibility=Document.VISIBILITY_SHARED)
        | Q(pk__in=allowed_ids)
    )


class CanAccessDocument(permissions.BasePermission):
    """
    L'utente può accedere al documento se:
    - è in DocumentPermission (can_read) O
    - appartiene a una UO in DocumentOUPermission (can_read) O
    - è ADMIN O
    - è owner / created_by O
    - visibilità shared O office (stessa UO del proprietario)
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
        if obj.owner_id == user.id or obj.created_by_id == user.id:
            return True
        if obj.visibility == Document.VISIBILITY_SHARED:
            return True
        if obj.user_permissions.filter(user=user, can_read=True).exists():
            return True
        from apps.organizations.models import OrganizationalUnitMembership
        from apps.users.permissions import get_user_ou_ids

        user_ou_ids = get_user_ou_ids(user)
        if obj.ou_permissions.filter(organizational_unit_id__in=user_ou_ids, can_read=True).exists():
            return True
        if obj.visibility == Document.VISIBILITY_OFFICE:
            peer_ids = set(
                OrganizationalUnitMembership.objects.filter(
                    organizational_unit_id__in=user_ou_ids, is_active=True
                ).values_list("user_id", flat=True)
            )
            if obj.owner_id and obj.owner_id in peer_ids:
                return True
        return False
