# AXDOC — FASE 03
# MFA, SSO e Integrazione LDAP/Active Directory

## Fonte nei documenti di analisi
requisiti_documentale_estesi.docx:
> RF-002: Autenticazione multi-fattore (MFA)
> RF-008: Autenticazione tramite provider esterni (SSO)
> RF-009: Integrazione LDAP/Active Directory
> RNF-008: MFA

Documento Tecnico vDocs:
> "Autenticazione e autorizzazione rigorose per garantire che solo gli 
> utenti autorizzati possano accedere alle risorse appropriate."

**MFA e SSO sono stati citati come requisiti in Fase 1 ma non implementati 
(solo placeholder). LDAP non è mai stato trattato. Questa fase li completa.**

**Prerequisito: FASE 01 completata. Può essere sviluppata in parallelo con le altre fasi avanzate.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] MFA via TOTP (Google Authenticator / Authy) (RF-002, RNF-008)
- [ ] MFA via Email OTP come fallback
- [ ] Abilitazione/disabilitazione MFA dal profilo utente
- [ ] Codici di recupero MFA
- [ ] Flusso login con MFA: login → verifica TOTP → accesso
- [ ] SSO tramite OAuth2/OIDC (Google, Microsoft Azure AD) (RF-008)
- [ ] Integrazione LDAP/Active Directory (RF-009)
- [ ] Sincronizzazione utenti da LDAP
- [ ] Mapping ruoli LDAP → ruoli AXDOC
- [ ] Frontend: setup MFA (QR code, verifica, codici recupero)
- [ ] Frontend: bottone "Accedi con Google/Microsoft"
- [ ] Tutti i test passano

---

## STEP 9B.1 — MFA via TOTP

### Prompt per Cursor:

```
Implementa l'autenticazione a due fattori TOTP in `backend/apps/authentication/`.

Requisiti: RF-002, RNF-008

Installa dipendenze in requirements.txt:
  - pyotp==2.9.*          # TOTP generation and verification
  - qrcode[pil]==7.4.*    # QR code generation per setup TOTP
  - Pillow (già presente)

Modifica `backend/apps/users/models.py` — aggiungi a User:
  - mfa_enabled: bool default False
  - mfa_secret: CharField max 64 blank=True (chiave TOTP, cifrata a riposo)
  - mfa_backup_codes: JSONField default=list 
    (lista di 8 codici monouso hashati, per recupero account)
  - mfa_setup_at: DateTimeField null=True

Crea `backend/apps/authentication/mfa.py`:
  - generate_totp_secret() → str: genera secret base32 casuale
  - get_totp_uri(secret, email, issuer='ITDocs') → str: URI per QR code
  - generate_qr_code_base64(totp_uri) → str: immagine QR come base64 PNG
  - verify_totp(secret, code, window=1) → bool: verifica codice TOTP
    (window=1 accetta ±30 secondi di deriva clock)
  - generate_backup_codes() → tuple[list[str], list[str]]:
    ritorna (codici_plain, codici_hashed) — 8 codici UUID troncati a 8 char
  - verify_backup_code(stored_hashed_codes, provided_code) → tuple[bool, list]:
    verifica e rimuove il codice usato dalla lista

Aggiungi views in `backend/apps/authentication/views.py`:

MFASetupInitView (GET /api/auth/mfa/setup/):
  - Solo utenti autenticati con mfa_enabled=False
  - Genera nuovo totp_secret (NON salvato ancora)
  - Salva secret temporaneo in cache (key: f"mfa_setup_{user.id}", TTL 10min)
  - Risponde: { "secret": "...", "qr_code_base64": "...", "otpauth_uri": "..." }

MFASetupConfirmView (POST /api/auth/mfa/setup/confirm/):
  - Corpo: { "code": "123456" }
  - Recupera secret dalla cache
  - Verifica codice TOTP con il secret
  - Se valido:
    * Salva secret cifrato su user.mfa_secret (cifra con DJANGO SECRET_KEY)
    * Genera backup codes → salva hash su user.mfa_backup_codes
    * Imposta user.mfa_enabled = True, mfa_setup_at = now()
    * Invalida cache
  - Risponde: { "success": true, "backup_codes": ["ABCD1234", ...] }
    (backup codes mostrati UNA SOLA VOLTA in chiaro)

MFADisableView (POST /api/auth/mfa/disable/):
  - Corpo: { "code": "123456" } O { "backup_code": "ABCD1234" }
  - Verifica identità tramite TOTP O backup code
  - Azzera: mfa_secret, mfa_backup_codes, mfa_enabled=False
  - Risponde 200

MFAVerifyView (POST /api/auth/mfa/verify/):
  - Usato nel flusso di login quando mfa_enabled=True
  - Richiede token MFA temporaneo (non JWT completo, solo accesso a questo endpoint)
  - Corpo: { "code": "123456" } O { "backup_code": "ABCD1234" }
  - Se valido: risponde con JWT access + refresh completi
  - Se backup_code: rimuove il codice usato dalla lista

Modifica LoginView:
  - Dopo autenticazione credenziali corrette:
    * Se user.mfa_enabled=False: risponde normalmente con JWT
    * Se user.mfa_enabled=True:
      → NON risponde con JWT completo
      → Genera MFA_PENDING_TOKEN (JWT con scope='mfa_pending', TTL=5min)
      → Risponde: { "mfa_required": true, "mfa_pending_token": "..." }
  
  MFA_PENDING_TOKEN:
    - JWT custom con payload: { "user_id": "...", "scope": "mfa_pending" }
    - Firmato con SECRET_KEY, scade 5 minuti
    - Usato SOLO per accedere a MFAVerifyView

Crea `backend/apps/authentication/encryption.py`:
  - encrypt_secret(plaintext) → str: cifra con Fernet (usa SECRET_KEY come base)
  - decrypt_secret(ciphertext) → str: decifra
  Installa: `cryptography` in requirements.txt

TEST `backend/apps/authentication/tests/test_mfa.py`:
  - Setup MFA: QR code generato, secret in cache
  - Confirm con codice TOTP valido → mfa_enabled=True, backup codes restituiti
  - Confirm con codice errato → 400
  - Login con MFA abilitato → mfa_required=True, mfa_pending_token
  - Verifica TOTP su MFAVerifyView → JWT completo
  - Verifica backup code → JWT completo, codice rimosso dalla lista
  - 8 backup codes → usa tutti → il 9° fallisce
  - Disabilita MFA con codice corretto → mfa_enabled=False

Esegui: `pytest backend/apps/authentication/tests/test_mfa.py -v --tb=short`
```

