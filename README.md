# AXDOC — Sistema di Gestione Documentale

Sistema di gestione documentale con workflow, protocollazione, fascicoli, firma digitale, conservazione, chat e videochiamata.

## Requisiti di sistema

- **Docker** 24+ e **Docker Compose** v2
- (Opzionale) Node.js 18+ e Python 3.11+ per sviluppo locale

## Quick Start (Docker)

```bash
# 1. Clona il repository
git clone <repo-url>
cd AXDOC

# 2. Copia e configura le variabili d'ambiente
cp backend/.env.example backend/.env
# Modifica backend/.env con i tuoi valori (DB, SECRET_KEY, ecc.)

# 3. Avvia tutti i servizi
docker-compose up -d --build

# 4. Esegui le migrations
docker-compose exec backend python manage.py migrate

# 5. Crea il superuser
docker-compose exec backend python manage.py createsuperuser

# 6. (Opzionale) Carica dati di esempio
# docker-compose exec backend python manage.py loaddata e2e_fixtures.json

# Accedi a: http://localhost:3000 (frontend)
# API: http://localhost:8000/api/
```

## Struttura del progetto

- **backend/** — Django (DRF), app: authentication, documents, metadata, protocols, workflows, dossiers, signatures, sharing, notifications, search, audit, chat, dashboard
- **frontend/** — React + TypeScript + Vite, Tailwind CSS
- **Task di progetto/** — Specifiche per fase (FASE_01–FASE_14)

## Variabili d'ambiente principali

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| SECRET_KEY | Chiave Django | (obbligatoria) |
| DEBUG | Modalità debug | False |
| DB_NAME, DB_USER, DB_PASSWORD, DB_HOST | MySQL | axdoc, axdoc, ..., db |
| REDIS_URL | Redis per Channels | redis://redis:6379/0 |
| CORS_ALLOWED_ORIGINS | Origini CORS | http://localhost:3000 |
| FRONTEND_URL | URL frontend (email, redirect) | http://localhost:3000 |
| ALLOWED_HOSTS | Host consentiti | localhost, 127.0.0.1 |

## API

- **Auth:** `/api/auth/login/`, `/api/auth/me/`, `/api/auth/change-password/`, MFA, SSO, inviti
- **Documenti:** `/api/documents/`, `/api/folders/`, versioni, allegati, metadati, lock
- **Workflow:** `/api/workflows/templates/`, `/api/workflows/instances/`
- **Protocolli:** `/api/protocols/`
- **Fascicoli:** `/api/dossiers/`
- **Ricerca:** `/api/search/`
- **Notifiche:** `/api/notifications/`
- **Audit:** `/api/audit/`
- **Chat:** `/api/chat/rooms/`, WebSocket `ws/chat/<room_id>/`
- **Dashboard:** `/api/dashboard/stats/`, `/api/dashboard/recent_documents/`, `/api/dashboard/my_tasks/`
- **Condivisione:** `/api/documents/<id>/share/`, `/api/public/share/<token>/`

## Eseguire i test

```bash
# Test backend
docker-compose exec backend pytest --cov=apps -v

# Test frontend unitari
cd frontend && npm run test -- --run

# Build frontend
cd frontend && npm run build
```

## Backup (FASE 15, RNF-022–024)

- **Script:** `backend/scripts/backup.sh` (--db-only | --media-only | full). Eseguire da root app: `cd /app && ./scripts/backup.sh`
- **Ripristino:** `backend/scripts/restore.sh --db file.dump.gz [--media file.tar.gz]`
- **Stato:** `python manage.py backup_status`
- **API (solo ADMIN):** `GET /api/admin/backups/`, `POST /api/admin/backups/run/`
- **Retention:** `BACKUP_RETENTION_DAYS` (default 30)

## Health check

- **GET /api/health/** — Pubblico, per load balancer. Risposta: `status` (healthy | degraded | unhealthy), `checks` (database, redis, storage, migrations), `uptime_seconds`. HTTP 503 se unhealthy.

## Deploy in produzione

1. Certificati SSL in `nginx/ssl/` (vedi `nginx/ssl/README.md`); per test self-signed:  
   `openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -subj "/CN=localhost"`
2. Avvio con nginx:  
   `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
3. Static files:  
   `docker-compose exec backend python manage.py collectstatic --noinput`
4. Verifica:  
   `curl -k https://localhost/api/health/`

Impostare `DEBUG=False`, `ALLOWED_HOSTS` e `SECRET_KEY`; usare `config.settings.production`.

## Credenziali default

Dopo `createsuperuser`: usare l’email e la password impostate. **Cambiare in produzione.**

---

FASE 14 — Dashboard, Security Hardening, documentazione.
