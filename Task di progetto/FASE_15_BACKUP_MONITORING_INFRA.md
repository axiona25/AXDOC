# AXDOC — FASE 15
# Backup, Monitoring, Infrastruttura Produzione

## Fonte nei documenti di analisi

**Backup** — requisiti_documentale_estesi.docx:
> RNF-022: Backup giornalieri
> RNF-023: Ripristino dati
> RNF-024: Retention backup

**Monitoraggio** — Documento Tecnico vDocs:
> "7.5 Monitoraggio e Logging: Un sistema di monitoraggio deve essere implementato 
> per rilevare eventuali problemi di prestazioni o anomalie nell'infrastruttura."

**Disponibilità** — requisiti_documentale_estesi.docx:
> RNF-012: Disponibilità 99.5%
> RNF-013: Ridondanza servizi
> RNF-014: Disaster recovery

**Scalabilità** — requisiti_documentale_estesi.docx:
> RNF-015: Scalabilità orizzontale
> RNF-016: Bilanciamento carico

**Cifratura a riposo** — requisiti_documentale_estesi.docx:
> RNF-002: Cifratura dati a riposo

**Nessuno di questi requisiti è implementato nelle fasi precedenti.**

**Prerequisito: FASE 14 completata. Questa fase è prevalentemente infrastrutturale.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Script backup automatico MySQL (RNF-022)
- [ ] Backup file system (upload files e media)
- [ ] Retention policy backup (RNF-024)
- [ ] Script ripristino backup (RNF-023)
- [ ] Health check endpoint per load balancer
- [ ] Monitoring con django-prometheus o Sentry
- [ ] Logging strutturato (JSON) per analisi
- [ ] docker-compose.prod.yml per produzione con nginx
- [ ] Configurazione nginx come reverse proxy + SSL
- [ ] Cifratura dati a riposo (RNF-002): MySQL encryption at rest
- [ ] Tutti i test passano

---

## STEP 9F.1 — Backup Automatico

### Prompt per Cursor:

```
Implementa il sistema di backup automatico del database e dei file.

Requisiti: RNF-022, RNF-023, RNF-024

Installa in requirements.txt:
  - django-dbbackup==4.1.*   # backup database

Aggiungi in `backend/config/settings/base.py`:
  INSTALLED_APPS += ['dbbackup']
  
  DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
  DBBACKUP_STORAGE_OPTIONS = {'location': env('BACKUP_DIR', default='/backups/db')}
  DBBACKUP_CLEANUP_KEEP = env.int('BACKUP_RETENTION_DAYS', default=30)
  DBBACKUP_CLEANUP_KEEP_MEDIA = env.int('BACKUP_MEDIA_RETENTION_DAYS', default=30)

Aggiungi in `docker-compose.yml`:
  Volume backup persistente:
    volumes:
      - backup_data:/backups

Crea `backend/scripts/backup.sh`:
  #!/bin/bash
  # Script backup completo: DB + media files
  # Uso: ./backup.sh [--full] [--db-only] [--media-only]
  
  set -e
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_ROOT="/backups"
  DB_BACKUP_DIR="$BACKUP_ROOT/db"
  MEDIA_BACKUP_DIR="$BACKUP_ROOT/media"
  LOG_FILE="$BACKUP_ROOT/backup.log"
  
  log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
  
  backup_database() {
    log "Avvio backup database MySQL..."
    python manage.py dbbackup --compress --noinput \
      --output-filename "db_backup_${TIMESTAMP}.dump.gz"
    log "Backup database completato."
  }
  
  backup_media() {
    log "Avvio backup media files..."
    tar -czf "$MEDIA_BACKUP_DIR/media_${TIMESTAMP}.tar.gz" \
      /app/media/ /app/uploads/
    log "Backup media completato. $(du -sh /app/media/ | cut -f1) compressi."
  }
  
  cleanup_old_backups() {
    RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
    log "Pulizia backup più vecchi di $RETENTION_DAYS giorni..."
    find "$DB_BACKUP_DIR" -name "*.dump.gz" -mtime +$RETENTION_DAYS -delete
    find "$MEDIA_BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    log "Pulizia completata."
  }
  
  # Esecuzione
  case "${1:-full}" in
    --db-only) backup_database ;;
    --media-only) backup_media ;;
    *) backup_database && backup_media ;;
  esac
  cleanup_old_backups
  log "Backup completato con successo."

Crea `backend/scripts/restore.sh`:
  #!/bin/bash
  # Ripristino da backup (RNF-023)
  # Uso: ./restore.sh --db backup_file.dump.gz [--media media_backup.tar.gz]
  
  set -e
  
  restore_database() {
    BACKUP_FILE="$1"
    log "ATTENZIONE: il ripristino sovrascriverà il database corrente."
    read -p "Confermi? (yes/NO): " confirm
    [ "$confirm" = "yes" ] || { log "Ripristino annullato."; exit 0; }
    
    log "Ripristino database da $BACKUP_FILE..."
    python manage.py dbrestore --input-filename "$BACKUP_FILE" --noinput
    log "Ripristino database completato."
    log "Esegui le migrations se necessario: python manage.py migrate"
  }
  
  restore_media() {
    BACKUP_FILE="$1"
    log "Ripristino media files da $BACKUP_FILE..."
    tar -xzf "$BACKUP_FILE" -C /
    log "Ripristino media completato."
  }

Crea management command `backend/apps/admin_panel/management/commands/backup_status.py`:
  - Lista ultimi 10 backup con: data, dimensione, tipo (db/media)
  - Stato: presente/mancante/corrotto
  - Uso: `python manage.py backup_status`

Aggiungi API:
  GET /api/admin/backups/:
    Solo ADMIN. Lista backup disponibili con info.
  
  POST /api/admin/backups/run/:
    Solo ADMIN. Avvia backup manuale (chiama backup.sh sincrono).
    Risponde: { "status": "completed", "db_file": "...", "media_file": "..." }

Crea cron schedule in `docker-compose.yml` (servizio cron):
  cron:
    image: alpine:3.18
    volumes:
      - ./backend:/app
      - backup_data:/backups
    command: >
      sh -c "echo '0 2 * * * cd /app && ./scripts/backup.sh >> /backups/cron.log 2>&1' 
             | crontab - && crond -f"
    # Backup ogni giorno alle 2:00 AM (RNF-022)
    depends_on:
      - db

TEST:
  - backup.sh --db-only: file .dump.gz creato
  - backup_status: lista file presenti
  - cleanup_old_backups: file più vecchi di RETENTION_DAYS eliminati

Esegui: `bash backend/scripts/backup.sh --db-only`
Esegui: `pytest backend/apps/admin_panel/tests/test_backup.py -v`
```