---

## STEP 9B.2 — SSO OAuth2/OIDC

### Prompt per Cursor:

```
Implementa SSO con OAuth2/OIDC per Google e Microsoft Azure AD (RF-008).

Installa in requirements.txt:
  - social-auth-app-django==5.4.*
  - social-auth-core==4.5.*

Configura in `backend/config/settings/base.py`:

INSTALLED_APPS += ['social_django']

AUTHENTICATION_BACKENDS = [
  'social_core.backends.google.GoogleOAuth2',
  'social_core.backends.microsoft.MicrosoftOAuth2',
  'django.contrib.auth.backends.ModelBackend',
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env('GOOGLE_OAUTH2_CLIENT_ID', default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env('GOOGLE_OAUTH2_CLIENT_SECRET', default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']

SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = env('MICROSOFT_OAUTH2_CLIENT_ID', default='')
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = env('MICROSOFT_OAUTH2_CLIENT_SECRET', default='')
SOCIAL_AUTH_MICROSOFT_GRAPH_TENANT_ID = env('MICROSOFT_TENANT_ID', default='common')

SOCIAL_AUTH_PIPELINE = [
  'social_core.pipeline.social_auth.social_details',
  'social_core.pipeline.social_auth.social_uid',
  'social_core.pipeline.social_auth.auth_allowed',
  'social_core.pipeline.social_auth.social_user',
  'social_core.pipeline.user.get_username',
  'apps.authentication.pipeline.create_or_update_user',  # custom
  'social_core.pipeline.social_auth.associate_user',
  'social_core.pipeline.social_auth.load_extra_data',
]

Aggiungi a `.env.example`:
  GOOGLE_OAUTH2_CLIENT_ID=
  GOOGLE_OAUTH2_CLIENT_SECRET=
  MICROSOFT_OAUTH2_CLIENT_ID=
  MICROSOFT_TENANT_ID=common
  MICROSOFT_OAUTH2_CLIENT_SECRET=

Crea `backend/apps/authentication/pipeline.py`:

def create_or_update_user(strategy, details, backend, user=None, *args, **kwargs):
  """
  Pipeline step custom per SSO.
  - Se utente esistente con stessa email: collega account SSO
  - Se utente nuovo: crea con ruolo OPERATOR di default
  - Genera JWT e li mette nella sessione per il redirect finale
  """
  if user:
    # Aggiorna nome/avatar se cambiato
    user.first_name = details.get('first_name', user.first_name)
    user.last_name = details.get('last_name', user.last_name)
    user.save(update_fields=['first_name', 'last_name'])
    return {'user': user}
  
  email = details.get('email')
  if not email:
    raise Exception("Email non disponibile dal provider SSO")
  
  # Cerca utente esistente per email
  try:
    existing_user = User.objects.get(email=email, is_deleted=False)
    return {'user': existing_user}
  except User.DoesNotExist:
    pass
  
  # Crea nuovo utente SSO
  new_user = User.objects.create_user(
    email=email,
    first_name=details.get('first_name', ''),
    last_name=details.get('last_name', ''),
    role='OPERATOR',
    must_change_password=False,  # SSO, nessuna password locale
  )
  return {'user': new_user}

Aggiungi views SSO in `backend/apps/authentication/views.py`:

SSOInitView (GET /api/auth/sso/{provider}/):
  - provider: 'google' O 'microsoft'
  - Genera URL di redirect OAuth2 verso il provider
  - Risponde: { "auth_url": "https://accounts.google.com/o/oauth2/..." }

SSOCallbackView (GET /api/auth/sso/{provider}/callback/):
  - Riceve il callback OAuth2 dal provider
  - Completa il flusso social-auth-django
  - Genera JWT per l'utente autenticato
  - Redirect a: {FRONTEND_URL}/sso-callback?access={token}&refresh={token}
    oppure {FRONTEND_URL}/sso-callback?error={message}

Aggiorna `config/urls.py`:
  - path('api/auth/sso/', include('social_django.urls', namespace='social'))
  - path('api/auth/sso/<str:provider>/', SSOInitView.as_view())

TEST `backend/apps/authentication/tests/test_sso.py`:
  - Con GOOGLE_OAUTH2_CLIENT_ID vuoto: SSO disabilitato → endpoint ritorna 503
  - Mock del callback OAuth2: utente creato con dati provider
  - Secondo login stesso utente: aggiorna dati, non crea duplicato
  - Email già registrata: collega account SSO senza creare nuovo utente

Esegui: `pytest backend/apps/authentication/tests/test_sso.py -v --tb=short`
```

