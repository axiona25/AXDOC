"""JWT refresh/access con claim tenant_id (FASE 29)."""
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


def issue_refresh_for_user(user) -> RefreshToken:
    refresh = RefreshToken.for_user(user)
    tid = getattr(user, "tenant_id", None)
    if tid:
        s = str(tid)
        refresh["tenant_id"] = s
        refresh.access_token["tenant_id"] = s
    from .session_limit import limit_concurrent_refresh_sessions

    limit_concurrent_refresh_sessions(user)
    return refresh


class AxdocTokenRefreshSerializer(TokenRefreshSerializer):
    """Mantiene tenant_id sull'access (e sul refresh ruotato)."""

    def validate(self, attrs):
        data = super().validate(attrs)
        refresh_str = data.get("refresh") or attrs["refresh"]
        refresh = RefreshToken(refresh_str)
        tid = refresh.get("tenant_id")
        if not tid:
            return data
        access = AccessToken(data["access"])
        access["tenant_id"] = tid
        data["access"] = str(access)
        if "refresh" in data:
            nr = RefreshToken(data["refresh"])
            nr["tenant_id"] = tid
            data["refresh"] = str(nr)
        return data