---

## STEP 9F.2 — Health Check e Monitoring

### Prompt per Cursor:

```
Implementa health check, logging strutturato e monitoring.

Requisiti: RNF-012, RNF-013, Documento Tecnico 7.5

Installa in requirements.txt:
  - django-health-check==3.18.*
  - sentry-sdk[django]==1.45.*   # error tracking (opzionale)
  - django-structlog==8.1.*      # logging strutturato JSON
  - django-prometheus==2.3.*     # metriche Prometheus (opzionale)

Aggiungi in `backend/config/settings/base.py`:

INSTALLED_APPS += [
  'health_check',
  'health_check.db',
  'health_check.cache',
  'health_check.storage',
  'health_check.contrib.migrations',
  'django_structlog',
]

# Logging strutturato JSON
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'json': {
      '()': 'structlog.stdlib.ProcessorFormatter',
      'processor': structlog.processors.JSONRenderer(),
    },
    'console': {
      'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
    }
  },
  'handlers': {
    'console': {
      'class': 'logging.StreamHandler',
      'formatter': 'json' if not DEBUG else 'console',
    },
    'file': {
      'class': 'logging.handlers.RotatingFileHandler',
      'filename': env('LOG_FILE', default='/var/log/axdoc/app.log'),
      'maxBytes': 10 * 1024 * 1024,  # 10MB
      'backupCount': 5,
      'formatter': 'json',
    },
  },
  'root': {'handlers': ['console'], 'level': 'INFO'},
  'loggers': {
    'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    'apps': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
  }
}

MIDDLEWARE += ['django_structlog.middlewares.RequestMiddleware']

# Sentry (opzionale, solo se DSN configurato)
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
  import sentry_sdk
  from sentry_sdk.integrations.django import DjangoIntegration
  sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()],
                  traces_sample_rate=0.1, send_default_pii=False)

Aggiungi in `config/urls.py`:
  path('health/', include('health_check.urls')),

Crea endpoint custom health check:
  GET /api/health/: (pubblico, per load balancer)
    Risponde rapidamente con:
    {
      "status": "healthy|degraded|unhealthy",
      "timestamp": "...",
      "checks": {
        "database": "ok|error",
        "redis": "ok|error",
        "storage": "ok|error",
        "migrations": "ok|pending"
      },
      "version": "1.0.0",
      "uptime_seconds": N
    }
    
    HTTP 200 se healthy/degraded, HTTP 503 se unhealthy
    
    Il load balancer usa questo endpoint per routing (RNF-013, RNF-016)

Crea `backend/apps/admin_panel/views.py` — aggiungi:
  GET /api/admin/metrics/:
    Solo ADMIN. Metriche aggregate:
    - requests_per_minute (ultimi 5 min da strutlog)
    - avg_response_time_ms
    - error_rate_percent
    - active_websocket_connections (da channels)
    - queue_depth (jobs in attesa, N/A senza celery)

Aggiorna LicensePage.tsx (Fase 9D):
  Aggiungi sezione "Salute del Sistema":
  - SystemHealthWidget: 
    * chiama /api/health/ ogni 60 secondi
    * Semaforo visivo: verde/giallo/rosso per ogni check
    * Uptime display

TEST:
  - /health/: risponde 200 con checks
  - Simula DB down: /health/ → status=unhealthy, HTTP 503
  - Log strutturato: ogni request genera log JSON con user_id, path, duration_ms

Esegui: `pytest backend/apps/admin_panel/tests/test_health.py -v`
```

