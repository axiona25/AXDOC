"""
Permessi per utenti ospiti (FASE 17).
- IsInternalUser: nega l'accesso agli ospiti (protocolli, fascicoli, workflow, metadata, UO, gestione utenti).
- Documenti: gli ospiti vedono solo documenti con DocumentPermission esplicita (can_read).
"""
from rest_framework import permissions


class IsInternalUser(permissions.BasePermission):
    """
    Consente l'accesso solo agli utenti interni.
    Gli utenti ospiti ricevono 403 (non possono accedere a protocolli, fascicoli, workflow, metadata, UO, list/create/destroy utenti).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, "user_type", "internal") == "internal"