---

## STEP 9B.3 — Integrazione LDAP/Active Directory

### Prompt per Cursor:

```
Implementa l'integrazione LDAP/Active Directory (RF-009).

Installa in requirements.txt:
  - django-auth-ldap==4.6.*
  - python-ldap==3.4.*

Aggiungi in `backend/config/settings/base.py`:

import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType, ActiveDirectoryGroupType

# LDAP — tutti i valori da env, vuoti di default (LDAP disabilitato se vuoto)
LDAP_ENABLED = env.bool('LDAP_ENABLED', default=False)

if LDAP_ENABLED:
  AUTH_LDAP_SERVER_URI = env('LDAP_SERVER_URI')  # es: ldap://dc.company.com
  AUTH_LDAP_BIND_DN = env('LDAP_BIND_DN')        # es: cn=svc_axdoc,ou=services,dc=company,dc=com
  AUTH_LDAP_BIND_PASSWORD = env('LDAP_BIND_PASSWORD')
  AUTH_LDAP_USER_SEARCH = LDAPSearch(
    env('LDAP_USER_BASE_DN'),     # es: ou=users,dc=company,dc=com
    ldap.SCOPE_SUBTREE,
    env('LDAP_USER_FILTER', default='(sAMAccountName=%(user)s)'),
  )
  AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': env('LDAP_ATTR_FIRSTNAME', default='givenName'),
    'last_name': env('LDAP_ATTR_LASTNAME', default='sn'),
    'email': env('LDAP_ATTR_EMAIL', default='mail'),
  }
  AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    env('LDAP_GROUP_BASE_DN', default=''),
    ldap.SCOPE_SUBTREE,
    '(objectClass=group)',
  )
  AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType()
  
  # Mapping gruppi AD → ruoli AXDOC
  AUTH_LDAP_USER_FLAGS_BY_GROUP = {}
  LDAP_ROLE_MAPPING = {
    env('LDAP_GROUP_ADMIN', default='cn=axdoc-admin,ou=groups,dc=company,dc=com'): 'ADMIN',
    env('LDAP_GROUP_APPROVER', default='cn=axdoc-approver,ou=groups,dc=company,dc=com'): 'APPROVER',
    env('LDAP_GROUP_REVIEWER', default='cn=axdoc-reviewer,ou=groups,dc=company,dc=com'): 'REVIEWER',
    env('LDAP_GROUP_OPERATOR', default='cn=axdoc-operator,ou=groups,dc=company,dc=com'): 'OPERATOR',
  }
  
  AUTH_LDAP_ALWAYS_UPDATE_USER = True  # aggiorna dati ad ogni login
  AUTH_LDAP_FIND_GROUP_PERMS = True
  AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_NEVER,  # per ambienti interni
    ldap.OPT_REFERRALS: 0,
  }
  
  AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
  ] + AUTHENTICATION_BACKENDS

Aggiungi a `.env.example`:
  LDAP_ENABLED=false
  LDAP_SERVER_URI=ldap://dc.azienda.com
  LDAP_BIND_DN=cn=svc_axdoc,ou=services,dc=azienda,dc=com
  LDAP_BIND_PASSWORD=
  LDAP_USER_BASE_DN=ou=users,dc=azienda,dc=com
  LDAP_USER_FILTER=(sAMAccountName=%(user)s)
  LDAP_GROUP_BASE_DN=ou=groups,dc=azienda,dc=com
  LDAP_GROUP_ADMIN=cn=axdoc-admin,ou=groups,dc=azienda,dc=com
  LDAP_GROUP_APPROVER=cn=axdoc-approver,ou=groups,dc=azienda,dc=com
  LDAP_GROUP_REVIEWER=cn=axdoc-reviewer,ou=groups,dc=azienda,dc=com
  LDAP_GROUP_OPERATOR=cn=axdoc-operator,ou=groups,dc=azienda,dc=com

Crea `backend/apps/authentication/ldap_signals.py`:
  Aggancia il segnale populate_user di django-auth-ldap per:
  - Mappare il gruppo AD al ruolo AXDOC (user.role)
  - Creare/aggiornare OrganizationalUnit dal gruppo AD se configurato
  - Aggiornare user.must_change_password = False (LDAP gestisce la password)

Crea management command `backend/apps/authentication/management/commands/sync_ldap_users.py`:
  - Connette a LDAP e sincronizza tutti gli utenti nel base DN
  - Crea utenti mancanti, aggiorna esistenti, disabilita utenti rimossi da LDAP
  - Applica mapping ruoli
  - Risponde con report: { "created": N, "updated": N, "disabled": N, "errors": [...] }
  - Uso: `python manage.py sync_ldap_users [--dry-run]`

Aggiungi API admin:

GET /api/admin/ldap/status/:
  - Solo ADMIN
  - Testa connessione LDAP: risponde con { "connected": bool, "server": "...", "error": str|null }

POST /api/admin/ldap/sync/:
  - Solo ADMIN
  - Avvia sync LDAP manuale (chiama sync_ldap_users in background o sincrono)
  - Risponde con report della sincronizzazione

TEST `backend/apps/authentication/tests/test_ldap.py`:
  - Con LDAP_ENABLED=False: login normale funziona, endpoint LDAP disabilitati
  - Mock LDAP: login con credenziali LDAP → utente creato con ruolo mappato
  - Mock LDAP: secondo login → utente aggiornato, non duplicato
  - sync_ldap_users: crea utenti mancanti, disabilita rimossi

Esegui: `pytest backend/apps/authentication/tests/test_ldap.py -v --tb=short`
(I test LDAP usano mock, non richiedono server AD reale)
```