---

## STEP 9F.3 — Configurazione Produzione con Nginx

### Prompt per Cursor:

```
Crea la configurazione completa per il deploy in produzione.

Requisiti: RNF-001 (HTTPS/TLS), RNF-013 (ridondanza), RNF-015/016 (scalabilità)

Crea `nginx/nginx.conf`:

upstream backend {
  # Per scalabilità orizzontale: aggiungere più istanze backend
  server backend:8000;
  # server backend2:8000;  # seconda istanza per ridondanza
  keepalive 32;
}

upstream frontend {
  server frontend:3000;
}

server {
  listen 80;
  server_name _;
  # Redirect tutto su HTTPS (RNF-001)
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl http2;
  server_name _;
  
  # SSL/TLS (RNF-001)
  ssl_certificate /etc/nginx/ssl/cert.pem;
  ssl_certificate_key /etc/nginx/ssl/key.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
  ssl_prefer_server_ciphers off;
  ssl_session_cache shared:SSL:10m;
  ssl_session_timeout 1d;
  
  # Security headers (RNF-005)
  add_header X-Frame-Options DENY;
  add_header X-Content-Type-Options nosniff;
  add_header X-XSS-Protection "1; mode=block";
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';";
  
  # Upload file grandi (RNF-011: 200MB)
  client_max_body_size 210M;
  
  # Timeout
  proxy_read_timeout 300s;
  proxy_connect_timeout 75s;
  
  # API Backend
  location /api/ {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
  
  # WebSocket (Django Channels)
  location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;  # 24h per WebSocket
  }
  
  # Health check (no log per non inquinare i log)
  location /health/ {
    proxy_pass http://backend;
    access_log off;
  }
  
  # File statici Django (admin, DRF browsable API)
  location /static/ {
    alias /app/staticfiles/;
    expires 1y;
    add_header Cache-Control "public, immutable";
  }
  
  # File media (upload utenti) — con autenticazione!
  # I file media NON devono essere serviti direttamente senza autenticazione
  # Il backend gestisce /api/documents/{id}/download/ con auth
  location /media/ {
    deny all;  # Blocca accesso diretto, passa sempre per il backend
  }
  
  # Frontend React
  location / {
    proxy_pass http://frontend;
    proxy_set_header Host $host;
  }
}

Crea `docker-compose.prod.yml`:
  Override per produzione che aggiunge:
  - nginx service con volume SSL
  - Variabili produzione (DEBUG=False, HTTPS, ecc.)
  - Healthcheck su tutti i container
  - Restart policy: always
  - Resource limits

Crea `nginx/ssl/README.md`:
  Istruzioni per ottenere certificato SSL:
  - Let's Encrypt con certbot: `certbot certonly --nginx -d yourdomain.com`
  - Self-signed per test: 
    `openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem`

Crea `backend/config/settings/production.py`:
  Estende base.py con tutte le impostazioni sicure:
  - DEBUG = False
  - ALLOWED_HOSTS da env
  - SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  - SESSION_COOKIE_SECURE = True
  - CSRF_COOKIE_SECURE = True
  - SECURE_SSL_REDIRECT = False (gestito da nginx)
  - STATIC_ROOT = '/app/staticfiles/'
  - MEDIA_ROOT = '/app/media/'
  - DBBACKUP_STORAGE su S3 o filesystem esterno

Aggiorna `README.md` con sezione Deploy Produzione:
  ```bash
  # Produzione con nginx
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
  
  # Colleziona static files
  docker-compose exec backend python manage.py collectstatic --noinput
  
  # Verifica health
  curl https://yourdomain.com/health/
  ```

TEST:
  - `docker-compose -f docker-compose.yml -f docker-compose.prod.yml config` 
    → valida la configurazione senza errori
  - Health endpoint risponde 200
  - Redirect HTTP→HTTPS funziona (con certificato self-signed)

Verifica:
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml config
  → Nessun errore YAML
```

---

## STEP 9F.4 — Cifratura Dati a Riposo

