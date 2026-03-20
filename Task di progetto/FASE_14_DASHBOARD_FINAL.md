# AXDOC — FASE 14
# Dashboard, Test E2E e Security Hardening

## Obiettivo
Completare la Dashboard con reportistica, rifinire la UI,
implementare test E2E completi e preparare per il deploy.

**Prerequisito: FASE 13 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Dashboard con statistiche per ruolo
- [ ] Widget: fascicoli in lavorazione, approvati, in conservazione
- [ ] Widget: attività recenti
- [ ] Widget: step workflow pendenti
- [ ] UI responsive (mobile-friendly)
- [ ] Gestione profilo utente
- [ ] Impostazioni (tema, preferenze)
- [ ] Test E2E con Playwright o Cypress
- [ ] Performance: API < 2s (RNF-010)
- [ ] Security headers configurati
- [ ] README.md completo con istruzioni deploy
- [ ] Tutti i test unitari, di integrazione ed E2E passano

---

## STEP 8.1 — API Dashboard e Reportistica

### Prompt per Cursor:

```
Crea l'API per la dashboard in `backend/apps/documents/views.py` 
o una nuova app `backend/apps/dashboard/`.

Crea GET /api/dashboard/stats/:
  Risponde con dati diversi per ruolo:

  Per TUTTI:
  - my_pending_steps: count step workflow assegnati a me
  - my_documents: { total, draft, in_review, approved, rejected }
  - recent_activity: ultimi 10 AuditLog relativi ai miei documenti
  - unread_notifications: count

  Per ADMIN in più:
  - total_users: count utenti attivi
  - total_documents: count tutti i documenti
  - total_dossiers: { open, archived }
  - total_protocols: { count, this_month }
  - documents_by_status: { draft: N, in_review: N, approved: N, ... }
  - active_workflows: count istanze workflow attive
  - storage_used_mb: somma file sizes (DocumentVersion)

  Per APPROVER/REVIEWER in più:
  - pending_approvals: count documenti assegnati allo step corrente
  - dossiers_responsible: count fascicoli di cui sono responsabile

Crea GET /api/dashboard/recent_documents/:
  - Ultimi 10 documenti modificati accessibili all'utente
  - Include: titolo, stato, ultima modifica, autore

Crea GET /api/dashboard/my_tasks/:
  - Step workflow assegnati all'utente corrente (pending)
  - Raggruppati per documento
  - Con scadenza se presente

TEST:
  - Stats per ADMIN: include campi admin
  - Stats per OPERATOR: non include campi admin
  - recent_documents: solo documenti accessibili
  - my_tasks: solo step assegnati a me

Esegui: `pytest` su nuovi test
```

---

## STEP 8.2 — Frontend: Dashboard Completa

### Prompt per Cursor:

```
Crea la Dashboard completa nel frontend.

Leggi il file `frontend/src/services/` e crea `dashboardService.ts`:
  - getDashboardStats(): GET /api/dashboard/stats/
  - getRecentDocuments(): GET /api/dashboard/recent_documents/
  - getMyTasks(): GET /api/dashboard/my_tasks/

Crea `frontend/src/components/dashboard/`:

StatsCard.tsx:
  - Card con: icona, titolo, valore numerico principale, trend/sottotitolo
  - Varianti colore: blue, green, orange, red, gray

DocumentsByStatusChart.tsx:
  - Grafico a ciambella (donut) con stati documenti
  - Usa Recharts o Chart.js (già in dipendenze)
  - Legenda con colori per stato

RecentActivityFeed.tsx:
  - Lista attività recenti stile "social feed"
  - Ogni item: avatar utente, azione descritta, target, data relativa
  - Max 10 item, link "Vedi tutto" → /audit

PendingTasksWidget.tsx:
  - Lista task workflow pendenti per l'utente
  - Ogni task: documento, step richiesto, scadenza (se presente)
  - Badge urgente se scadenza < 2 giorni
  - Click → naviga al documento

RecentDocumentsWidget.tsx:
  - Tabella compatta: nome, stato, data, autore
  - Click → apre DocumentDetailPanel

Aggiorna `frontend/src/pages/DashboardPage.tsx` (route: /dashboard):

Layout dashboard per ruolo ADMIN:
  - Row 1: 4 StatsCard (Utenti, Documenti, Fascicoli, Protocolli)
  - Row 2: DocumentsByStatusChart + PendingTasksWidget
  - Row 3: RecentActivityFeed + RecentDocumentsWidget

Layout dashboard per OPERATOR/REVIEWER/APPROVER:
  - Row 1: 3 StatsCard (Documenti miei, Step pendenti, Notifiche)
  - Row 2: PendingTasksWidget (grande, prominente)
  - Row 3: RecentDocumentsWidget

Aggiorna il menu di navigazione con tutti i link:
  - Dashboard (tutti)
  - Documenti (tutti)
  - Protocolli (ADMIN, APPROVER)
  - Fascicoli (tutti)
  - Workflow (ADMIN per gestione, tutti per visualizzazione)
  - Utenti (ADMIN)
  - Organizzazioni (ADMIN)
  - Metadati (ADMIN)
  - Ricerca (tutti)
  - Audit (ADMIN)
  - Impostazioni (tutti per profilo)

Crea `frontend/src/pages/ProfilePage.tsx` (route: /profile):
  - Form modifica: nome, cognome, telefono, avatar (upload)
  - Sezione cambio password
  - Sezione MFA (placeholder per ora)

TEST Vitest:
  - DashboardPage ADMIN: tutte le widget renderizzate
  - DashboardPage OPERATOR: widget corrette per ruolo
  - PendingTasksWidget: badge urgente quando scadenza vicina
  - StatsCard: render valore e tendenza
```

