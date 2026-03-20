# AXDOC — Sistema di Gestione Documentale Aziendale
## FASE 00 — Panoramica del Progetto

> **Tieni questo file sempre aperto in Cursor come riferimento.**
> È il documento master: architettura, convenzioni, struttura directory e mappa fasi.

---

## Stack Tecnologico

| Layer          | Tecnologia                        | Versione   |
|----------------|-----------------------------------|------------|
| Backend        | Django + Django REST Framework    | 4.2 / 3.14 |
| Autenticazione | SimpleJWT                         | 5.3        |
| Frontend       | React + TypeScript                | 18 / 5.x   |
| Build tool     | Vite                              | 5.x        |
| Database       | MySQL                             | 8.0        |
| Cache / WS     | Redis                             | 7          |
| WebSocket      | Django Channels + Daphne          | 4.x        |
| Container      | Docker + Docker Compose           | latest     |
| Reverse Proxy  | Nginx                             | 1.25       |

---

## Struttura Directory del Progetto

```
axdoc/
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py          # settings comuni
│   │   │   ├── development.py   # DEBUG=True, console email
│   │   │   └── production.py    # DEBUG=False, HTTPS, S3
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py              # Channels (WebSocket)
│   ├── apps/
│   │   ├── authentication/      # login, logout, JWT, MFA, SSO, LDAP
│   │   ├── users/               # User model, ruoli, import CSV
│   │   ├── organizations/       # Unità Organizzative (UO), gruppi
│   │   ├── documents/           # Document, DocumentVersion, cartelle
│   │   ├── metadata/            # MetadataStructure, campi dinamici, template
│   │   ├── workflows/           # WorkflowTemplate, WorkflowInstance, step
│   │   ├── protocols/           # Protocol, numerazione progressiva
│   │   ├── dossiers/            # Dossier (fascicolo), archiviazione
│   │   ├── signatures/          # Firma digitale CADES/PADES, conservazione
│   │   ├── sharing/             # Condivisione link interni/esterni
│   │   ├── search/              # Full-text search, indicizzazione
│   │   ├── notifications/       # Notifiche in-app, email
│   │   ├── audit/               # AuditLog, tracciamento attività
│   │   ├── chat/                # Chat real-time, videochiamata WebRTC
│   │   └── admin_panel/         # Licenza, backup, health check, metriche
│   ├── requirements.txt
│   ├── Dockerfile
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/            # LoginForm, MFAVerifyModal, SSOButtons
│   │   │   ├── users/           # UserTable, UserForm, ImportUsersModal
│   │   │   ├── organizations/   # OUTree, OUForm
│   │   │   ├── documents/       # FileExplorer, DocumentDetailPanel
│   │   │   ├── metadata/        # MetadataStructureForm, DynamicForm
│   │   │   ├── workflows/       # WorkflowBuilder, WorkflowStatusBadge
│   │   │   ├── protocols/       # ProtocolTable, ProtocolForm
│   │   │   ├── dossiers/        # DossierCard, DossierForm
│   │   │   ├── sharing/         # ShareModal, ShareListPanel
│   │   │   ├── notifications/   # NotificationBell, NotificationPanel
│   │   │   ├── chat/            # ChatPanel, ChatWindow, VideoCallModal
│   │   │   └── ui/              # Button, Modal, Badge, Table, ecc.
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── WorkflowsPage.tsx
│   │   │   ├── ProtocolsPage.tsx
│   │   │   ├── DossiersPage.tsx
│   │   │   ├── UsersPage.tsx
│   │   │   ├── MetadataPage.tsx
│   │   │   ├── SearchPage.tsx
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── AdminPage.tsx
│   │   │   ├── ChatPage.tsx
│   │   │   └── PublicSharePage.tsx   # Accesso senza login
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useChatRoom.ts
│   │   │   └── useWebRTC.ts
│   │   ├── services/             # chiamate API (axios)
│   │   ├── store/                # Zustand stores
│   │   ├── types/                # TypeScript interfaces
│   │   └── utils/
│   ├── e2e/                      # Test Playwright
│   ├── package.json
│   └── vite.config.ts
├── nginx/
│   ├── nginx.conf
│   └── ssl/
├── scripts/
│   ├── backup.sh
│   └── restore.sh
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

---

## Ruoli Utente

| Ruolo           | Codice      | Permessi principali |
|-----------------|-------------|---------------------|
| **Operatore**   | `OPERATOR`  | Lavora sui documenti assegnati, compila metadati, avvia upload |
| **Revisore**    | `REVIEWER`  | Revisiona documenti, richiede modifiche, guida operatori |
| **Approvatore** | `APPROVER`  | Approva/rifiuta documenti, firma digitale, avvia protocollazione |
| **Amministratore** | `ADMIN`  | Gestione completa: utenti, UO, workflow, metadati, reportistica |

---

## Mappa Completa delle 16 Fasi

| # | File | Contenuto | Requisiti coperti |
|---|------|-----------|-------------------|
| 00 | `FASE_00_OVERVIEW.md` | **Questo file** — architettura, stack, ruoli | — |
| 01 | `FASE_01_SETUP_AUTH.md` | Docker, Django, React, JWT, login/logout, blocco, reset password | RF-001..010 |
| 02 | `FASE_02_USERS_UO.md` | Gestione utenti, inviti email, unità organizzative con gerarchia | RF-011..027 |
| 03 | `FASE_03_MFA_SSO_LDAP.md` | MFA TOTP (Google Auth), SSO OAuth2 Google/Microsoft, LDAP/AD | RF-002, RF-008, RF-009, RNF-008 |
| 04 | `FASE_04_IMPORT_GRUPPI.md` | Import utenti CSV/Excel, gruppi utenti, cifratura on-demand, licenza | RF-016, RF-017 |
| 05 | `FASE_05_DOCUMENTS.md` | Documenti, cartelle, upload/download, versioning, lock, allegati | RF-028..039 |
| 06 | `FASE_06_METADATA.md` | Strutture metadati dinamiche, validazione, form generati | RF-040..047 |
| 07 | `FASE_07_TEMPLATE_SCANNER.md` | Template DOCX con segnaposto, conversione AGID, PDF da scansione + OCR | RF-047, AGID |
| 08 | `FASE_08_WORKFLOW.md` | Workflow multi-step RACI, approvazione, rifiuto, richiesta modifiche | RF-048..057 |
| 09 | `FASE_09_PROTOCOLS_DOSSIERS.md` | Protocollazione con numerazione progressiva, fascicoli, archiviazione | RF-058..069 |
| 10 | `FASE_10_FIRMA_CONSERVAZIONE.md` | Firma CADES/PADES, OTP, conservazione digitale AGID, provider Aruba | RF-075..080 |
| 11 | `FASE_11_CONDIVISIONE.md` | Condivisione doc/protocolli con interni ed esterni via link email | AXDOC "Condivisione" |
| 12 | `FASE_12_SEARCH_NOTIFICATIONS.md` | Ricerca full-text, filtri avanzati, notifiche in-app, audit log | RF-070..074, RNF-007 |
| 13 | `FASE_13_CHAT_VIDEOCHIAMATA.md` | Chat real-time WebSocket + Redis, videochiamata WebRTC | AXDOC "Chat e videochiamata" |
| 14 | `FASE_14_DASHBOARD_FINAL.md` | Dashboard per ruolo, test E2E Playwright, security hardening | RNF-003..006, RNF-009..011 |
| 15 | `FASE_15_BACKUP_MONITORING_INFRA.md` | Backup automatici, health check, logging JSON, nginx SSL, cifratura riposo | RNF-001..002, RNF-012..024 |

---

## Dipendenze tra Fasi

```
01 ──► 02 ──► 03
        │
        ├──► 04
        │
        └──► 05 ──► 06 ──► 07
                    │
                    ├──► 08 ──► 09 ──► 10
                    │           │
                    │           └──► 11
                    │
                    └──► 12 ──► 13 ──► 14 ──► 15
