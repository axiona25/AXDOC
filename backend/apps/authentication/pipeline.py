"""
Pipeline SSO: crea o aggiorna utente da provider OAuth2 (RF-008).
"""
from django.contrib.auth import get_user_model

User = get_user_model()


def create_or_update_user(strategy, details, backend, user=None, *args, **kwargs):
    """
    Se utente esistente (user): aggiorna nome.
    Se social_user esiste (account collegato): ritorna user.
    Altrimenti cerca per email; se trovato associa, se no crea nuovo con ruolo OPERATOR.
    """
    if user:
        user.first_name = details.get("first_name") or user.first_name
        user.last_name = details.get("last_name") or user.last_name
        user.save(update_fields=["first_name", "last_name"])
        return {"user": user}

    email = details.get("email")
    if not email:
        return {}

    existing = User.objects.filter(email__iexact=email, is_deleted=False).first()
    if existing:
        return {"user": existing}

    import secrets
    new_user = User.objects.create_user(
        email=email,
        password=secrets.token_urlsafe(32),
        first_name=details.get("first_name", ""),
        last_name=details.get("last_name", ""),
        role="OPERATOR",
        must_change_password=False,
    )
    new_user.set_unusable_password()
    new_user.save(update_fields=["password"])
    return {"user": new_user}
