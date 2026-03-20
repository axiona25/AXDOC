# IT Docs — Indice Completo Fasi di Sviluppo
## Sistema di Gestione Documentale Aziendale

**Stack:** Django 4.2 (BE) · React 18 + TypeScript (FE) · MySQL 8.0 (DB)  
**Totale fasi:** 16 · **Totale requisiti coperti:** RF-001..RF-080 + RNF-001..RNF-024

---

## Ordine di Sviluppo

| # | File | Contenuto | Requisiti | Prerequisiti |
|---|------|-----------|-----------|--------------|
| 00 | `FASE_00_OVERVIEW.md` | Architettura, stack, ruoli, convenzioni | — | — |
| 01 | `FASE_01_SETUP_AUTH.md` | Docker, JWT, login/logout, blocco account, reset password | RF-001..010 | — |
| 02 | `FASE_02_USERS_UO.md` | Gestione utenti, inviti email, unità organizzative con gerarchia | RF-011..027 | Fase 01 |
| 03 | `FASE_03_MFA_SSO_LDAP.md` | MFA TOTP, SSO Google/Microsoft, LDAP/Active Directory | RF-002, RF-008, RF-009, RNF-008 | Fase 01 |
| 04 | `FASE_04_IMPORT_GRUPPI.md` | Import utenti CSV/Excel, gruppi trasversali, cifratura on-demand, licenza | RF-016, RF-017 | Fase 02 |
| 05 | `FASE_05_DOCUMENTS.md` | Documenti, cartelle, upload/download, versioning, lock, allegati, permessi | RF-028..039 | Fase 02 |
| 06 | `FASE_06_METADATA.md` | Strutture metadati dinamiche, validazione, form generati | RF-040..047 | Fase 05 |
| 07 | `FASE_07_TEMPLATE_SCANNER.md` | Template DOCX con segnaposto, conversione AGID, PDF da scansione + OCR | RF-047, RNF collaudo AGID | Fase 06 |
| 08 | `FASE_08_WORKFLOW.md` | Workflow multi-step RACI, approvazione, rifiuto, richiesta modifiche | RF-048..057 | Fase 06 |
| 09 | `FASE_09_PROTOCOLS_DOSSIERS.md` | Protocollazione con numerazione progressiva, fascicoli, archiviazione | RF-058..069 | Fase 08 |
| 10 | `FASE_10_FIRMA_CONSERVAZIONE.md` | Firma digitale CADES/PADES, OTP, conservazione digitale, provider Aruba | RF-075..080 | Fase 09 |
| 11 | `FASE_11_CONDIVISIONE.md` | Condivisione doc/protocolli con interni ed esterni, link temporanei | IT_Docs "Condivisione" | Fase 05 |
| 12 | `FASE_12_SEARCH_NOTIFICATIONS.md` | Ricerca full-text, filtri avanzati, notifiche in-app, audit log | RF-070..074, RNF-007 | Fase 08 |
| 13 | `FASE_13_CHAT_VIDEOCHIAMATA.md` | Chat real-time WebSocket, videochiamata WebRTC, presenza utenti | IT_Docs "Chat e videochiamata" | Fase 12 |
| 14 | `FASE_14_DASHBOARD_FINAL.md` | Dashboard per ruolo, test E2E Playwright, security hardening, README | RNF-003..006, RNF-009..011 | Fase 13 |
| 15 | `FASE_15_BACKUP_MONITORING_INFRA.md` | Backup automatici, health check, logging JSON, nginx SSL, cifratura a riposo | RNF-001..002, RNF-012..016, RNF-022..024 | Fase 14 |

---

## Dipendenze tra Fasi (grafo)

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

**Nota:** Le Fasi 03 e 04 possono essere sviluppate in parallelo con le Fasi 05-07, 
purché la Fase 02 sia completata. La Fase 11 può essere sviluppata dopo la Fase 05.

---

## Requisiti Funzionali — Mappa Completa

| Area | RF | Fase |
|------|----|------|
| Autenticazione e accessi | RF-001..010 | 01, 03 |
| Gestione utenti | RF-011..020 | 02, 04 |
| Unità organizzative | RF-021..027 | 02 |
| Gestione documenti | RF-028..039 | 05 |
| Metadati | RF-040..047 | 06, 07 |
| Workflow documentale | RF-048..057 | 08 |
| Protocollazione | RF-058..063 | 09 |
| Fascicoli | RF-064..069 | 09 |
| Ricerca | RF-070..074 | 12 |
| Firma digitale e conservazione | RF-075..080 | 10 |

---

## Requisiti Non Funzionali — Mappa Completa

