# AXDOC — FASE 01
# Setup Progetto, Autenticazione e Utenti Base

**Prerequisito:** nessuno — è la prima fase.

---

## CHECKLIST DI COMPLETAMENTO

Prima di passare alla FASE 02, verificare che TUTTI questi punti siano ✅:

- [ ] `docker-compose up --build` avvia backend, frontend, db e redis senza errori
- [ ] `python manage.py migrate` completa senza errori
- [ ] API `POST /api/auth/login/` restituisce JWT con credenziali valide
- [ ] API `POST /api/auth/login/` restituisce 401 con credenziali errate
- [ ] API `POST /api/auth/logout/` invalida il refresh token
- [ ] API `POST /api/auth/refresh/` rinnova l'access token
- [ ] Blocco account dopo 5 tentativi falliti → 423 (RF-005)
- [ ] Sblocco automatico dopo 15 minuti
- [ ] API `POST /api/auth/password-reset/` invia email con token (RF-003)
- [ ] API `POST /api/auth/password-reset/confirm/` reimposta password (RF-004)
- [ ] API `GET /api/users/me/` restituisce profilo utente autenticato
- [ ] API `GET /api/users/` funziona solo per ADMIN
- [ ] Registro `AuditLog` per ogni login/logout
- [ ] Tutti i test pytest passano (`pytest --cov` ≥ 80%)
- [ ] Frontend: pagina `/login` funzionante con gestione errori
- [ ] Frontend: pagina `/forgot-password` funzionante
- [ ] Frontend: pagina `/reset-password/:token` funzionante
- [ ] Frontend: routing protetto — redirect a `/login` se non autenticato
- [ ] Frontend: tutti i test Vitest passano
- [ ] `npm run build` completa senza errori TypeScript

---

## STEP 1.1 — Struttura Docker e Setup Iniziale

### Prompt per Cursor:

```
Crea la struttura base del progetto AXDOC con Docker Compose.

Stack: Django 4.2, DRF 3.14, React 18 TypeScript, MySQL 8.0, Redis 7.

Crea i seguenti file partendo dalla root del progetto:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. docker-compose.yml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Quattro servizi:

db:
  image: mysql:8.0
  environment: MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD (tutti da .env)
  ports: "3306:3306"
  volumes: mysql_data:/var/lib/mysql
  healthcheck: mysqladmin ping ogni 10s

redis:
  image: redis:7-alpine
  ports: "6379:6379"
  volumes: redis_data:/data

backend:
  build: ./backend
  command: python manage.py runserver 0.0.0.0:8000
  ports: "8000:8000"
  volumes: ./backend:/app
  env_file: .env
  depends_on: db (condition: service_healthy), redis

frontend:
  build: ./frontend
  command: npm run dev -- --host
  ports: "3000:3000"
  volumes: ./frontend:/app, /app/node_modules
  environment: VITE_API_URL=http://localhost:8000

volumes: mysql_data, redis_data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. backend/Dockerfile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev gcc pkg-config \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. backend/requirements.txt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Django==4.2.*
djangorestframework==3.14.*
djangorestframework-simplejwt==5.3.*
django-cors-headers==4.*
mysqlclient==2.2.*
Pillow==10.*
django-environ==0.11.*
pytest-django==4.7.*
pytest-cov==4.*
black==24.*
flake8==7.*
factory-boy==3.3.*
channels==4.0.*
channels-redis==4.2.*
daphne==4.0.*
redis==5.*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. backend/config/settings/base.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import environ
env = environ.Env()
environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terze parti
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    # App AXDOC (da aggiungere man mano)
    'apps.users',
    'apps.authentication',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
AUTH_USER_MODEL = 'users.User'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', default='axdoc'),
        'USER': env('DB_USER', default='axdoc'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default='db'),
        'PORT': env('DB_PORT', default='3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:3000'])
CORS_ALLOW_CREDENTIALS = True

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@axdoc.local')
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. backend/config/settings/development.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from .base import *
DEBUG = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. backend/config/urls.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. backend/config/wsgi.py e asgi.py standard Django
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. backend/pytest.ini
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.development
python_files = tests/test_*.py
addopts = -v --tb=short

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. .env (nella root del progetto)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECRET_KEY=axdoc-dev-secret-key-cambia-in-produzione
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings.development
DB_NAME=axdoc
DB_USER=axdoc
DB_PASSWORD=axdoc_password
DB_HOST=db
DB_PORT=3306
MYSQL_DATABASE=axdoc
MYSQL_USER=axdoc
MYSQL_PASSWORD=axdoc_password
MYSQL_ROOT_PASSWORD=root_password
REDIS_URL=redis://redis:6379/0
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@axdoc.local
FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000
VITE_API_URL=http://localhost:8000

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. frontend/ — scaffolding con Vite + React + TypeScript
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Esegui: npm create vite@latest frontend -- --template react-ts
Poi installa le dipendenze nel package.json:

dependencies:
  react-router-dom: ^6
  axios: ^1
  zustand: ^4
  react-hook-form: ^7
  zod: ^3
  @hookform/resolvers: ^3
  @tanstack/react-query: ^5
  tailwindcss: ^3
  @headlessui/react: ^2
  lucide-react: ^0.400

devDependencies:
  vitest: ^1
  @testing-library/react: ^16
  @testing-library/jest-dom: ^6
  @testing-library/user-event: ^14
  jsdom: ^24
  @types/node: ^20
  autoprefixer: ^10
  postcss: ^8

Crea frontend/vite.config.ts:
  server.proxy: { '/api': { target: 'http://backend:8000', changeOrigin: true } }
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'] }

Crea frontend/tailwind.config.ts base.
Crea frontend/src/test/setup.ts con import '@testing-library/jest-dom'.
Crea frontend/Dockerfile:
  FROM node:20-alpine
  WORKDIR /app
  COPY package*.json .
  RUN npm install
  COPY . .
  EXPOSE 3000
  CMD ["npm", "run", "dev", "--", "--host"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
11. .gitignore nella root
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
node_modules/
dist/
.DS_Store
*.log
media/
staticfiles/

Dopo aver creato tutti i file:
  docker-compose up --build -d
  docker-compose logs backend
  → Deve mostrare "Starting development server at http://0.0.0.0:8000/"
```