---

## STEP 8.3 — Security Headers e Hardening

### Prompt per Cursor:

```
Configura i security headers e le misure di hardening.

Requisiti: RNF-001..RNF-008

Modifica `backend/config/settings/base.py`:

1. SECURE_BROWSER_XSS_FILTER = True (RNF-005)
2. SECURE_CONTENT_TYPE_NOSNIFF = True
3. X_FRAME_OPTIONS = 'DENY'
4. SECURE_HSTS_SECONDS = 31536000 (in production)
5. SECURE_HSTS_INCLUDE_SUBDOMAINS = True
6. SESSION_COOKIE_SECURE = True (in production)
7. CSRF_COOKIE_SECURE = True (in production)
8. SECURE_SSL_REDIRECT = True (in production)

Crea `backend/config/settings/production.py` che estende base con settings sicuri.

Aggiungi in `backend/apps/authentication/views.py` su LoginView:
- Rate limiting: max 10 login/minuto per IP
  Implementa con un semplice cache (Django cache framework)
  Usa: from django.core.cache import cache
  Key: f"login_attempts_{ip}"

Aggiungi validazione password forte:
  In settings: AUTH_PASSWORD_VALIDATORS con:
  - MinimumLengthValidator (8 char)
  - NumericPasswordValidator
  - CommonPasswordValidator
  Custom: UppercasePasswordValidator (almeno 1 maiuscola)
  Custom: SpecialCharPasswordValidator (almeno 1 carattere speciale)

Modifica DocumentVersion.file per salvataggio con nome oscurato:
  upload_to='documents/%Y/%m/{uuid4}' invece del nome originale
  (sicurezza: non esporre nome file nel percorso server)

Aggiungi in DocumentViewSet.download():
  - Verifica mime type del file prima di servirlo
  - Imposta header X-Content-Type-Options: nosniff

Configura CORS in modo restrittivo:
  CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')
  CORS_ALLOW_CREDENTIALS = True
  CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']

TEST:
  - Rate limiting: 11 tentativi login dallo stesso IP → 429
  - Password debole: 'password123' → errore validazione
  - Download file: Content-Disposition corretto
  - CORS: origine non autorizzata → 403

Esegui: `pytest backend/ -v --tb=short -k "security or rate_limit or password"`
```

---

## STEP 8.4 — Test E2E

### Prompt per Cursor:

```
Crea test E2E completi con Playwright.

Installa: `npm install --save-dev @playwright/test`
Configura: `playwright.config.ts` con baseURL http://localhost:3000

Crea `frontend/e2e/`:

auth.spec.ts:
  - Login con credenziali valide → dashboard
  - Login con credenziali errate → messaggio errore
  - 5 login falliti → account bloccato
  - Logout → redirect login
  - Pagine protette senza auth → redirect login

documents.spec.ts:
  - Upload documento → appare in file explorer
  - Navigazione cartelle
  - Download documento
  - Nuova versione documento
  - Ricerca per titolo

workflow.spec.ts:
  - ADMIN: crea workflow template con 2 step
  - Avvia workflow su documento
  - Revisore: approva step 1
  - Approvatore: approva step 2 → documento APPROVED
  - Rifiuto: documento REJECTED

protocols.spec.ts:
  - Crea protocollo in entrata → ID progressivo
  - Crea secondo protocollo → ID incrementato
  - Documento protocollato non modificabile

search.spec.ts:
  - Ricerca per titolo trova documento
  - Filtro per struttura metadati

Aggiungi script in `package.json`:
  "test:e2e": "playwright test"
  "test:e2e:ui": "playwright test --ui"

Crea `frontend/e2e/fixtures/`:
  - test-admin.json: credenziali admin di test
  - test-operator.json: credenziali operatore di test
  - sample.pdf: PDF di test per upload

Prima di eseguire i test E2E:
  - Assicurati che docker-compose sia up
  - Esegui seed del DB: `python manage.py loaddata e2e_fixtures.json`
  - Crea `backend/fixtures/e2e_fixtures.json` con dati iniziali

Esegui: `npm run test:e2e`
Tutti i test devono passare.
```

---

## STEP 8.5 — Performance e Ottimizzazioni

### Prompt per Cursor:

```
Ottimizza le performance per rispettare RNF-009 e RNF-010.

Requisiti: RNF-009 (1000 utenti concorrenti), RNF-010 (API < 2s)

Backend ottimizzazioni:

1. Aggiungi index ai campi più utilizzati nelle query:
   In ogni migration appropriata:
   - Document: index su (status, created_by, folder, is_deleted)
   - DocumentVersion: index su (document, is_current)
   - AuditLog: index su (user, action, timestamp)
   - Notification: index su (recipient, is_read, created_at)
   - Protocol: index su (organizational_unit, year, direction)
   
   Crea migration: `python manage.py makemigrations --name add_performance_indexes`

2. Ottimizza le query N+1 con select_related e prefetch_related:
   - DocumentViewSet.list: select_related('created_by', 'folder', 'metadata_structure')
     prefetch_related('allowed_users', 'allowed_ous')
   - WorkflowInstanceViewSet: prefetch step_instances con assigned_to
   - DossierViewSet: prefetch documents e protocols

3. Aggiungi paginazione ovunque mancante (max 100 risultati per chiamata)

4. Configura Django cache:
   In settings: CACHES con LocMemCache (sviluppo) o Redis (produzione)
   Cache su:
   - /api/dashboard/stats/ (TTL 60s, invalida su modifica)
   - /api/organizations/tree/ (TTL 300s)
   - /api/notifications/unread_count/ (TTL 30s)

5. Aggiungi select_for_update nella creazione protocolli:
   Verifica che ProtocolCounter.get_next_number() sia atomico

Frontend ottimizzazioni:

1. Code splitting con React.lazy per pagine pesanti:
   - WorkflowsPage, MetadataPage, DossierDetailPage

2. React Query con stale time appropriato:
   - Dashboard stats: staleTime 60s
   - Document list: staleTime 30s
   - Notifications: staleTime 15s

3. Virtualizzazione per liste lunghe:
   - DocumentTable con react-window se > 100 righe

4. Memoizzazione componenti pesanti:
   - FileExplorer con useMemo per albero cartelle

5. Ottimizza bundle:
   Esegui: `npm run build -- --analyze`
   Identifica chunk > 500KB e splitta

TEST PERFORMANCE:

Crea `backend/tests/test_performance.py`:
  - Misura tempo risposta /api/documents/ con 1000 documenti nel DB
    → deve essere < 2000ms
  - Misura /api/search/?q=test con 1000 documenti
    → deve essere < 3000ms
  - Verifica no N+1 queries (usa django-queries-count in test)

Esegui: `pytest backend/tests/test_performance.py -v --tb=short`
```

---

## STEP 8.6 — README e Documentazione Deploy

### Prompt per Cursor:

```
Crea la documentazione completa per il progetto.

Crea `README.md` nella root del progetto con:

# AXDOC — Sistema di Gestione Documentale

## Requisiti di sistema
- Docker 24+ e Docker Compose v2
- (Opzionale) Node.js 18+ e Python 3.11+ per sviluppo locale

## Quick Start (Docker)

```bash
# 1. Clona il repository
git clone ...
cd axdoc

# 2. Copia e configura le variabili d'ambiente
cp backend/.env.example backend/.env
# Modifica backend/.env con i tuoi valori