```

> Le fasi **03** e **04** si possono sviluppare **in parallelo** con le fasi 05-07,
> purché la FASE 02 sia completata.
> La Fase **11** può partire non appena la Fase **05** è completata.

---

## Convenzioni di Sviluppo

### Backend (Python/Django)
- Formattazione: **black** + **isort** + **flake8**
- Test: **pytest** + **pytest-django** — ogni app ha `tests/` con test unitari e di integrazione
- Ogni model ha `__str__` e docstring
- Ogni ViewSet ha docstring sull'endpoint
- UUID come primary key su tutti i modelli principali
- Soft delete (campo `is_deleted`) invece di DELETE fisico dove indicato
- `created_at` e `updated_at` su tutti i modelli con `auto_now_add` / `auto_now`
- Variabili d'ambiente tramite `django-environ` — nessun valore hardcoded

### Frontend (TypeScript/React)
- Formattazione: **eslint** + **prettier**
- Test unitari: **Vitest** + **React Testing Library**
- Test E2E: **Playwright** (FASE 14)
- Ogni componente ha il suo file di test `*.test.tsx`
- State globale: **Zustand**
- Chiamate API: **Axios** + **TanStack Query** per caching
- Routing: **React Router DOM v6**
- Stili: **Tailwind CSS**
- Form: **React Hook Form** + **Zod** per validazione

### Git
- Branch per fase: `feature/fase-XX-nome`
- Commit dopo ogni STEP completato con test passanti
- Formato commit: `feat(fase-XX): descrizione breve`

---

## Struttura di ogni file FASE_XX

Ogni file di fase è strutturato così:

```
FASE_XX_NOME.md
├── Fonte nei documenti di analisi   ← requisito originale
├── Prerequisito                     ← fase precedente richiesta
├── CHECKLIST DI COMPLETAMENTO       ← verifica prima di andare avanti
├── STEP XX.1 — Modelli / Backend
│   └── Prompt completo copia-incolla per Cursor
├── STEP XX.2 — API / Views
│   └── Prompt completo copia-incolla per Cursor
├── STEP XX.3 — Frontend
│   └── Prompt completo copia-incolla per Cursor
└── TEST INTEGRAZIONE FASE XX        ← esegui sempre alla fine
```

**Regola d'oro:** non passare alla fase successiva finché tutti i ✅ della checklist non sono soddisfatti.

---

## Variabili d'Ambiente (.env)

```env
# ── Django ───────────────────────────────────────────────
SECRET_KEY=cambia-questa-chiave-in-produzione
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings.development

