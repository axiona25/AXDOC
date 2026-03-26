"""Limite sessioni JWT concorrenti (refresh token in blacklist)."""
from django.conf import settings


def limit_concurrent_refresh_sessions(user) -> None:
    """
    Mantiene al massimo MAX_CONCURRENT_SESSIONS refresh token attivi (non blacklisted)
    per utente, invalidando i più vecchi.
    """
    max_sessions = int(getattr(settings, "MAX_CONCURRENT_SESSIONS", 3) or 0)
    if max_sessions <= 0 or not user or not user.pk:
        return

    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    blacklisted_ids = BlacklistedToken.objects.values_list("token_id", flat=True)
    active = (
        OutstandingToken.objects.filter(user=user)
        .exclude(id__in=blacklisted_ids)
        .order_by("-created_at")
    )
    active_list = list(active)
    excess = active_list[max_sessions:]
    for ot in excess:
        BlacklistedToken.objects.get_or_create(token=ot)