# 3. Avvia tutti i servizi
docker-compose up -d --build

# 4. Esegui le migrations
docker-compose exec backend python manage.py migrate

# 5. Crea il superuser
docker-compose exec backend python manage.py createsuperuser

# 6. (Opzionale) Carica dati di esempio
docker-compose exec backend python manage.py loaddata e2e_fixtures.json

# Accedi a: http://localhost:3000
```

## Struttura del Progetto
[descrizione directory]

## Variabili d'Ambiente
[tabella con tutte le var e descrizione]

## API Documentation
Dopo avvio: http://localhost:8000/api/docs/ (Swagger UI)

## Eseguire i Test
```bash
# Test backend
docker-compose exec backend pytest --cov=apps --cov-report=html

# Test frontend unitari
docker-compose exec frontend npm run test -- --run

# Test E2E (richiede docker-compose up)
npm run test:e2e
```

## Deploy in Produzione
[istruzioni per deploy con nginx + gunicorn + mysql]

## Credenziali Default
- Admin: admin@axdoc.local / Admin123! (CAMBIARE IN PRODUZIONE)

Crea anche `backend/docs/API.md` con lista di tutti gli endpoint.

Aggiungi Swagger/OpenAPI:
  - pip install drf-spectacular
  - Configura in settings e urls.py
  - GET /api/docs/ → Swagger UI
  - GET /api/schema/ → OpenAPI JSON

Aggiungi `backend/apps/management/commands/setup_demo_data.py`:
  Management command che crea:
  - 5 utenti con ruoli diversi
  - 3 UO con gerarchia
  - 2 strutture metadati
  - 1 workflow template
  - 10 documenti di esempio in varie cartelle
  
  Uso: `python manage.py setup_demo_data`
```

---

## TEST FINALE COMPLETO

### Prompt per Cursor:

```
Esegui la suite completa di test per verificare che tutto il sistema funzioni.

FASE 1: Backend Unit Tests
```bash
docker-compose exec backend pytest --cov=apps --cov-report=term-missing -v
```
→ Atteso: 0 failures, coverage > 80%

FASE 2: Frontend Unit Tests
```bash
docker-compose exec frontend npm run test -- --run --reporter=verbose
```
→ Atteso: 0 failures

FASE 3: Test E2E
```bash
# Avvia docker-compose e carica fixture
docker-compose exec backend python manage.py setup_demo_data
npm run test:e2e
```
→ Atteso: 0 failures su tutti gli spec

FASE 4: Test di Regressione Manuale
Esegui questo scenario completo nel browser:

Accesso (Fase 1):
□ Login admin@axdoc.local / Admin123!
□ Dashboard si apre con statistiche

Gestione Utenti (Fase 2):
□ Crea nuova UO "Finance" con codice "FIN"
□ Invita utente finance@test.com come OPERATOR in UO Finance
□ Accetta invito, completa registrazione, effettua login

Documenti (Fase 3):
□ Crea cartella "Bilanci" / sottocartella "2024"
□ Carica PDF in "Bilanci/2024"
□ Carica seconda versione → versione 1 ancora scaricabile
□ Verifica lock/unlock

Metadati (Fase 4):
□ Crea struttura "Bilancio" con campo "anno" (number) e "tipo" (select)
□ Carica documento con struttura "Bilancio", compila metadati
□ Modifica metadati dal panel

Workflow (Fase 5):
□ Avvia workflow "Approvazione Standard" sul documento
□ Login come revisore, approva
□ Login come approvatore, approva
□ Documento diventa APPROVED

Protocollazione (Fase 6):
□ Protocolla il documento approvato
□ Verifica che non sia più modificabile
□ Crea fascicolo "Bilanci 2024"
□ Aggiunge documento e protocollo al fascicolo

Ricerca (Fase 7):
□ Cerca "Bilanci" → trova documento
□ Cerca con filtro struttura "Bilancio" → trova
□ Notifiche workflow visibili e cliccabili

Dashboard (Fase 8):
□ Dashboard admin mostra statistiche corrette
□ Step pendenti nel widget task

Se tutti i test passano: il sistema è pronto per il deploy.

Crea `FASE_08_FINAL_TEST_REPORT.md` con:
- Risultati test automatici (copia output)
- Checklist manuale con esiti
- Eventuali issue aperte
- Note per il deploy
```