---

## STEP 9B.4 — Frontend: MFA e SSO

### Prompt per Cursor:

```
Crea i componenti frontend per MFA e SSO.

Aggiungi `frontend/src/services/authService.ts` (aggiorna esistente):
  - initMFASetup(): GET /api/auth/mfa/setup/
  - confirmMFASetup(code): POST /api/auth/mfa/setup/confirm/
  - disableMFA(code): POST /api/auth/mfa/disable/
  - verifyMFA(mfaPendingToken, code): POST /api/auth/mfa/verify/
  - getSSOAuthUrl(provider): GET /api/auth/sso/{provider}/

Crea `frontend/src/components/auth/`:

MFASetupWizard.tsx:
  Wizard a 3 step per configurare MFA nel profilo utente:
  
  Step 1 — Istruzioni:
    - "Scarica Google Authenticator o Authy"
    - Link a App Store / Google Play
    - Bottone "Continua"
  
  Step 2 — Scansiona QR Code:
    - QR Code come immagine (base64 da API)
    - Alternatively: mostra secret come testo per inserimento manuale
    - "Scansiona questo QR code con la tua app authenticator"
    - Bottone "Continua"
  
  Step 3 — Verifica:
    - Input 6 cifre per TOTP
    - Bottone "Attiva MFA"
    - Se successo: mostra backup codes (lista di 8 codici)
      con bottone "Scarica codici" (download .txt) e "Ho salvato i codici"
    - Warning: "Salva questi codici in un posto sicuro. 
      Non potranno essere visualizzati di nuovo."

MFAVerifyModal.tsx:
  Modal mostrato durante il login quando mfa_required=true:
  - Input 6 cifre TOTP (auto-focus, auto-submit a 6 cifre)
  - Link "Usa codice di recupero" → switch a input testo libero
  - Timer "Il codice cambia ogni 30 secondi" con countdown visivo
  - Messaggio errore se codice sbagliato

SSOButtons.tsx:
  Componente con bottoni SSO:
  - Bottone "Accedi con Google" (icona Google + testo)
  - Bottone "Accedi con Microsoft" (icona Microsoft + testo)
  - Mostrati solo se le credenziali SSO sono configurate (check API)
  - Click → redirect a SSOInitView → provider → callback

Aggiorna `frontend/src/pages/LoginPage.tsx`:
  - Aggiungi SSOButtons sotto il form login con separatore "oppure"
  - Dopo login, se risposta ha mfa_required=True:
    → Salva mfa_pending_token in state temporaneo
    → Apri MFAVerifyModal

Crea `frontend/src/pages/SSOCallbackPage.tsx` (route: /sso-callback):
  - Legge access e refresh token dai query params
  - Salva in localStorage, aggiorna authStore
  - Redirect a /dashboard
  - Se c'è errore nei query params: mostra messaggio e link a /login

Aggiorna `frontend/src/pages/ProfilePage.tsx` (Fase 8):
  Aggiungi sezione "Sicurezza":
  - Se MFA disabilitato: card "Autenticazione a due fattori" 
    con descrizione e bottone "Abilita MFA" → apre MFASetupWizard
  - Se MFA abilitato: badge "MFA Attivo ✓" + bottone "Disabilita" 
    → modal conferma con input TOTP

LDAPStatusCard.tsx (solo ADMIN, in impostazioni sistema):
  - Stato connessione LDAP (verde/rosso)
  - Bottone "Testa connessione"
  - Bottone "Sincronizza utenti" con ultimo sync timestamp
  - Risultati ultimo sync: N creati, N aggiornati, N disabilitati

TEST Vitest:
  - MFASetupWizard: 3 step, bottone continua, verifica TOTP, backup codes
  - MFAVerifyModal: input auto-submit, switch backup code
  - SSOButtons: render condizionale in base a config
  - SSOCallbackPage: salva token, redirect dashboard
  - LoginPage: apre MFAVerifyModal se mfa_required

Esegui: `npm run test -- --run`
Esegui: `npm run build`
```