# ── Database ─────────────────────────────────────────────
DB_NAME=axdoc
DB_USER=axdoc
DB_PASSWORD=axdoc_password
DB_HOST=db
DB_PORT=3306

# ── Redis ────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── JWT ──────────────────────────────────────────────────
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# ── Email ────────────────────────────────────────────────
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.esempio.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@axdoc.local

# ── Frontend ─────────────────────────────────────────────
VITE_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000

# ── Cifratura campi sensibili ─────────────────────────────
# Genera con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY=

# ── MFA / SSO ────────────────────────────────────────────
GOOGLE_OAUTH2_CLIENT_ID=
GOOGLE_OAUTH2_CLIENT_SECRET=
MICROSOFT_OAUTH2_CLIENT_ID=
MICROSOFT_OAUTH2_CLIENT_SECRET=
MICROSOFT_TENANT_ID=common

# ── LDAP (opzionale) ─────────────────────────────────────
LDAP_ENABLED=false
LDAP_SERVER_URI=ldap://dc.azienda.com
LDAP_BIND_DN=
LDAP_BIND_PASSWORD=
LDAP_USER_BASE_DN=
LDAP_GROUP_BASE_DN=

# ── Firma digitale / Conservazione ───────────────────────
SIGNATURE_PROVIDER=mock          # mock | aruba
CONSERVATION_PROVIDER=mock       # mock | aruba
ARUBA_SIGN_API_URL=
ARUBA_SIGN_API_KEY=
ARUBA_CONSERVATION_API_URL=
ARUBA_CONSERVATION_API_KEY=

# ── Backup ───────────────────────────────────────────────
BACKUP_DIR=/backups/db
BACKUP_RETENTION_DAYS=30

# ── Monitoring (opzionale) ───────────────────────────────
SENTRY_DSN=
```

---

## Comandi Utili di Riferimento

```bash
# ── Avvio sviluppo ───────────────────────────────────────
docker-compose up -d
docker-compose logs -f backend

# ── Backend ──────────────────────────────────────────────
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend pytest                          # tutti i test
docker-compose exec backend pytest apps/authentication/ -v  # test singola app
docker-compose exec backend pytest --cov=apps --cov-report=term-missing

# ── Frontend ─────────────────────────────────────────────
docker-compose exec frontend npm run dev
docker-compose exec frontend npm run test -- --run          # unit test
docker-compose exec frontend npm run build                  # verifica build
docker-compose exec frontend npx playwright test            # E2E (FASE 14)

# ── Database ─────────────────────────────────────────────
docker-compose exec db mysql -u axdoc -paxdoc_password axdoc

# ── Produzione ───────────────────────────────────────────
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker-compose exec backend python manage.py collectstatic --noinput
```
