#!/bin/bash
# Ripristino da backup (FASE 15, RNF-023)
# Uso: ./restore.sh --db backup_file.dump.gz [--media media_backup.tar.gz]

set -e
BACKUP_ROOT="${BACKUP_ROOT:-/backups}"
LOG_FILE="${BACKUP_ROOT}/backup.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

restore_database() {
  local backup_file="$1"
  if [ ! -f "$backup_file" ]; then
    log "File non trovato: $backup_file"
    exit 1
  fi
  log "ATTENZIONE: il ripristino sovrascrivera il database corrente."
  read -p "Confermi? (yes/NO): " confirm
  [ "$confirm" = "yes" ] || { log "Ripristino annullato."; exit 0; }
  log "Ripristino database da $backup_file..."
  python manage.py dbrestore -i "$backup_file" --noinput
  log "Ripristino database completato. Esegui: python manage.py migrate"
}

restore_media() {
  local backup_file="$1"
  if [ ! -f "$backup_file" ]; then
    log "File non trovato: $backup_file"
    exit 1
  fi
  log "Ripristino media da $backup_file..."
  tar -xzf "$backup_file" -C /
  log "Ripristino media completato."
}

while [ $# -gt 0 ]; do
  case "$1" in
    --db) restore_database "$2"; shift 2 ;;
    --media) restore_media "$2"; shift 2 ;;
    *) shift ;;
  esac
done