---

## STEP 1.2 — App Users: Modello Utente Custom

### Prompt per Cursor:

```
Crea l'app Django `backend/apps/users/` con il modello utente custom.

Requisiti: RF-011..RF-020

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
backend/apps/users/models.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email obbligatoria')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('must_change_password', False)
        return self.create_user(email, password, **extra_fields)

ROLE_CHOICES = [
    ('OPERATOR', 'Operatore'),
    ('REVIEWER', 'Revisore'),
    ('APPROVER', 'Approvatore'),
    ('ADMIN', 'Amministratore'),
]

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='OPERATOR')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)   # cancellazione logica RF-014
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)  # blocco RF-005
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    must_change_password = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_users'
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Utente'
        verbose_name_plural = 'Utenti'

    def __str__(self):
        return f'{self.get_full_name()} <{self.email}>'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def is_locked(self):
        from django.utils import timezone
        return self.locked_until is not None and self.locked_until > timezone.now()

    def get_primary_ou_name(self):
        membership = self.ou_memberships.filter(is_active=True).first()
        return membership.organizational_unit.name if membership else ''

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
backend/apps/users/serializers.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crea i seguenti serializer:

UserSerializer (lettura — no password):
  fields: id, email, first_name, last_name, role, is_active, is_deleted,
          date_joined, avatar, phone, get_full_name

UserCreateSerializer (scrittura admin):
  fields: email, first_name, last_name, role, phone
  Crea utente con password casuale e must_change_password=True

UserUpdateSerializer (scrittura parziale):
  fields: first_name, last_name, phone, avatar, role (solo ADMIN)

UserProfileSerializer (utente modifica se stesso):
  fields: first_name, last_name, phone, avatar
  (non può cambiare email o ruolo)

ChangePasswordSerializer:
  fields: old_password, new_password, new_password_confirm
  Valida: new_password == new_password_confirm, min 8 char, 1 numero, 1 maiuscola

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
backend/apps/users/views.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UserViewSet(ModelViewSet):
  queryset: User.objects.filter(is_deleted=False)
  Permessi:
    - list, create, destroy → solo ADMIN
    - retrieve, update → ADMIN oppure utente stesso
  Filtri: role, is_active, ricerca per first_name, last_name, email
  Paginazione: 20 per pagina

  extra action: GET /users/me/
    Ritorna: UserSerializer(request.user)

  extra action: POST /users/{id}/deactivate/
    Solo ADMIN — imposta is_active=False

  extra action: POST /users/{id}/reactivate/
    Solo ADMIN — imposta is_active=True

Crea permesso custom: IsAdminOrSelf
  Consente accesso se user.role == 'ADMIN' oppure user == obj

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
backend/apps/users/urls.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
urlpatterns = [path('', include(router.urls))]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Migration + Admin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python manage.py makemigrations users
Registra UserAdmin in admin.py con tutti i campi visibili.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST: backend/apps/users/tests/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_models.py:
  - Creazione utente: UUID generato, email unica
  - is_locked(): True se locked_until > now, False altrimenti
  - get_full_name(): "Mario Rossi"
  - Cancellazione logica: is_deleted=True non appare in queryset

test_views.py:
  - GET /api/users/ anonimo → 401
  - GET /api/users/ utente OPERATOR → 403
  - GET /api/users/ utente ADMIN → 200 con lista
  - POST /api/users/ ADMIN → 201 utente creato
  - GET /api/users/me/ → dati utente loggato
  - PATCH /api/users/{id}/ utente modifica se stesso → 200
  - PATCH /api/users/{id}/ utente modifica altro → 403

Esegui: pytest backend/apps/users/ -v --tb=short
→ Tutti i test devono passare
```

