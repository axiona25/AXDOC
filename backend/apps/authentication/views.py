"""
Viste autenticazione: login, logout, JWT refresh, MFA, reset password, invite, me (RF-001..RF-010, RF-002).
"""
import jwt
from datetime import timedelta, datetime
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import UserSerializer, ChangePasswordSerializer
from .models import PasswordResetToken, AuditLog, UserInvitation
from .serializers import (
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    InviteUserSerializer,
    AcceptInvitationSerializer,
)
from .mfa import (
    generate_totp_secret,
    get_totp_uri,
    generate_qr_code_base64,
    verify_totp,
    generate_backup_codes,
    verify_backup_code,
)
from .encryption import encrypt_secret, decrypt_secret
from apps.users.permissions import IsAdminRole

User = get_user_model()

MFA_SETUP_CACHE_TTL = 600  # 10 min
MFA_PENDING_TOKEN_TTL_MINUTES = 5


def _create_mfa_pending_token(user):
    """JWT con scope mfa_pending, TTL 5 min."""
    payload = {
        "user_id": str(user.id),
        "scope": "mfa_pending",
        "exp": datetime.utcnow() + timedelta(minutes=MFA_PENDING_TOKEN_TTL_MINUTES),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return token if isinstance(token, str) else token.decode()


def _decode_mfa_pending_token(token_str):
    """Decode e verifica MFA pending token. Ritorna user o None."""
    if not token_str:
        return None
    try:
        payload = jwt.decode(
            token_str,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        if payload.get("scope") != "mfa_pending":
            return None
        user_id = payload.get("user_id")
        if not user_id:
            return None
        return User.objects.get(pk=user_id)
    except Exception:
        return None

LOCKOUT_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _get_client_ip_and_agent(request):
    ip = None
    ua = ""
    if request:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = (
            x_forwarded.split(",")[0].strip()
            if x_forwarded
            else request.META.get("REMOTE_ADDR")
        )
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
    return ip, ua


LOGIN_RATE_LIMIT_PER_MINUTE = 10


class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "email": "...", "password": "..." }
    Ritorna: access, refresh, user, must_change_password.
    Rate limit: 10 tentativi/minuto per IP (FASE 14).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.core.cache import cache
        ip, _ = _get_client_ip_and_agent(request)
        rate_key = f"login_attempts_{ip}"
        attempts = cache.get(rate_key, 0)
        if attempts >= LOGIN_RATE_LIMIT_PER_MINUTE:
            return Response(
                {"detail": "Troppi tentativi di accesso. Riprova tra un minuto."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(email__iexact=email, is_deleted=False)
        except User.DoesNotExist:
            cache.set(rate_key, cache.get(rate_key, 0) + 1, timeout=60)
            AuditLog.log(None, "LOGIN_FAILED", {"email": email}, request)
            return Response(
                {"detail": "Email o password non corretti."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if user.is_locked():
            cache.set(rate_key, cache.get(rate_key, 0) + 1, timeout=60)
            return Response(
                {
                    "error": "account_locked",
                    "locked_until": user.locked_until.isoformat(),
                    "message": f"Account bloccato. Riprova dopo {LOCKOUT_MINUTES} minuti.",
                },
                status=status.HTTP_423_LOCKED,
            )

        if not user.check_password(password):
            cache.set(rate_key, cache.get(rate_key, 0) + 1, timeout=60)
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= LOCKOUT_ATTEMPTS:
                user.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
                user.save(update_fields=["failed_login_attempts", "locked_until"])
                AuditLog.log(
                    user,
                    "LOGIN_FAILED",
                    {"attempts": LOCKOUT_ATTEMPTS, "locked": True},
                    request,
                )
                return Response(
                    {
                        "error": "account_locked",
                        "locked_until": user.locked_until.isoformat(),
                        "message": f"Account bloccato dopo {LOCKOUT_ATTEMPTS} tentativi. Riprova dopo {LOCKOUT_MINUTES} minuti.",
                    },
                    status=status.HTTP_423_LOCKED,
                )
            user.save(update_fields=["failed_login_attempts"])
            AuditLog.log(user, "LOGIN_FAILED", {"attempts": user.failed_login_attempts}, request)
            return Response(
                {"detail": "Email o password non corretti."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = timezone.now()
        user.save(update_fields=["failed_login_attempts", "locked_until", "last_login"])

        # MFA: se abilitato, ritorna token temporaneo per step verifica (RF-002)
        if getattr(user, "mfa_enabled", False):
            mfa_pending_token = _create_mfa_pending_token(user)
            AuditLog.log(user, "LOGIN", {"mfa_pending": True}, request)
            return Response(
                {
                    "mfa_required": True,
                    "mfa_pending_token": mfa_pending_token,
                },
                status=status.HTTP_200_OK,
            )

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)
        AuditLog.log(user, "LOGIN", {}, request)

        return Response(
            {
                "access": access,
                "refresh": refresh_str,
                "user": UserSerializer(user).data,
                "must_change_password": user.must_change_password,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Body: { "refresh": "..." }
    Invalida il refresh token (blacklist).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_str = request.data.get("refresh")
        if not refresh_str:
            return Response(
                {"detail": "refresh token mancante."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_str)
            token.blacklist()
        except Exception:
            pass
        AuditLog.log(request.user, "LOGOUT", {}, request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshTokenView(TokenRefreshView):
    """POST /api/auth/refresh/ — rinnovo access token."""


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/
    Body: { "email": "..." }
    Invia email con link (se utente esiste). Risponde sempre 200.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email, is_deleted=False).first()
        if user:
            PasswordResetToken.objects.filter(user=user, used=False).delete()
            pr = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=1),
            )
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
            link = f"{frontend_url}/reset-password/{pr.token}"
            send_mail(
                subject="Reset password AXDOC",
                message=f"Usa questo link per reimpostare la password (valido 1 ora):\n{link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            AuditLog.log(None, "PASSWORD_RESET", {"email": email}, request)

        return Response(
            {"message": "Se l'email esiste, riceverai un link a breve."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/
    Body: { "token": "uuid", "new_password": "...", "new_password_confirm": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_uuid = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        pr = PasswordResetToken.objects.filter(token=token_uuid).first()
        if not pr or not pr.is_valid():
            return Response(
                {"detail": "Link non valido o scaduto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(new_password, pr.user)
        except DjangoValidationError as e:
            msg = e.messages[0] if e.messages else "Password non valida."
            return Response({"new_password": msg}, status=status.HTTP_400_BAD_REQUEST)
        pr.user.set_password(new_password)
        pr.user.must_change_password = False
        pr.user.save(update_fields=["password", "must_change_password"])
        pr.used = True
        pr.save(update_fields=["used"])
        return Response(
            {"message": "Password aggiornata."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Body: { "old_password", "new_password", "new_password_confirm" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Password attuale errata."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(serializer.validated_data["new_password"], request.user)
        except DjangoValidationError as e:
            msg = e.messages[0] if e.messages else "Password non valida."
            return Response({"new_password": msg}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.must_change_password = False
        request.user.save(update_fields=["password", "must_change_password"])
        AuditLog.log(request.user, "PASSWORD_CHANGED", {}, request)
        return Response(
            {"message": "Password aggiornata."},
            status=status.HTTP_200_OK,
        )


class InviteUserView(APIView):
    """
    POST /api/auth/invite/
    Solo ADMIN. Crea UserInvitation, invia email con link /accept-invitation/{token}.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email, is_deleted=False).exists():
            return Response(
                {"email": "Un utente con questa email esiste già."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing = UserInvitation.objects.filter(
            email__iexact=email, is_used=False
        ).exclude(expires_at__lt=timezone.now())
        if existing.exists():
            return Response(
                {"email": "Esiste già un invito pendente per questa email."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ou_id = serializer.validated_data.get("organizational_unit_id")
        ou = None
        if ou_id:
            from apps.organizations.models import OrganizationalUnit
            ou = OrganizationalUnit.objects.filter(pk=ou_id, is_active=True).first()
        inv = UserInvitation.objects.create(
            email=email,
            invited_by=request.user,
            role=serializer.validated_data.get("role", "OPERATOR"),
            ou_role=serializer.validated_data.get("ou_role", "OPERATOR"),
            organizational_unit=ou,
            expires_at=timezone.now() + timedelta(days=7),
        )
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        link = f"{frontend_url}/accept-invitation/{inv.token}"
        send_mail(
            subject="Invito a AXDOC",
            message=f"Sei stato invitato a unirti a AXDOC. Clicca per accettare (valido 7 giorni):\n{link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        AuditLog.log(request.user, "USER_INVITED", {"email": email, "invitation_id": str(inv.id)}, request)
        return Response(
            {"id": str(inv.id), "email": email, "expires_at": inv.expires_at.isoformat()},
            status=status.HTTP_201_CREATED,
        )


class AcceptInvitationView(APIView):
    """
    GET /api/auth/accept-invitation/<token>/ — dati invito (email).
    POST /api/auth/accept-invitation/<token>/ — first_name, last_name, password, password_confirm.
    Crea User, eventuale membership UO, auto-login con JWT.
    """
    permission_classes = [AllowAny]

    def get(self, request, token=None):
        inv = UserInvitation.objects.filter(token=token).first()
        if not inv or not inv.is_valid():
            return Response(
                {"detail": "Invito non valido o scaduto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"email": inv.email})

    def post(self, request, token=None):
        inv = UserInvitation.objects.filter(token=token).first()
        if not inv or not inv.is_valid():
            return Response(
                {"detail": "Invito non valido o scaduto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(serializer.validated_data["password"])
        except DjangoValidationError as e:
            msg = e.messages[0] if e.messages else "Password non valida."
            return Response({"password": msg}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            email=inv.email,
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            role=inv.role,
            must_change_password=False,
        )
        if inv.organizational_unit_id:
            from apps.organizations.models import OrganizationalUnitMembership
            OrganizationalUnitMembership.objects.create(
                user=user,
                organizational_unit=inv.organizational_unit,
                role=inv.ou_role or "OPERATOR",
            )
        inv.is_used = True
        inv.accepted_at = timezone.now()
        inv.save(update_fields=["is_used", "accepted_at"])
        AuditLog.log(user, "INVITATION_ACCEPTED", {"invitation_id": str(inv.id)}, request)
        send_mail(
            subject="Benvenuto in AXDOC",
            message=f"Ciao {user.first_name}, il tuo account AXDOC è stato attivato.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class MFASetupInitView(APIView):
    """
    GET /api/auth/mfa/setup/
    Solo utenti autenticati con mfa_enabled=False.
    Genera secret temporaneo, salva in cache, ritorna secret + QR base64 + otpauth_uri.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "mfa_enabled", False):
            return Response(
                {"detail": "MFA già abilitato."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        secret = generate_totp_secret()
        cache_key = f"mfa_setup_{request.user.id}"
        cache.set(cache_key, secret, timeout=MFA_SETUP_CACHE_TTL)
        otpauth_uri = get_totp_uri(secret, request.user.email)
        qr_base64 = generate_qr_code_base64(otpauth_uri)
        return Response({
            "secret": secret,
            "qr_code_base64": qr_base64,
            "otpauth_uri": otpauth_uri,
        })


class MFASetupConfirmView(APIView):
    """
    POST /api/auth/mfa/setup/confirm/
    Body: { "code": "123456" }
    Verifica TOTP, salva secret cifrato, genera backup codes, abilita MFA.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, "mfa_enabled", False):
            return Response(
                {"detail": "MFA già abilitato."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        code = (request.data.get("code") or "").strip()
        if not code or len(code) != 6:
            return Response(
                {"code": "Codice a 6 cifre richiesto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cache_key = f"mfa_setup_{request.user.id}"
        secret = cache.get(cache_key)
        if not secret:
            return Response(
                {"detail": "Setup MFA scaduto. Riprova da capo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not verify_totp(secret, code):
            return Response(
                {"code": "Codice non valido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user.mfa_secret = encrypt_secret(secret)
        plain_codes, hashed_codes = generate_backup_codes()
        user.mfa_backup_codes = hashed_codes
        user.mfa_enabled = True
        user.mfa_setup_at = timezone.now()
        user.save(update_fields=["mfa_secret", "mfa_backup_codes", "mfa_enabled", "mfa_setup_at"])
        cache.delete(cache_key)
        return Response({
            "success": True,
            "backup_codes": plain_codes,
        })


class MFADisableView(APIView):
    """
    POST /api/auth/mfa/disable/
    Body: { "code": "123456" } oppure { "backup_code": "ABCD1234" }
    Verifica identità con TOTP o backup code, poi disabilita MFA.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not getattr(user, "mfa_enabled", False):
            return Response({"detail": "MFA non abilitato."}, status=status.HTTP_400_BAD_REQUEST)
        code = (request.data.get("code") or "").strip()
        backup_code = (request.data.get("backup_code") or "").strip()
        verified = False
        if code and len(code) == 6:
            secret = decrypt_secret(user.mfa_secret or "")
            if secret and verify_totp(secret, code):
                verified = True
        if not verified and backup_code:
            ok, new_list = verify_backup_code(user.mfa_backup_codes or [], backup_code)
            if ok:
                verified = True
                user.mfa_backup_codes = new_list
        if not verified:
            return Response(
                {"detail": "Codice non valido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.mfa_enabled = False
        user.mfa_secret = ""
        user.mfa_backup_codes = []
        user.mfa_setup_at = None
        user.save(update_fields=["mfa_enabled", "mfa_secret", "mfa_backup_codes", "mfa_setup_at"])
        return Response({"success": True})


class MFAVerifyView(APIView):
    """
    POST /api/auth/mfa/verify/
    Body: { "mfa_pending_token": "...", "code": "123456" } oppure { "mfa_pending_token": "...", "backup_code": "..." }
    Verifica TOTP o backup code e ritorna JWT access + refresh completi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token_str = request.data.get("mfa_pending_token") or request.headers.get("X-MFA-Pending-Token")
        user = _decode_mfa_pending_token(token_str)
        if not user:
            return Response(
                {"detail": "Token MFA non valido o scaduto."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        code = (request.data.get("code") or "").strip()
        backup_code = (request.data.get("backup_code") or "").strip()
        verified = False
        new_backup_codes = list(user.mfa_backup_codes or [])
        if code and len(code) == 6:
            secret = decrypt_secret(user.mfa_secret or "")
            if secret and verify_totp(secret, code):
                verified = True
        if not verified and backup_code:
            ok, new_backup_codes = verify_backup_code(user.mfa_backup_codes or [], backup_code)
            if ok:
                verified = True
                user.mfa_backup_codes = new_backup_codes
                user.save(update_fields=["mfa_backup_codes"])
        if not verified:
            return Response(
                {"detail": "Codice non valido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)
        AuditLog.log(user, "LOGIN", {"mfa_verified": True}, request)
        return Response({
            "access": access,
            "refresh": refresh_str,
            "user": UserSerializer(user).data,
            "must_change_password": user.must_change_password,
        })


class MeView(APIView):
    """GET /api/auth/me/ — dati utente autenticato."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# --- SSO (RF-008): init e JWT redirect ---

class SSOInitView(APIView):
    """
    GET /api/auth/sso/<provider>/
    Ritorna { "auth_url": "..." } per redirect al provider OAuth2.
    """
    permission_classes = [AllowAny]

    def get(self, request, provider=None):
        backend_map = {"google": "google-oauth2", "microsoft": "microsoft-graph"}
        backend = backend_map.get(provider) or provider
        if backend not in ("google-oauth2", "microsoft-graph"):
            return Response(
                {"detail": "Provider non valido."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if backend == "google-oauth2" and not settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            return Response(
                {"detail": "SSO non configurato per questo provider."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if backend == "microsoft-graph" and not settings.SOCIAL_AUTH_MICROSOFT_GRAPH_KEY:
            return Response(
                {"detail": "SSO non configurato per questo provider."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        from django.urls import reverse
        auth_url = request.build_absolute_uri(
            reverse("social:begin", args=[backend])
        )
        return Response({"auth_url": auth_url})


def sso_jwt_redirect_view(request):
    """
    Vista Django (dopo SSO complete): utente in sessione, genera JWT e redirect a frontend.
    """
    from django.shortcuts import redirect
    from django.contrib.auth import get_user_model
    from urllib.parse import urlencode
    User = get_user_model()
    if not request.user.is_authenticated:
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        return redirect(f"{frontend_url}/login?error=sso_failed")
    user = request.user
    if not isinstance(user, User):
        user = User.objects.get(pk=user.pk)
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    refresh_str = str(refresh)
    AuditLog.log(user, "LOGIN", {"sso": True}, request)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    params = urlencode({"access": access, "refresh": refresh_str})
    return redirect(f"{frontend_url}/sso-callback?{params}")


# --- Admin LDAP (RF-009) ---

class LDAPStatusView(APIView):
    """GET /api/admin/ldap/status/ — stato connessione LDAP (solo ADMIN)."""
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        if not getattr(settings, "LDAP_ENABLED", False):
            return Response({
                "connected": False,
                "server": "",
                "error": "LDAP disabilitato",
            })
        server = getattr(settings, "AUTH_LDAP_SERVER_URI", "")
        try:
            import ldap
            conn = ldap.initialize(server)
            conn.simple_bind_s(
                getattr(settings, "AUTH_LDAP_BIND_DN", ""),
                getattr(settings, "AUTH_LDAP_BIND_PASSWORD", ""),
            )
            conn.unbind_s()
            return Response({"connected": True, "server": server, "error": None})
        except Exception as e:
            return Response({
                "connected": False,
                "server": server,
                "error": str(e),
            })


class LDAPSyncView(APIView):
    """POST /api/admin/ldap/sync/ — avvia sincronizzazione utenti LDAP (solo ADMIN)."""
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        if not getattr(settings, "LDAP_ENABLED", False):
            return Response(
                {"detail": "LDAP disabilitato."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        try:
            call_command("sync_ldap_users", stdout=out)
            return Response({"message": "Sync avviato.", "output": out.getvalue()})
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