### Prompt per Cursor:

```
Documenta e implementa la cifratura dei dati a riposo (RNF-002).

La cifratura a riposo si implementa su più livelli:

LIVELLO 1 — MySQL Encryption at Rest:
  Aggiungi al servizio MySQL in docker-compose.yml:
  
  db:
    command: >
      mysqld
      --innodb-encrypt-tables=ON
      --innodb-encrypt-log=ON
      --innodb-encryption-key-id=1
      --early-plugin-load=keyring_file.so
      --keyring-file-data=/var/lib/mysql-keyring/keyring
  
  Crea file di documentazione `docs/ENCRYPTION_AT_REST.md`:
    Guida completa per:
    - Configurare MySQL InnoDB tablespace encryption
    - Gestire le chiavi di cifratura
    - Backup delle chiavi (CRITICO: perdita chiavi = perdita dati)
    - Verifica che la cifratura sia attiva: 
      SELECT * FROM information_schema.INNODB_TABLESPACES_ENCRYPTION;

LIVELLO 2 — Campi sensibili cifrati nell'applicazione:
  Installa: django-encrypted-model-fields==0.6.*
  
  In settings: FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY')
  Aggiungi a .env.example: FIELD_ENCRYPTION_KEY=  # genera con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  
  Cifra i seguenti campi:
  - User.phone → EncryptedCharField
  - SignatureRequest.provider_response → EncryptedJSONField (contiene dati provider)
  - SystemLicense.license_key → EncryptedCharField
  - UserInvitation.token → rimane CharField ma la email → EncryptedEmailField
  
  Crea migration: `python manage.py makemigrations --name encrypt_sensitive_fields`

LIVELLO 3 — File media cifrati (opzionale, avanzato):
  Documenta l'opzione di usare storage S3 con cifratura server-side:
  
  In `docs/S3_STORAGE.md`:
    Configurazione per usare AWS S3 con SSE-S3 o SSE-KMS:
    - pip install django-storages boto3
    - settings: DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    - AWS_S3_ENCRYPTION = True
    - AWS_S3_OBJECT_PARAMETERS = {'ServerSideEncryption': 'AES256'}

Aggiorna /api/admin/system_info/ (Fase 9F.2):
  Aggiungi campi:
  - encryption_at_rest: bool (true se FIELD_ENCRYPTION_KEY configurato)
  - mysql_encryption: "enabled|unknown" (query a information_schema)
  - ssl_enabled: bool (true se HTTPS)

TEST:
  - Campo cifrato salvato: valore nel DB non leggibile in chiaro
  - Campo cifrato recuperato: valore originale corretto
  - Migration applicata senza errori

Esegui:
  `python manage.py makemigrations --check`  (no migrations pending)
  `pytest backend/ -k "encrypt" -v`
```

---

## TEST INTEGRAZIONE FASE 9F

### Prompt per Cursor:

```
Test di integrazione Fase 9F.

1. Test backup:
   a) `docker-compose exec cron sh -c "cd /app && ./scripts/backup.sh --db-only"`
      → file .dump.gz creato in /backups/db/
   b) GET /api/admin/backups/ → lista backup con file appena creato
   c) POST /api/admin/backups/run/ → backup completo via API
   d) Verifica retention: crea file fittizio più vecchio di 30 giorni
      `touch -d "31 days ago" /backups/db/old_backup.dump.gz`
      Esegui cleanup → file eliminato

2. Test health check:
   a) GET /health/ → risposta JSON con tutti i check verdi
   b) `docker-compose stop redis`
      GET /health/ → redis: "error", status: "degraded", HTTP 200
   c) `docker-compose start redis`
      GET /health/ → status: "healthy"
   d) GET /api/health/ → stesso risultato

3. Test nginx produzione:
   a) `docker-compose -f docker-compose.yml -f docker-compose.prod.yml config`
      → No errori YAML
   b) Genera certificato self-signed:
      `openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
       -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem \
       -subj "/C=IT/ST=Italia/L=Milano/O=Test/CN=localhost"`
   c) `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
   d) `curl -k https://localhost/health/` → risponde 200
   e) `curl -k http://localhost/api/` → redirect 301 a HTTPS

4. Test cifratura:
   a) Aggiungi numero di telefono a utente → salvato cifrato
   b) Verifica nel DB: `SELECT phone FROM users_user WHERE id=...`
      → valore cifrato (non leggibile)
   c) GET /api/users/me/ → numero decifrato correttamente

5. Test logging strutturato:
   a) Fai alcune richieste API
   b) Verifica log: `docker-compose logs backend | head -20`
      → ogni log è JSON valido con: timestamp, method, path, status, duration_ms

Crea `FASE_09F_TEST_REPORT.md`.
```
