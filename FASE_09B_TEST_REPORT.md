# FASE 09B (FASE 03) — Report test integrazione MFA, SSO, LDAP

## Implementazione completata

### Backend
- **MFA TOTP (STEP 9B.1)**
  - Modello `User`: campi `mfa_enabled`, `mfa_secret`, `mfa_backup_codes`, `mfa_setup_at`
  - `apps/authentication/mfa.py`: `generate_totp_secret`, `get_totp_uri`, `generate_qr_code_base64`, `verify_totp`, `generate_backup_codes`, `verify_backup_code`
  - `apps/authentication/encryption.py`: cifratura Fernet per il secret
  - Endpoint: `GET /api/auth/mfa/setup/`, `POST /api/auth/mfa/setup/confirm/`, `POST /api/auth/mfa/disable/`, `POST /api/auth/mfa/verify/`
  - Login: se `mfa_enabled` → risposta `mfa_required` + `mfa_pending_token` (JWT 5 min)
- **SSO OAuth2 (STEP 9B.2)**
  - `social_django` in `INSTALLED_APPS`, pipeline custom `create_or_update_user`
  - `GET /api/auth/sso/<provider>/` (google | microsoft) → `auth_url`
  - Callback → redirect a `/api/auth/sso/jwt-redirect/` → JWT e redirect a frontend `/sso-callback?access=...&refresh=...`
- **LDAP (STEP 9B.3)**
  - Settings condizionali con `LDAP_ENABLED` (try/except su `django-auth-ldap`)
  - `GET /api/admin/ldap/status/`, `POST /api/admin/ldap/sync/` (solo ADMIN)
  - Management command: `python manage.py sync_ldap_users [--dry-run]`

### Frontend
- **authService**: `initMFASetup`, `confirmMFASetup`, `disableMFA`, `verifyMFA`, `getSSOAuthUrl`
- **MFASetupWizard**: 3 step (istruzioni → QR → verifica → backup codes)
- **MFAVerifyModal**: input 6 cifre, auto-submit, switch a codice di recupero
- **SSOButtons**: bottoni Google/Microsoft (solo se configurati)
- **SSOCallbackPage**: legge `access` e `refresh` da query, salva token, redirect a dashboard
- **ProfilePage**: sezione Sicurezza (Abilita/Disabilita MFA), LDAPStatusCard per ADMIN
- **LoginPage**: gestione `mfa_required` + modal verifica, SSOButtons sotto il form

## Come eseguire i test

### Backend (in Docker)
```bash
docker-compose up -d
docker-compose exec backend pip install pyotp qrcode cryptography PyJWT social-auth-app-django social-auth-core  # se non in requirements
docker-compose exec backend python manage.py migrate
docker-compose exec backend pytest apps/authentication/tests/test_mfa.py apps/authentication/tests/test_sso.py -v --tb=short
```

### Frontend
```bash
cd frontend && npm run test -- --run
npm run build
```

### Test manuale MFA
1. Login come admin → Profilo → Sicurezza → Abilita MFA
2. Wizard: continua → scansiona QR (o inserisci secret) → inserisci codice TOTP → salva backup codes
3. Logout → login → inserisci email/password → si apre MFAVerifyModal → inserisci codice TOTP (o backup)
4. Profilo → Disabilita MFA (con codice TOTP)

### Test manuale SSO
- Con `GOOGLE_OAUTH2_CLIENT_ID` e secret configurati in `.env`: bottone “Accedi con Google” visibile → redirect a Google → dopo auth redirect a `/sso-callback` → dashboard
- Senza configurazione: bottoni SSO non appaiono (API 503)

### Test LDAP
- `LDAP_ENABLED=false`: `GET /api/admin/ldap/status/` → `{ "connected": false, "error": "LDAP disabilitato" }`
- Con server LDAP: configurare variabili in `.env` e installare `django-auth-ldap` + `python-ldap`

## Note
- **django-auth-ldap** e **python-ldap** non sono in `requirements.txt` di default (dipendenze di sistema). Aggiungerli se si usa LDAP.
- Il flusso SSO richiede sessioni Django per il redirect post-OAuth; verificare che `SessionMiddleware` e cookie siano corretti in produzione.
