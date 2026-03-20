# Cifratura dati a riposo (RNF-002) — FASE 15

La cifratura a riposo si implementa su più livelli.

## Livello 1 — MySQL InnoDB (tablespace encryption)

Per abilitare la cifratura dei tablespace InnoDB:

1. **Preparare il keyring** (directory con chiave):

   ```bash
   mkdir -p /var/lib/mysql-keyring
   chown mysql:mysql /var/lib/mysql-keyring
   ```

2. **Avviare MySQL con opzioni di cifratura** (es. in `docker-compose` o `command`):

   ```yaml
   db:
     command: >
       mysqld
       --innodb-encrypt-tables=ON
       --innodb-encrypt-log=ON
       --innodb-encryption-key-id=1
       --early-plugin-load=keyring_file.so
       --keyring-file-data=/var/lib/mysql-keyring/keyring
     volumes:
       - mysql_data:/var/lib/mysql
       - mysql_keyring:/var/lib/mysql-keyring
   ```

3. **Verificare che la cifratura sia attiva**:

   ```sql
   SELECT * FROM information_schema.INNODB_TABLESPACES_ENCRYPTION;
   ```

4. **Backup delle chiavi (critico)**  
   Senza il keyring non è possibile decifrare i dati. Eseguire backup sicuro di `/var/lib/mysql-keyring/` e conservarlo separatamente dai backup del database.

## Livello 2 — Campi sensibili nell’applicazione

Per cifrare campi sensibili (es. token, risposte provider) si può usare `django-encrypted-model-fields`:

- `FIELD_ENCRYPTION_KEY` in settings (chiave Fernet)
- Sostituire i campi con `EncryptedCharField`, `EncryptedJSONField` dove necessario
- Generare chiave:  
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Livello 3 — File media (S3 con SSE)

Vedi `S3_STORAGE.md` per l’uso di S3 con cifratura server-side (SSE-S3 o SSE-KMS).