---

## TEST INTEGRAZIONE FASE 9B

### Prompt per Cursor:

```
Test di integrazione Fase 9B.

1. `pytest backend/apps/authentication/ -v --cov=apps/authentication`

2. `npm run test -- --run`

3. Test manuale MFA:
   a) Login come admin → profilo → sezione Sicurezza → "Abilita MFA"
   b) Segui wizard: QR code mostrato
   c) Scansiona con Google Authenticator (O usa script Python per generare il codice):
      python3 -c "import pyotp; print(pyotp.TOTP('SECRET_DA_QR').now())"
   d) Inserisci codice → MFA attivo
   e) Logout → login → inserisci email/password → MFAVerifyModal appare
   f) Inserisci codice TOTP → accesso
   g) Inserisci codice sbagliato → errore
   h) Usa backup code → accesso, codice rimosso dalla lista
   i) Disabilita MFA dal profilo → verifica TOTP → MFA disabilitato
   
4. Test SSO (se configurato):
   - Con GOOGLE_OAUTH2_CLIENT_ID configurato:
     → Bottone Google appare nel login
     → Click → redirect a Google
     → Dopo autenticazione: redirect a /sso-callback?access=...
     → Dashboard aperta con utente autenticato
   - Senza configurazione: bottoni non appaiono

5. Test LDAP (se disponibile server test):
   `docker-compose exec backend python manage.py sync_ldap_users --dry-run`
   → Output: report senza modifiche effettive
   
   GET /api/admin/ldap/status/ → { "connected": false } (senza server)

Crea `FASE_09B_TEST_REPORT.md`.
```
