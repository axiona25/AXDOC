#!/bin/bash
# Backup completo: DB + media (FASE 15, RNF-022, RNF-024)
# Uso: ./backup.sh [--full] [--db-only] [--media-only]
# Eseguire da root app: cd /app && ./scripts/backup.sh

set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="${BACKUP_ROOT:-/backups}"
DB_BACKUP_DIR="${BACKUP_DIR:-$BACKUP_ROOT/db}"
MEDIA_BACKUP_DIR="${BACKUP_ROOT}/media"
LOG_FILE="${BACKUP_ROOT}/backup.log"
MEDIA_PATH="${MEDIA_PATH:-/app/media}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$DB_BACKUP_DIR" "$MEDIA_BACKUP_DIR"
touch "$LOG_FILE"

backup_database() {
  log "Avvio backup database MySQL..."
  if python manage.py dbbackup --compress --noinput 2>>"$LOG_FILE"; then
    log "Backup database completato."
  else
    log "ERRORE: backup database fallito."
    return 1
  fi
}

backup_media() {
  log "Avvio backup media files..."
  if [ -d "$MEDIA_PATH" ]; then
    tar -czf "$MEDIA_BACKUP_DIR/media_${TIMESTAMP}.tar.gz" -C "$(dirname "$MEDIA_PATH")" "$(basename "$MEDIA_PATH")" 2>>"$LOG_FILE"
    log "Backup media completato."
  else
    log "Cartella media non trovata ($MEDIA_PATH), skip."
  fi
}

cleanup_old_backups() {
  log "Pulizia backup piu vecchi di $RETENTION_DAYS giorni..."
  find "$DB_BACKUP_DIR" -name "*.dump.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
  find "$MEDIA_BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
  log "Pulizia completata."
}

case "${1:-full}" in
  --db-only) backup_database ;;
  --media-only) backup_media ;;
  *) backup_database && backup_media ;;
esac
cleanup_old_backups
log "Backup completato con successo."
