# AXDOC — FASE 02
# Gestione Utenti Avanzata e Unità Organizzative

**Prerequisito: FASE 01 completata e tutti i test passanti.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] API `/api/organizations/` CRUD completo
- [ ] Gerarchia UO (parent/children) funzionante
- [ ] Univocità codice UO (RF-027)
- [ ] Assegnazione utenti a UO con ruoli (RF-025)
- [ ] Invito utente via email con link di accettazione (RF-018)
- [ ] Utente invitato imposta password al primo accesso
- [ ] Export lista utenti UO in CSV (RF-026 collaudo)
- [ ] Filtro UO "Le mie" / "Tutte" funzionante
- [ ] Frontend: pagina Gestione Utenti (solo ADMIN)
- [ ] Frontend: pagina Unità Organizzative con albero gerarchico
- [ ] Frontend: form invito utente
- [ ] Tutti i test pytest passano
- [ ] Tutti i test React passano

---

## STEP 2.1 — App Organizations: Modello e API

### Prompt per Cursor:

```
Crea `backend/apps/organizations/` per la gestione delle Unità Organizzative.

Requisiti: RF-021..RF-027

Crea `backend/apps/organizations/models.py`:

class OrganizationalUnit(models.Model):
  - id: UUID primary key
  - name: CharField max 200
  - code: CharField max 50, UNIQUE (RF-027)
  - description: TextField blank=True
  - parent: FK a self null=True (gerarchia RF-024) related_name='children'
  - is_active: bool default True
  - created_at, updated_at: auto timestamps
  - created_by: FK User null=True
  
  Metodo: get_ancestors() → lista UO parent fino alla radice
  Metodo: get_descendants() → lista UO figlie ricorsiva
  Metodo: get_all_members() → tutti gli utenti incluse UO figlie

class OrganizationalUnitMembership(models.Model):
  - id: UUID primary key
  - user: FK User
  - organizational_unit: FK OrganizationalUnit
  - role: CharField choices [OPERATOR, REVIEWER, APPROVER] (ruolo nella UO)
  - joined_at: auto_now_add
  - is_active: bool default True
  
  Meta: unique_together = ['user', 'organizational_unit']

Crea `backend/apps/organizations/serializers.py`:
  - OrganizationalUnitSerializer (con nested children solo al primo livello)
  - OrganizationalUnitDetailSerializer (con members)
  - OrganizationalUnitMembershipSerializer
  - OrganizationalUnitCreateSerializer

Crea `backend/apps/organizations/views.py`:

OrganizationalUnitViewSet:
  - list: filtrabile per is_active, parent (null=root), codice, nome
    Query param `mine=true` → solo UO in cui l'utente è membro (RF-024 filtro collaudo)
  - retrieve: dettaglio con figli e membri
  - create: solo ADMIN
  - update/partial_update: solo ADMIN
  - destroy: soft delete (is_active=False), solo ADMIN, solo se senza documenti
  
  Extra endpoints:
  - POST /organizations/{id}/add_member/ → aggiunge utente con ruolo
  - DELETE /organizations/{id}/remove_member/{user_id}/ → rimuove utente
  - GET /organizations/{id}/members/ → lista membri con ruolo
  - GET /organizations/{id}/export/ → CSV dei membri (RF-026 collaudo)
  - GET /organizations/tree/ → struttura ad albero completa

Crea `backend/apps/organizations/utils.py`:
  - export_members_csv(ou_id) → StringIO con CSV

Crea migration e urls.py, aggiungi a config/urls.py

TEST: `backend/apps/organizations/tests/`:
  - CRUD UO solo ADMIN
  - Unicità codice UO → 400 se duplicato
  - Gerarchia: parent → children correttamente
  - get_descendants() include tutti i livelli
  - Assegnazione membro → appare in get_all_members() anche dalla UO parent
  - Export CSV ha headers e dati corretti
  - Filtro mine=true → solo UO dell'utente loggato

Esegui: `pytest backend/apps/organizations/ -v --tb=short`
```

---

## STEP 2.2 — Invito Utenti e Onboarding

### Prompt per Cursor:

```
Implementa il sistema di invito utenti (RF-018) nell'app authentication e users.

Modifica `backend/apps/authentication/models.py`:
  Aggiungi UserInvitation:
  - id: UUID primary key
  - email: EmailField
  - invited_by: FK User
  - token: UUID unique
  - organizational_unit: FK OrganizationalUnit null=True
  - role: CharField (ruolo da assegnare)
  - ou_role: CharField (ruolo nell'UO)
  - created_at: auto_now_add
  - expires_at: default = created_at + 7 giorni
  - accepted_at: DateTimeField null=True
  - is_used: bool default False

Aggiungi in `backend/apps/authentication/views.py`:

InviteUserView (POST /api/auth/invite/):
  - Solo ADMIN
  - Accetta: email, role, organizational_unit_id (opz.), ou_role (opz.)
  - Verifica che email non sia già registrata
  - Crea UserInvitation con token UUID
  - Invia email con link: /accept-invitation/{token}
  - Link valido 7 giorni
  - Risponde 201 con invitation id

AcceptInvitationView (POST /api/auth/accept-invitation/{token}/):
  - Pubblica (no auth richiesta)
  - Verifica token valido e non scaduto e non usato
  - GET: ritorna email dell'invito (per mostrare nel form)
  - POST: accetta first_name, last_name, password, password_confirm
  - Crea User con dati forniti e ruolo dall'invito
  - Se organizational_unit presente: crea OrganizationalUnitMembership
  - Marca invito come usato
  - Invia email di benvenuto
  - Risponde con JWT tokens (auto-login)

Modifica LoginView:
  - Se user.must_change_password=True dopo login: risponde con flag 
    force_password_change=True e token temporaneo
  - Il frontend deve reindirizzare a pagina cambio password

ChangePasswordView (POST /api/auth/change-password/):
  - Richiede auth
  - Accetta old_password, new_password, confirm_password
  - Valida old_password, aggiorna password
  - Imposta must_change_password=False
  - Invalida tutti i refresh token precedenti

TEST:
  - Invio invito: email inviata, invitation creata nel DB
  - Token scaduto → 400
  - Token usato → 400
  - Accettazione invito: utente creato, membership creata, auto-login
  - Invito doppio stesso email → 400

Esegui: `pytest backend/apps/authentication/ -v --tb=short`
```