---

## STEP 1.3 — App Authentication: JWT, Sicurezza e Audit

### Prompt per Cursor:

```
Crea `backend/apps/authentication/` con il sistema di autenticazione completo.

Requisiti: RF-001..RF-010, RF-006, RF-007, RNF-001, RNF-006, RNF-007

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
backend/apps/authentication/models.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta

class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE,
                             related_name='password_reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

ACTION_CHOICES = [
    ('LOGIN', 'Login'), ('LOGIN_FAILED', 'Login Fallito'),
    ('LOGOUT', 'Logout'), ('PASSWORD_RESET', 'Reset Password'),
    ('PASSWORD_CHANGED', 'Password Cambiata'),
    ('USER_CREATED', 'Utente Creato'), ('USER_UPDATED', 'Utente Modificato'),
    ('USER_INVITED', 'Invito Inviato'), ('INVITATION_ACCEPTED', 'Invito Accettato'),
    ('DOCUMENT_CREATED', 'Documento Creato'),
    ('DOCUMENT_UPLOADED', 'Documento Caricato'),
    ('DOCUMENT_DOWNLOADED', 'Documento Scaricato'),
    ('DOCUMENT_DELETED', 'Documento Eliminato'),
    ('DOCUMENT_SHARED', 'Documento Condiviso'),
    ('WORKFLOW_STARTED', 'Workflow Avviato'),
    ('WORKFLOW_APPROVED', 'Documento Approvato'),
    ('WORKFLOW_REJECTED', 'Documento Rifiutato'),
    ('PROTOCOL_CREATED', 'Protocollo Creato'),
    ('DOCUMENT_SIGNED', 'Documento Firmato'),
    ('DOCUMENT_CONSERVED', 'Documento in Conservazione'),
    ('DOCUMENT_ENCRYPTED', 'Documento Cifrato'),
]

class AuditLog(models.Model):
    """Registro di tutte le azioni importanti nel sistema (RF-010, RNF-007)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', null=True, on_delete=models.SET_NULL,
                             related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'

    @classmethod
    def log(cls, user, action, detail=None, request=None):
        ip = None
        ua = ''
        if request:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')
        cls.objects.create(user=user, action=action, detail=detail or {}, ip_address=ip, user_agent=ua)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
backend/apps/authentication/views.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crea i seguenti views:

1. LoginView (POST /api/auth/login/) — AllowAny
   - Corpo: { "email": "...", "password": "..." }
   - Cerca utente per email (is_deleted=False)
   - Se utente non trovato: AuditLog(LOGIN_FAILED), risponde 401
   - Se is_locked(): risponde 423 con { "error": "account_locked",
     "locked_until": "ISO datetime", "message": "Account bloccato. Riprova dopo X minuti." }
   - Verifica password con check_password()
   - Se password errata:
     * incrementa failed_login_attempts
     * Se failed_login_attempts >= 5:
       locked_until = now() + timedelta(minutes=15)
       AuditLog(LOGIN_FAILED, {"attempts": 5, "locked": true})
       risponde 423
     * Altrimenti AuditLog(LOGIN_FAILED), risponde 401
   - Se password corretta:
     * azzera failed_login_attempts e locked_until
     * Aggiorna last_login = now()
     * Genera JWT: access + refresh (SimpleJWT)
     * AuditLog(LOGIN)
     * Risponde 200: { "access": "...", "refresh": "...",
       "user": { id, email, first_name, last_name, role },
       "must_change_password": bool }

2. LogoutView (POST /api/auth/logout/) — IsAuthenticated
   - Corpo: { "refresh": "..." }
   - Invalida refresh token (blacklist)
   - AuditLog(LOGOUT)
   - Risponde 204

3. RefreshTokenView (POST /api/auth/refresh/)
   Usa simplejwt.views.TokenRefreshView direttamente.

4. PasswordResetRequestView (POST /api/auth/password-reset/) — AllowAny
   - Corpo: { "email": "..." }
   - Cerca utente (silenzioso se non trovato)
   - Se trovato:
     * Invalida token precedenti non usati
     * Crea PasswordResetToken (scadenza 1h)
     * Invia email con link: {FRONTEND_URL}/reset-password/{token}
     * AuditLog(PASSWORD_RESET, {"email": email})
   - Risponde sempre 200 { "message": "Se l'email esiste riceverai un link." }

5. PasswordResetConfirmView (POST /api/auth/password-reset/confirm/) — AllowAny
   - Corpo: { "token": "...", "new_password": "...", "new_password_confirm": "..." }
   - Verifica token (PasswordResetToken.is_valid())
   - Valida password (min 8 char, 1 maiuscola, 1 numero)
   - Imposta nuova password, marca token come usato
   - Risponde 200

6. ChangePasswordView (POST /api/auth/change-password/) — IsAuthenticated
   - ChangePasswordSerializer
   - Verifica old_password, aggiorna password
   - Imposta must_change_password=False
   - AuditLog(PASSWORD_CHANGED)
   - Risponde 200

7. MeView (GET /api/auth/me/) — IsAuthenticated
   Ritorna UserSerializer(request.user)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
backend/apps/authentication/urls.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
urlpatterns = [
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('refresh/', RefreshTokenView.as_view()),
    path('password-reset/', PasswordResetRequestView.as_view()),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),
    path('me/', MeView.as_view()),
]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crea migration e aggiungi authentication a INSTALLED_APPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST: backend/apps/authentication/tests/test_auth.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usa pytest-django + factory-boy.

Crea UserFactory in conftest.py:
  class UserFactory(factory.django.DjangoModelFactory):
    class Meta: model = User
    email = factory.Sequence(lambda n: f'user{n}@test.com')
    first_name = 'Test'
    last_name = factory.Sequence(lambda n: f'User{n}')
    role = 'OPERATOR'
    must_change_password = False

Test da implementare:
  test_login_success: ritorna access + refresh + user data
  test_login_wrong_password: 401
  test_login_nonexistent_email: 401
  test_login_5_failed_attempts_locks_account: dopo 5 tentativi → 423
  test_locked_account_correct_password_still_locked: anche con pass giusta → 423
  test_logout_blacklists_token: dopo logout, refresh fallisce
  test_password_reset_request_existing_email: token creato, 200
  test_password_reset_request_nonexistent_email: 200 (no leak)
  test_password_reset_confirm_valid_token: password cambiata
  test_password_reset_confirm_expired_token: 400
  test_password_reset_confirm_used_token: 400
  test_me_authenticated: ritorna dati utente
  test_me_unauthenticated: 401
  test_audit_log_created_on_login: AuditLog con action=LOGIN
  test_audit_log_created_on_failed_login: AuditLog con action=LOGIN_FAILED

Esegui: pytest backend/apps/authentication/ -v --tb=short
→ Tutti i test devono passare
```

