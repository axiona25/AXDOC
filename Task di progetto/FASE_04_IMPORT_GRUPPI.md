# AXDOC — FASE 04
# Importazione Utenti, Gruppi e Gestione Licenza

## Fonte nei documenti di analisi

**Importazione utenti** — requisiti_documentale_estesi.docx:
> RF-016: Gestione gruppi utenti
> RF-017: Importazione utenti (da CSV/Excel)

**Cifratura On-Demand** — Documento Tecnico vDocs:
> "Cifratura dei documenti On Demand proprietaria."

**Gestione Licenze** — Documento Collaudo:
> "Gestione delle licenze, monitoraggio e modifica degli utenti e dei relativi ruoli"

**Gruppi utenti** — requisiti_documentale_estesi.docx:
> RF-016: Gestione gruppi utenti (distinto dai ruoli e dalle UO)

**Nessuna di queste funzionalità è presente nelle fasi precedenti.**

**Prerequisito: FASE 02 completata.**

---

## CHECKLIST DI COMPLETAMENTO

- [ ] Importazione utenti da CSV (RF-017)
- [ ] Importazione utenti da Excel (.xlsx)
- [ ] Template CSV/Excel scaricabile
- [ ] Validazione e report errori import
- [ ] Gruppi utenti (RF-016) distinti da UO e ruoli
- [ ] Cifratura documento On-Demand (AES-256)
- [ ] Decifratura con password
- [ ] Pannello gestione licenza (ADMIN)
- [ ] Monitoraggio: utenti attivi, storage usato, feature abilitate
- [ ] Tutti i test passano

---

## STEP 9D.1 — Importazione Utenti da CSV/Excel

### Prompt per Cursor:

```
Implementa l'importazione massiva di utenti da CSV/Excel (RF-017).

Installa in requirements.txt:
  - openpyxl==3.1.*    # lettura Excel
  - tablib==3.5.*      # parsing CSV/Excel unificato

Crea `backend/apps/users/importers.py`:

IMPORT_COLUMNS = {
  'email': {'required': True, 'type': 'email'},
  'first_name': {'required': True, 'type': 'str', 'max': 150},
  'last_name': {'required': True, 'type': 'str', 'max': 150},
  'role': {'required': True, 'type': 'choice', 
           'choices': ['OPERATOR', 'REVIEWER', 'APPROVER', 'ADMIN']},
  'organizational_unit_code': {'required': False, 'type': 'str'},
  'ou_role': {'required': False, 'type': 'choice',
              'choices': ['OPERATOR', 'REVIEWER', 'APPROVER'], 'default': 'OPERATOR'},
  'phone': {'required': False, 'type': 'str'},
}

class UserImporter:
  
  def parse_file(self, file_obj, file_type: str) -> list[dict]:
    """
    Parsa CSV o Excel. Ritorna lista di dict con le righe.
    file_type: 'csv' | 'xlsx'
    """
  
  def validate_row(self, row: dict, row_number: int) -> list[str]:
    """
    Valida una singola riga. Ritorna lista di errori (vuota se OK).
    Controlli: campi required, formato email, valori choice validi,
    email già esistente nel sistema.
    """
  
  def import_users(self, rows: list[dict], send_invite: bool = True) -> dict:
    """
    Importa utenti validati.
    - Crea User per ogni riga valida
    - Se send_invite=True: invia email invito
    - Se organizational_unit_code: aggiunge a UO
    - Ritorna: {
        "total": N,
        "created": N,
        "skipped": N,  # già esistenti
        "errors": [{"row": N, "email": "...", "errors": [...]}]
      }
    """
  
  @staticmethod
  def get_template_csv() -> str:
    """Ritorna CSV template con header e riga esempio"""
  
  @staticmethod
  def get_template_xlsx() -> bytes:
    """Ritorna Excel template con header, riga esempio e dropdown validazione"""

Aggiungi views in `backend/apps/users/views.py`:

GET /api/users/import/template/?format=csv|xlsx:
  - Solo ADMIN
  - Scarica template CSV o Excel
  - Content-Disposition: attachment

POST /api/users/import/preview/:
  - Solo ADMIN
  - Multipart con file CSV o Excel
  - Valida ogni riga SENZA creare utenti
  - Risponde:
    {
      "total_rows": N,
      "valid_rows": N,
      "invalid_rows": N,
      "preview": [
        {"row": 1, "email": "...", "name": "...", "valid": true, "errors": []},
        {"row": 2, "email": "...", "name": "...", "valid": false, "errors": ["Email non valida"]},
      ]
    }

POST /api/users/import/:
  - Solo ADMIN
  - Multipart con file CSV o Excel + { "send_invite": true }
  - Importa solo le righe valide
  - Risponde con report completo
  - Registra AuditLog: action='users_imported', detail=report

Frontend (da aggiungere in UsersPage.tsx):

ImportUsersModal.tsx:
  - Bottone "Importa utenti" → apre modale
  - Step 1: 
    * Download template CSV / Excel
    * Upload area (drag & drop o click)
  - Step 2 — Preview:
    * Tabella con righe: N° riga, email, nome, ruolo, UO, stato (✓ / ✗ + errori)
    * Riepilogo: N valide, N con errori
    * Toggle "Invia email di invito agli utenti creati"
    * Bottone "Importa N utenti validi"
  - Step 3 — Risultati:
    * "N utenti creati, N saltati (già esistenti), N errori"
    * Lista eventuali righe con errori non risolti

TEST:
  - Template CSV scaricato: ha header corretti
  - Preview CSV valido: N valid_rows corretti
  - Preview con email duplicata: riga marcata invalid
  - Import: utenti creati nel DB, inviti inviati (mock email)
  - Import Excel: funziona come CSV

Esegui: `pytest backend/apps/users/tests/test_import.py -v`
```