| Area | RNF | Fase |
|------|-----|------|
| Sicurezza (HTTPS, cifratura, RBAC, SQL inj., XSS, CSRF, Audit, MFA) | RNF-001..008 | 03, 14, 15 |
| Prestazioni (1000 utenti, API <2s, upload 200MB) | RNF-009..011 | 14 |
| Disponibilità (99.5%, ridondanza, disaster recovery) | RNF-012..014 | 15 |
| Scalabilità (orizzontale, load balancing) | RNF-015..016 | 15 |
| Manutenibilità (microservizi, codice documentato, zero downtime) | RNF-017..019 | 14 |
| Compatibilità (browser, OS) | RNF-020..021 | 14 |
| Backup (giornalieri, ripristino, retention) | RNF-022..024 | 15 |

---

## Come Usare Questi File con Cursor

1. **Apri `FASE_00_OVERVIEW.md`** e tienilo sempre aperto come riferimento
2. **Procedi fase per fase**, nell'ordine numerico indicato
3. **Ogni fase contiene più STEP** — copiali uno alla volta in Cursor
4. **Non passare alla fase successiva** finché tutti i test della checklist non sono ✅
5. **In caso di errori**, usa il prompt di integrazione finale di ogni fase per diagnosticarli

### Struttura di ogni fase
```
FASE_XX.md
├── Obiettivo
├── CHECKLIST DI COMPLETAMENTO  ← verifica prima di andare avanti
├── STEP XX.1 — [Modelli/Backend]
│   └── Prompt completo copia-incolla per Cursor
├── STEP XX.2 — [API/Views]
│   └── Prompt completo copia-incolla per Cursor
├── STEP XX.3 — [Frontend]
│   └── Prompt completo copia-incolla per Cursor
└── TEST INTEGRAZIONE  ← esegui sempre alla fine della fase
```

---

## Stack Tecnologico Completo

### Backend
| Libreria | Uso | Fase |
|----------|-----|------|
| Django 4.2 + DRF | Framework principale | 01 |
| SimpleJWT | Autenticazione JWT | 01 |
| django-environ | Variabili d'ambiente | 01 |
| pyotp + qrcode | MFA TOTP | 03 |
| social-auth-app-django | SSO OAuth2 | 03 |
| django-auth-ldap | LDAP/Active Directory | 03 |
| cryptography | Cifratura (MFA secret, docs) | 03, 04 |
| openpyxl + tablib | Import CSV/Excel | 04 |
| django-encrypted-model-fields | Cifratura campi DB | 04, 15 |
| PyPDF2 + python-docx | Estrazione testo, template | 07, 12 |
| pytesseract + img2pdf | OCR e PDF da scansione | 07 |
| reportlab + pypdf | Generazione PDF/AGID | 07 |
| channels + daphne | WebSocket real-time | 13 |
| channels-redis | Channel layer Redis | 13 |
| social-auth-app-django | SSO provider | 03 |
| django-health-check | Health check endpoint | 15 |
| django-structlog | Logging JSON strutturato | 15 |
| django-dbbackup | Backup database | 15 |
| drf-spectacular | Swagger/OpenAPI docs | 14 |

### Frontend
| Libreria | Uso | Fase |
|----------|-----|------|
| React 18 + TypeScript | Framework | 01 |
| Vite | Build tool | 01 |
| React Router DOM | Routing | 01 |
| Axios | HTTP client | 01 |
| Zustand | State management | 01 |
| React Hook Form + Zod | Form e validazione | 01 |
| TanStack Query | Server state / caching | 01 |
| Tailwind CSS | Styling | 01 |
| Recharts | Grafici dashboard | 14 |
| simple-peer | WebRTC videochiamate | 13 |
| Playwright | Test E2E | 14 |
| Vitest + RTL | Unit test | 01 |

### Infrastruttura
| Componente | Uso | Fase |
|------------|-----|------|
| Docker + Docker Compose | Containerizzazione | 01 |
| MySQL 8.0 | Database principale | 01 |
| Redis 7 | Channel layer, cache, sessioni | 13 |
| Nginx | Reverse proxy, SSL termination | 15 |
| LibreOffice headless | Conversione documenti in PDF | 07 |
| Tesseract OCR | OCR documenti scansionati | 07 |

---

## Variabili d'Ambiente Principali

```env
# Database
DB_NAME=itdocs
DB_USER=itdocs
DB_PASSWORD=
DB_HOST=db

# Security
SECRET_KEY=
FIELD_ENCRYPTION_KEY=    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DEBUG=True

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
DEFAULT_FROM_EMAIL=noreply@itdocs.local

# Redis
REDIS_URL=redis://redis:6379/0

# Frontend
VITE_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000

# MFA / SSO
SIGNATURE_PROVIDER=mock         # mock | aruba
CONSERVATION_PROVIDER=mock      # mock | aruba
GOOGLE_OAUTH2_CLIENT_ID=
MICROSOFT_OAUTH2_CLIENT_ID=
LDAP_ENABLED=false

# Backup
BACKUP_DIR=/backups/db
BACKUP_RETENTION_DAYS=30

# Sentry (opzionale)
SENTRY_DSN=
```