---

## STEP 1.4 — Frontend: Pagine Autenticazione

### Prompt per Cursor:

```
Crea le pagine e i servizi di autenticazione nel frontend React TypeScript.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/types/auth.ts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export type UserRole = 'OPERATOR' | 'REVIEWER' | 'APPROVER' | 'ADMIN'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole
  avatar: string | null
  phone: string
  must_change_password: boolean
}

export interface LoginRequest { email: string; password: string }
export interface LoginResponse {
  access: string
  refresh: string
  user: User
  must_change_password: boolean
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/services/api.ts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Istanza axios con:
- baseURL: import.meta.env.VITE_API_URL
- interceptor REQUEST: aggiunge Bearer token da localStorage('axdoc_access_token')
- interceptor RESPONSE:
  * Su 401: prova refreshToken()
  * Se refresh riesce: riprova la richiesta originale con nuovo token
  * Se refresh fallisce: rimuove token, window.location = '/login'

Funzione refreshToken():
  POST /api/auth/refresh/ con refresh da localStorage
  Salva nuovo access token
  Lancia errore se fallisce

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/services/authService.ts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
login(email, password):
  POST /api/auth/login/
  Salva access in localStorage('axdoc_access_token')
  Salva refresh in localStorage('axdoc_refresh_token')
  Ritorna LoginResponse

logout(refreshToken):
  POST /api/auth/logout/ con refresh
  Rimuove entrambi i token da localStorage

getMe(): GET /api/auth/me/

requestPasswordReset(email): POST /api/auth/password-reset/

confirmPasswordReset(token, new_password, new_password_confirm):
  POST /api/auth/password-reset/confirm/

changePassword(old_password, new_password, new_password_confirm):
  POST /api/auth/change-password/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/store/authStore.ts (Zustand)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
State:
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean

Actions:
  setUser(user): imposta user e isAuthenticated=true
  clearUser(): rimuove user e isAuthenticated=false
  initializeAuth(): chiama getMe() se token in localStorage,
                    setta user o chiama clearUser() su errore

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/components/auth/ProtectedRoute.tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Props: children, allowedRoles?: UserRole[]
- Se isLoading: mostra spinner
- Se !isAuthenticated: <Navigate to="/login" />
- Se allowedRoles e user.role non incluso: <Navigate to="/unauthorized" />
- Altrimenti: render children

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/pages/LoginPage.tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layout centrato verticalmente. Card bianca con:
- Titolo "AXDOC" + sottotitolo "Gestione Documentale"
- Form react-hook-form:
  * Email (validazione: email valida, required)
  * Password (required, min 6 char)
  * Bottone "Accedi" con loading spinner durante submit
- Gestione errori:
  * 401: "Email o password non corretti"
  * 423: "Account bloccato. Riprova dopo X minuti." (mostra locked_until)
  * rete: "Errore di connessione. Riprova."
- Link "Hai dimenticato la password?" → /forgot-password
- Dopo login: se must_change_password → /change-password
              altrimenti → /dashboard

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/pages/ForgotPasswordPage.tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Form con solo email
- Submit → authService.requestPasswordReset(email)
- Dopo submit (successo o errore):
  Mostra messaggio: "Se l'email è registrata, riceverai un link a breve."
- Link back a /login

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/pages/ResetPasswordPage.tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Legge :token da useParams()
- Form: nuova password + conferma
- Validazione zod: min 8 char, almeno 1 numero, 1 maiuscola
- Submit → authService.confirmPasswordReset(token, ...)
- Successo: toast "Password cambiata" → redirect /login dopo 2s
- Errore 400: "Link non valido o scaduto"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/pages/ChangePasswordPage.tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Mostrata quando must_change_password=True dopo login
- Form: vecchia password, nuova password, conferma
- Stesso schema validazione di ResetPasswordPage
- Submit → authService.changePassword(...)
- Successo → /dashboard

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/App.tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Routes:
  /login             → LoginPage (pubblica)
  /forgot-password   → ForgotPasswordPage (pubblica)
  /reset-password/:token → ResetPasswordPage (pubblica)
  /accept-invitation/:token → AcceptInvitationPage (pubblica, FASE 02)
  /share/:token      → PublicSharePage (pubblica, FASE 11)
  /change-password   → ChangePasswordPage (ProtectedRoute)
  /dashboard         → DashboardPage (ProtectedRoute)
  /unauthorized      → pagina semplice "Accesso non autorizzato"
  /                  → redirect a /dashboard

All'avvio: chiama authStore.initializeAuth()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
frontend/src/pages/DashboardPage.tsx (placeholder)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Per ora: pagina semplice con "Dashboard — in costruzione"
+ nome utente loggato da authStore
+ bottone Logout

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST: frontend/src/__tests__/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test_LoginPage.test.tsx:
  - Render del form
  - Submit con dati validi → authService.login chiamato
  - Errore 401 → messaggio errore visibile
  - Errore 423 → messaggio "Account bloccato"
  - Loading state durante submit

test_ProtectedRoute.test.tsx:
  - Non autenticato → redirect /login
  - Autenticato → render children
  - Ruolo sbagliato → redirect /unauthorized

test_authStore.test.ts:
  - setUser → isAuthenticated=true
  - clearUser → isAuthenticated=false, user=null

Esegui: npm run test -- --run → tutti i test passano
Esegui: npm run build → nessun errore TypeScript
```