---

## STEP 2.3 — Frontend: Pagine Utenti e UO

### Prompt per Cursor:

```
Crea le pagine di gestione Utenti e Unità Organizzative nel frontend.

Aggiungi a `frontend/src/services/`:

userService.ts:
  - getUsers(params): GET /api/users/ con filtri
  - getUser(id): GET /api/users/{id}/
  - createUser(data): POST /api/users/
  - updateUser(id, data): PUT/PATCH /api/users/{id}/
  - deleteUser(id): DELETE /api/users/{id}/
  - inviteUser(data): POST /api/auth/invite/

organizationService.ts:
  - getOrganizationalUnits(params): GET /api/organizations/
  - getOrganizationalUnitTree(): GET /api/organizations/tree/
  - getOrganizationalUnit(id): GET /api/organizations/{id}/
  - createOrganizationalUnit(data): POST /api/organizations/
  - updateOrganizationalUnit(id, data): PATCH /api/organizations/{id}/
  - addMember(ouId, userId, role): POST /api/organizations/{id}/add_member/
  - removeMember(ouId, userId): DELETE /api/organizations/{id}/remove_member/{uid}/
  - exportMembers(ouId): GET /api/organizations/{id}/export/ (download CSV)

Crea componenti in `frontend/src/components/users/`:

UserTable.tsx:
  - Tabella con colonne: nome, email, ruolo, stato, data creazione, azioni
  - Paginazione
  - Filtri: ruolo, stato (attivo/disabilitato)
  - Ricerca per nome/email
  - Azioni per riga: modifica, disabilita, elimina (solo ADMIN)

UserFormModal.tsx:
  - Modal con form: first_name, last_name, email, role
  - Validazione zod
  - Per creazione: opzione "Invia invito" invece di creare direttamente

InviteUserModal.tsx:
  - Form: email, role, unità organizzativa (select), ruolo nella UO
  - Submit → chiama inviteUser
  - Feedback successo/errore

Crea componenti in `frontend/src/components/organizations/`:

OUTree.tsx:
  - Visualizzazione ad albero delle UO (ricorsivo)
  - Click per espandere/collassare
  - Badge con numero membri
  - Azioni: modifica, aggiungi utente, esporta

OUFormModal.tsx:
  - Form: name, code, description, parent (select delle UO esistenti)
  - Validazione: code univoco (feedback real-time)

OUMembersPanel.tsx:
  - Lista membri con ruolo
  - Bottone "Aggiungi utente" → select utente + ruolo
  - Bottone rimozione per ogni membro
  - Esporta CSV

Crea pagine in `frontend/src/pages/`:

UsersPage.tsx (route: /users, solo ADMIN):
  - Header con "Gestione Utenti" + bottone "Invita Utente"
  - UserTable con tutti gli utenti
  - Gestione stati loading/error

OrganizationsPage.tsx (route: /organizations, solo ADMIN):
  - Tabs: "Le mie UO" / "Tutte le UO"
  - OUTree
  - Panel laterale con dettaglio UO selezionata + OUMembersPanel

AcceptInvitationPage.tsx (route: /accept-invitation/:token, pubblica):
  - Carica dati invito tramite token
  - Form: nome, cognome, password, conferma password
  - Submit → accetta invito, auto-login, redirect a /dashboard

Aggiorna `App.tsx` con le nuove route e ProtectedRoute con check ruolo ADMIN.

Aggiorna il menu di navigazione con link a Utenti e Organizzazioni.

TEST con Vitest:
  - UserTable: render, paginazione, filtri
  - InviteUserModal: submit con dati validi
  - OUTree: render struttura gerarchica
  - AcceptInvitationPage: form submit, error handling

Esegui: `npm run test -- --run` → tutti passano
Esegui: `npm run build` → nessun errore TypeScript
```

---

## TEST INTEGRAZIONE FASE 2

### Prompt per Cursor:

```
Esegui i test di integrazione per la Fase 2.

1. `docker-compose exec backend pytest --cov=apps --cov-report=term-missing`
   → Coverage > 80%, tutti i test passano

2. `docker-compose exec frontend npm run test -- --run`
   → Tutti i test passano

3. Test manuale end-to-end:

   a) Crea UO "Direzione" (root) come admin
   b) Crea UO "IT" con parent "Direzione"
   c) Verifica albero: GET /api/organizations/tree/ mostra gerarchia
   d) Invita utente operatore@test.com come OPERATOR nell'UO "IT"
   e) Verifica email in console Django (EMAIL_BACKEND=console)
   f) Accetta invito: POST /api/auth/accept-invitation/{token}/ con nome+password
   g) Login con operatore@test.com → successo
   h) Verifica che operatore non veda pagina /users (403)
   i) Verifica che admin veda operatore nella lista UO "IT"
   j) Export CSV dell'UO "IT" → scarica file con header e dati

4. Verifica nel browser:
   - /organizations mostra albero UO
   - Click su UO mostra membri
   - Form invito funziona (email in console Django)
   - /users mostra lista utenti con paginazione

Se ci sono errori, correggili.
Crea `FASE_02_TEST_REPORT.md` con i risultati.
```
