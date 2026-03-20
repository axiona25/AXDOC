"""
Stato backup: ultimi 10 backup db e media (FASE 15).
Uso: python manage.py backup_status
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Lista ultimi backup con data, dimensione e tipo"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10, help="Numero massimo backup per tipo")

    def handle(self, *args, **options):
        limit = options["limit"]
        backup_dir = getattr(settings, "DBBACKUP_STORAGE_OPTIONS", {}).get("location", "/backups/db")
        media_dir = os.path.join(os.path.dirname(backup_dir.rstrip("/")), "media") if backup_dir else "/backups/media"

        def file_info(path, pattern, label):
            if not os.path.isdir(path):
                return []
            out = []
            for f in sorted(os.listdir(path), reverse=True):
                if pattern not in f:
                    continue
                fp = os.path.join(path, f)
                if not os.path.isfile(fp):
                    continue
                try:
                    size = os.path.getsize(fp)
                    mtime = os.path.getmtime(fp)
                    from datetime import datetime
                    out.append({
                        "name": f,
                        "size": size,
                        "date": datetime.fromtimestamp(mtime).isoformat(),
                        "type": label,
                    })
                except OSError:
                    out.append({"name": f, "size": None, "date": None, "type": label, "error": "inaccessible"})
            return out[:limit]

        db_backups = file_info(backup_dir, ".dump", "db")
        media_backups = file_info(media_dir, ".tar.gz", "media")

        self.stdout.write("=== Backup DB ===")
        for b in db_backups:
            size_str = f"{b['size'] / 1024:.1f} KB" if b.get("size") else "?"
            self.stdout.write(f"  {b['name']}  {size_str}  {b.get('date', '?')}")
        if not db_backups:
            self.stdout.write("  Nessun backup trovato.")

        self.stdout.write("\n=== Backup Media ===")
        for b in media_backups:
            size_str = f"{b['size'] / (1024*1024):.2f} MB" if b.get("size") else "?"
            self.stdout.write(f"  {b['name']}  {size_str}  {b.get('date', '?')}")
        if not media_backups:
            self.stdout.write("  Nessun backup trovato.")