---

## TEST INTEGRAZIONE FASE 01

### Prompt per Cursor:

```
Esegui i test di integrazione completi per la FASE 01.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Avvio e migrazione
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docker-compose up -d
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser \
  --email admin@axdoc.com --first_name Admin --last_name AXDOC
  (password: Admin123!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. Test backend
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docker-compose exec backend pytest --cov=apps --cov-report=term-missing
→ Coverage ≥ 80%, ZERO failures

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. Test frontend
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docker-compose exec frontend npm run test -- --run
→ ZERO failures

docker-compose exec frontend npm run build
→ Build completata senza errori TypeScript

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. Test API manuali (curl)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# a) Login successo
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@axdoc.com","password":"Admin123!"}' | python3 -m json.tool
→ Deve mostrare access, refresh, user con role=ADMIN

# b) Salva il token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@axdoc.com","password":"Admin123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# c) Me
curl -s http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
→ Dati admin

# d) Me senza token → 401
curl -s http://localhost:8000/api/auth/me/ | python3 -m json.tool

# e) Blocco account (5 tentativi)
for i in 1 2 3 4 5; do
  curl -s -X POST http://localhost:8000/api/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@axdoc.com","password":"sbagliata"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Tentativo {i}: {d}')"
done
# Al 5° deve ritornare locked_until
# Prova login con password giusta → 423

# f) Password reset
curl -s -X POST http://localhost:8000/api/auth/password-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@axdoc.com"}' | python3 -m json.tool
→ 200 con messaggio. Controlla console Django per il link email.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. Test browser
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Apri http://localhost:3000
→ Redirect a /login
→ Login con admin@axdoc.com / Admin123! → /dashboard con nome utente
→ Refresh pagina → rimane autenticato (token in localStorage)
→ Logout → torna a /login
→ http://localhost:3000/dashboard senza login → redirect /login

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. Verifica AuditLog
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docker-compose exec backend python manage.py shell -c "
from apps.authentication.models import AuditLog
for log in AuditLog.objects.all()[:5]:
    print(log.action, log.user, log.timestamp)
"
→ Deve mostrare LOGIN, LOGIN_FAILED ecc.

Se tutti i passi sono ✅ crea FASE_01_TEST_REPORT.md con i risultati.
```
