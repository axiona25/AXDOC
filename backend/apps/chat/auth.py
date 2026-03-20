"""Auth per WebSocket: JWT da query string (SimpleJWT)."""
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_from_scope(scope):
    """Estrae user da scope (query string token=). Usa SimpleJWT per decode."""
    query = parse_qs(scope.get("query_string", b"").decode())
    token = (query.get("token") or [None])[0]
    if not token:
        return None
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        access = AccessToken(token)
        user_id = access.get("user_id")
        if user_id:
            return User.objects.filter(pk=user_id).first()
    except Exception:
        pass
    return None