---

## STEP 9D.2 — Gruppi Utenti

### Prompt per Cursor:

```
Implementa la gestione gruppi utenti (RF-016), distinta da UO e ruoli.

I Gruppi sono insiemi trasversali di utenti usabili per:
- Assegnare permessi su documenti a un gruppo
- Notifiche di gruppo
- Filtri e reportistica

Crea `backend/apps/users/models.py` — aggiungi:

class UserGroup(models.Model):
  - id: UUID primary key
  - name: CharField max 200 unique
  - description: TextField blank=True
  - members: ManyToMany User through UserGroupMembership
  - created_by: FK User
  - created_at, updated_at: timestamps
  - is_active: bool default True

class UserGroupMembership(models.Model):
  - group: FK UserGroup
  - user: FK User
  - added_by: FK User
  - added_at: auto_now_add
  Meta: unique_together = ['group', 'user']

Aggiungi in `backend/apps/documents/models.py`:
  - allowed_groups: ManyToMany UserGroup through DocumentGroupPermission

class DocumentGroupPermission(models.Model):
  - document: FK Document
  - group: FK UserGroup
  - can_read: bool default True
  - can_write: bool default False

Aggiorna CanAccessDocument permission:
  Aggiungi controllo: utente è membro di un gruppo con permesso sul documento

Aggiungi ViewSet in `backend/apps/users/views.py`:

UserGroupViewSet:
  - list: GET /api/groups/ con ricerca per nome
  - retrieve: con lista membri
  - create: solo ADMIN
  - update: solo ADMIN
  - destroy: soft delete, solo ADMIN
  Extra:
  - POST /api/groups/{id}/add_members/: body: {user_ids: [...]}
  - DELETE /api/groups/{id}/remove_member/{user_id}/
  - GET /api/groups/{id}/members/

Aggiorna frontend (UsersPage o nuova GroupsPage):
  GroupsPage.tsx (route: /groups, solo ADMIN):
  - Tabella gruppi: nome, N membri, data creazione
  - Azioni: modifica, aggiungi membri, elimina
  
  Aggiorna DocumentDetailPanel tab "Permessi":
  - Sezione "Gruppi": aggiunta/rimozione gruppi con permessi

TEST:
  - CRUD gruppo
  - Aggiunta membri: tutti in UserGroupMembership
  - Documento con gruppo: membro del gruppo può leggere, non-membro no
  - Rimozione gruppo da documento: membro perde accesso

Esegui: `pytest backend/apps/users/tests/test_groups.py -v`
```

---

## STEP 9D.3 — Cifratura Documenti On-Demand

### Prompt per Cursor:

```
Implementa la cifratura dei documenti On-Demand (Documento Tecnico vDocs).

"Cifratura dei documenti On Demand proprietaria" — i file vengono cifrati
con AES-256 su richiesta esplicita dell'utente, e decifrati al download
con la password fornita.

Installa in requirements.txt:
  - cryptography (già presente da Fase 9B)

Crea `backend/apps/documents/encryption.py`:

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

class DocumentEncryption:
  
  @staticmethod
  def derive_key(password: str, salt: bytes) -> bytes:
    """Deriva chiave AES-256 da password tramite PBKDF2 (100k iterazioni)"""
    kdf = PBKDF2HMAC(
      algorithm=hashes.SHA256(),
      length=32,  # 256 bit
      salt=salt,
      iterations=100_000,
    )
    return kdf.derive(password.encode())
  
  @staticmethod
  def encrypt_file(file_path: str, password: str) -> tuple[str, str]:
    """
    Cifra un file con AES-256-GCM.
    Ritorna: (encrypted_file_path, salt_b64)
    Il file cifrato ha estensione .enc
    """
    salt = os.urandom(16)
    key = DocumentEncryption.derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    with open(file_path, 'rb') as f:
      plaintext = f.read()
    
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    
    # Formato file: [salt 16B][nonce 12B][ciphertext]
    encrypted_path = file_path + '.enc'
    with open(encrypted_path, 'wb') as f:
      f.write(salt + nonce + ciphertext)
    
    return encrypted_path, base64.b64encode(salt).decode()
  
  @staticmethod
  def decrypt_file(encrypted_path: str, password: str) -> bytes:
    """
    Decifra file .enc. Ritorna i bytes del file originale.
    Solleva InvalidTag se password sbagliata.
    """
    with open(encrypted_path, 'rb') as f:
      data = f.read()
    
    salt = data[:16]
    nonce = data[16:28]
    ciphertext = data[28:]
    
    key = DocumentEncryption.derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

Modifica `backend/apps/documents/models.py`:
  Aggiungi in DocumentVersion:
  - is_encrypted: bool default False
  - encryption_salt: CharField blank=True (salt base64 per PBKDF2)
  (La password NON viene mai salvata — rimane solo nell'utente)

Aggiungi endpoints in DocumentViewSet:

POST /api/documents/{id}/encrypt/:
  - Solo chi ha can_write O ADMIN
  - Corpo: { "password": "myStrongPassword123" }
  - Prende la versione corrente del documento
  - Chiama DocumentEncryption.encrypt_file(file_path, password)
  - Salva file cifrato come nuova DocumentVersion
    (is_encrypted=True, encryption_salt=salt_b64)
  - Il file originale non viene eliminato (versione precedente rimane)
  - Crea AuditLog: action='document_encrypted'
  - Risponde: { "message": "Documento cifrato", "new_version": N }
  - IMPORTANTE: non salvare mai la password, comunicarlo nell'API response:
    "Conserva la password in un luogo sicuro. Non è recuperabile."

POST /api/documents/{id}/decrypt_download/:
  - Solo chi ha can_read
  - Corpo: { "password": "myStrongPassword123" }
  - Verifica versione corrente is_encrypted=True
  - Tenta DocumentEncryption.decrypt_file(encrypted_path, password)
  - Se cryptography.exceptions.InvalidTag: 400 "Password non corretta"
  - Se successo: risponde con FileResponse del contenuto decifrato
    (Content-Disposition: attachment, nome file originale senza .enc)
  - Crea AuditLog: action='document_decrypted'
  - Il file cifrato rimane sul server (non viene decifrato in-place)

Frontend:
  
  Aggiungi in DocumentDetailPanel (o DocumentTable context menu):
  
  EncryptDocumentModal.tsx:
    - Warning: "La cifratura è irreversibile senza la password.
      Non dimenticarla: non è recuperabile."
    - Input password + conferma password (validazione: min 8 char)
    - Checkbox "Ho letto e compreso il rischio"
    - Bottone "Cifra Documento"
    - Success: "Documento cifrato. Versione N creata."
  
  DecryptDownloadModal.tsx:
    - "Questo documento è cifrato. Inserisci la password per scaricarlo."
    - Input password
    - Bottone "Scarica documento decifrato"
    - Errore password sbagliata: messaggio chiaro
  
  Nel DocumentDetailPanel e DocumentTable:
    - Badge 🔒 accanto a documenti con versione corrente cifrata
    - Azione "Cifra" per documenti non cifrati
    - Azione "Scarica (decifra)" invece di download normale per documenti cifrati

TEST:
  - Encrypt: file cifrato salvato, is_encrypted=True, salt presente
  - Decrypt con password corretta: file originale ritornato
  - Decrypt con password sbagliata: 400
  - AuditLog creato per entrambe le azioni

Esegui: `pytest backend/apps/documents/tests/test_encryption.py -v`
```

---

## STEP 9D.4 — Pannello Gestione Licenza

### Prompt per Cursor:

```
Implementa il pannello di gestione licenza (Documento Collaudo: "Gestione licenze").

Crea `backend/apps/admin_panel/` (nuova app leggera):

Crea `backend/apps/admin_panel/models.py`:

class SystemLicense(models.Model):
  """Unica istanza — configurazione licenza del sistema"""
  - id: int (PK, sempre 1)
  - organization_name: CharField max 500
  - license_key: CharField max 500 (cifrata)
  - activated_at: DateField
  - expires_at: DateField null=True (null = perpetua)
  - max_users: IntegerField null=True (null = illimitato)
  - max_storage_gb: FloatField null=True
  - features_enabled: JSONField default=dict
    Es: {
      "mfa": true,
      "sso": false,
      "ldap": true,
      "digital_signature": true,
      "conservation": true,
      "chat": true,
      "encryption": true,
    }
  - created_at: auto_now_add
  - updated_at: auto_now
  
  class Meta:
    verbose_name = "Licenza di sistema"
  
  @classmethod
  def get_current(cls) → SystemLicense | None
  
  @classmethod
  def is_feature_enabled(cls, feature: str) → bool

Crea `backend/apps/admin_panel/views.py`:

GET /api/admin/license/:
  - Solo ADMIN
  - Risponde con configurazione licenza completa + statistiche real-time:
    {
      "license": { organization, activated_at, expires_at, max_users, features },
      "stats": {
        "active_users": N,
        "total_users": N,
        "storage_used_gb": float,
        "storage_limit_gb": float | null,
        "documents_count": N,
        "expires_in_days": int | null,
        "is_expired": bool,
      }
    }

GET /api/admin/system_info/:
  - Solo ADMIN
  - Info sul sistema:
    {
      "django_version": "...",
      "python_version": "...",
      "database_size_mb": float,
      "redis_connected": bool,
      "ldap_connected": bool,
      "signature_provider": "mock|aruba",
      "conservation_provider": "mock|aruba",
    }

Aggiungi middleware `backend/apps/admin_panel/middleware.py`:
  LicenseCheckMiddleware:
  - Ad ogni request: verifica SystemLicense.get_current()
  - Se licenza scaduta: risponde 402 con { "error": "license_expired", "expires_at": "..." }
  - Escludi: /api/auth/login/, /api/admin/license/, /api/public/
  - In development (DEBUG=True): skip del controllo

Crea management command `backend/apps/admin_panel/management/commands/setup_license.py`:
  - Crea/aggiorna licenza di sistema
  - Args: --org-name, --expires, --max-users, --features
  - Uso: `python manage.py setup_license --org-name "Acme Corp" --max-users 50`

Frontend — aggiungi in Settings/Admin:

LicensePage.tsx (route: /admin/license, solo ADMIN):

  LicenseInfoCard:
    - Nome organizzazione, licenza: valida fino a / perpetua
    - Barra progresso utenti (N/max)
    - Barra progresso storage (N GB / max GB)
    - Badge feature abilitate / disabilitate

  SystemStatsGrid:
    - Card: Utenti attivi oggi
    - Card: Documenti totali
    - Card: Storage usato
    - Card: Firma digitale (provider: mock/aruba)
    - Card: Conservazione (provider: mock/aruba)

  SystemInfoTable:
    - Versioni componenti
    - Stato connessioni (Redis, LDAP, provider)

  LicenseExpiredBanner.tsx (globale, mostrato a tutti gli ADMIN):
    - Banner rosso in cima se licenza scaduta o scade entro 30 giorni
    - "La tua licenza scade tra N giorni. Contatta il supporto."

TEST:
  - GET /api/admin/license/: statistiche corrette
  - LicenseCheckMiddleware: con licenza scaduta → 402
  - LicenseCheckMiddleware: con licenza valida → pass-through
  - is_feature_enabled: feature non in dict → False default

Esegui: `pytest backend/apps/admin_panel/ -v`
```

---

## TEST INTEGRAZIONE FASE 9D

### Prompt per Cursor:

```
Test di integrazione Fase 9D.

1. `pytest backend/apps/users/tests/test_import.py backend/apps/users/tests/test_groups.py backend/apps/documents/tests/test_encryption.py backend/apps/admin_panel/ -v --cov`

2. `npm run test -- --run`

3. Test manuale importazione:
   a) GET /api/users/import/template/?format=csv → scarica template
   b) Riempi il CSV con 5 utenti (3 validi, 1 email duplicata, 1 ruolo invalido)
   c) POST /api/users/import/preview/ → preview: 3 valid, 2 invalid
   d) POST /api/users/import/ → 3 utenti creati, report corretto
   e) GET /api/users/import/template/?format=xlsx → scarica Excel template
   f) Ripeti con Excel → stesso risultato

4. Test gruppi:
   a) Crea gruppo "Legale" con 3 utenti
   b) Assegna gruppo a documento (can_read)
   c) Login come utente nel gruppo → documento visibile
   d) Rimuovi utente dal gruppo → documento non più visibile

5. Test cifratura:
   a) POST /api/documents/{id}/encrypt/ con password "Sicuro123!"
      → versione N+1 creata, is_encrypted=True
   b) GET normale download → 400 (documento cifrato, usa decrypt_download)
   c) POST /api/documents/{id}/decrypt_download/ password corretta → file scaricato
   d) POST con password sbagliata → 400 "Password non corretta"

6. Test licenza:
   `python manage.py setup_license --org-name "Test Corp" --max-users 10`
   GET /api/admin/license/ → mostra stats e licenza

Crea `FASE_09D_TEST_REPORT.md`.
```
