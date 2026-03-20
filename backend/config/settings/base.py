"""
AXDOC — Django base settings.
"""
from pathlib import Path
import environ

env = environ.Env()
environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "daphne",
    "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terze parti
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # App AXDOC
    "apps.users",
    "apps.organizations",
    "apps.authentication",
    "apps.documents",
    "apps.metadata",
    "apps.protocols",
    "apps.workflows",
    "apps.dossiers",
    "apps.signatures",
    "apps.sharing",
    "apps.notifications",
    "apps.search",
    "apps.audit",
    "apps.chat",
    "apps.dashboard",
    "apps.admin_panel",
    "apps.archive",
    "apps.mail",
    "social_django",
    "dbbackup",
    "django_celery_beat",
]

# Backup (FASE 15, RNF-022, RNF-024)
BACKUP_DIR = env("BACKUP_DIR", default="/backups/db")
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {"location": BACKUP_DIR}
DBBACKUP_CLEANUP_KEEP = env.int("BACKUP_RETENTION_DAYS", default=30)
DBBACKUP_CLEANUP_KEEP_MEDIA = env.int("BACKUP_MEDIA_RETENTION_DAYS", default=30)

# ─── Celery ─────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Rome"
CELERY_BEAT_SCHEDULE = {
    "fetch-all-mail-accounts": {
        "task": "apps.mail.tasks.fetch_all_accounts",
        "schedule": 120.0,
    },
}

ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL", default="redis://redis:6379/0")],
        },
    },
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.admin_panel.middleware.LicenseCheckMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.microsoft.MicrosoftOAuth2",
]

# SSO OAuth2 (RF-008)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env("GOOGLE_OAUTH2_CLIENT_ID", default="")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env("GOOGLE_OAUTH2_CLIENT_SECRET", default="")
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["email", "profile"]
SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = env("MICROSOFT_OAUTH2_CLIENT_ID", default="")
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = env("MICROSOFT_OAUTH2_CLIENT_SECRET", default="")
SOCIAL_AUTH_MICROSOFT_GRAPH_TENANT_ID = env("MICROSOFT_TENANT_ID", default="common")
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "apps.authentication.pipeline.create_or_update_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
)
SOCIAL_AUTH_USER_MODEL = "users.User"
SOCIAL_AUTH_RAISE_EXCEPTIONS = False
LOGIN_REDIRECT_URL = "/api/auth/sso/jwt-redirect/"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/api/auth/sso/jwt-redirect/"

# LDAP (RF-009) — attivo solo se LDAP_ENABLED=True e django-auth-ldap installato
LDAP_ENABLED = env.bool("LDAP_ENABLED", default=False)
if LDAP_ENABLED:
    try:
        import ldap
        from django_auth_ldap.config import LDAPSearch, ActiveDirectoryGroupType
        AUTH_LDAP_SERVER_URI = env("LDAP_SERVER_URI")
        AUTH_LDAP_BIND_DN = env("LDAP_BIND_DN", default="")
        AUTH_LDAP_BIND_PASSWORD = env("LDAP_BIND_PASSWORD", default="")
        AUTH_LDAP_USER_SEARCH = LDAPSearch(
            env("LDAP_USER_BASE_DN"),
            ldap.SCOPE_SUBTREE,
            env("LDAP_USER_FILTER", default="(sAMAccountName=%(user)s)"),
        )
        AUTH_LDAP_USER_ATTR_MAP = {
            "first_name": env("LDAP_ATTR_FIRSTNAME", default="givenName"),
            "last_name": env("LDAP_ATTR_LASTNAME", default="sn"),
            "email": env("LDAP_ATTR_EMAIL", default="mail"),
        }
        AUTH_LDAP_ALWAYS_UPDATE_USER = True
        AUTHENTICATION_BACKENDS = [
            "django_auth_ldap.backend.LDAPBackend",
        ] + AUTHENTICATION_BACKENDS
    except ImportError:
        LDAP_ENABLED = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="axdoc"),
        "USER": env("DB_USER", default="axdoc"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="db"),
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

# Security headers (RNF-005, FASE 14)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Password validation (FASE 14)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "apps.authentication.password_validators.UppercasePasswordValidator"},
    {"NAME": "apps.authentication.password_validators.SpecialCharPasswordValidator"},
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# RNF-011: upload fino a 200MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 209715200
FILE_UPLOAD_MAX_MEMORY_SIZE = 209715200
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@axdoc.local")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

# Cache per MFA setup (secret temporaneo 10 min)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Firma digitale e conservazione (FASE 10)
SIGNATURE_PROVIDER = env("SIGNATURE_PROVIDER", default="mock")
CONSERVATION_PROVIDER = env("CONSERVATION_PROVIDER", default="mock")
ARUBA_SIGN_API_URL = env("ARUBA_SIGN_API_URL", default="")
ARUBA_SIGN_API_KEY = env("ARUBA_SIGN_API_KEY", default="")
ARUBA_SIGN_USER_ID = env("ARUBA_SIGN_USER_ID", default="")
ARUBA_CONSERVATION_API_URL = env("ARUBA_CONSERVATION_API_URL", default="")
ARUBA_CONSERVATION_API_KEY = env("ARUBA_CONSERVATION_API_KEY", default="")

# WebRTC (FASE 13)
WEBRTC_ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
]
