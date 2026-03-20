"""
Generazione pacchetti informativi AGID: PdV (Versamento), PdA (Archiviazione), PdD (Distribuzione).
"""
import io
import json
import zipfile
import hashlib
from datetime import datetime
from django.utils import timezone


class AgidPackager:
    """Genera pacchetti PdV/PdA/PdD conformi alle linee guida AGID."""

    def generate_pdv(self, documents, protocols=None, dossiers=None):
        """
        Genera Pacchetto di Versamento (PdV).
        Struttura ZIP:
        ├── manifest.json
        ├── documents/{uuid}_{filename}
        ├── documents/{uuid}_metadata.json
        ├── protocols/{numero}/scheda_protocollo.pdf
        ├── dossiers/{codice}/indice_fascicolo.pdf
        └── checksums.sha256
        Ritorna (zip_bytes, manifest_dict).
        """
        protocols = protocols or []
        dossiers = dossiers or []
        manifest = {
            "type": "PdV",
            "created_at": timezone.now().isoformat(),
            "document_ids": [str(d.id) for d in documents],
            "protocol_ids": [str(p.id) for p in protocols],
            "dossier_ids": [str(d.id) for d in dossiers],
            "entries": [],
        }
        buf = io.BytesIO()
        checksums = []
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in documents:
                entry = {"type": "document", "id": str(doc.id), "path": ""}
                fname = getattr(doc, "title", "") or str(doc.id)
                safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in fname)[:100]
                base = f"documents/{doc.id}_{safe_name}"
                meta = {
                    "id": str(doc.id),
                    "title": getattr(doc, "title", ""),
                    "created_at": getattr(doc, "created_at", None).isoformat() if getattr(doc, "created_at", None) else None,
                }
                zf.writestr(f"{base}_metadata.json", json.dumps(meta, indent=2))
                entry["path"] = f"{base}_metadata.json"
                # Placeholder per il file (in produzione si leggerebbe doc.current_version.file)
                content = b"%PDF-1.4 placeholder"
                zf.writestr(f"{base}.bin", content)
                chk = hashlib.sha256(content).hexdigest()
                checksums.append(f"{chk}  {base}.bin")
                manifest["entries"].append(entry)
            for prot in protocols:
                num = getattr(prot, "protocol_id", None) or str(prot.id)
                path = f"protocols/{num}/scheda_protocollo.pdf"
                content = b"%PDF-1.4 protocol placeholder"
                zf.writestr(path, content)
                checksums.append(f"{hashlib.sha256(content).hexdigest()}  {path}")
                manifest["entries"].append({"type": "protocol", "id": str(prot.id), "path": path})
            for doss in dossiers:
                code = getattr(doss, "identifier", None) or str(doss.id)
                path = f"dossiers/{code}/indice_fascicolo.pdf"
                content = b"%PDF-1.4 dossier placeholder"
                zf.writestr(path, content)
                checksums.append(f"{hashlib.sha256(content).hexdigest()}  {path}")
                manifest["entries"].append({"type": "dossier", "id": str(doss.id), "path": path})
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("checksums.sha256", "\n".join(checksums))
        buf.seek(0)
        return buf.getvalue(), manifest

    def generate_pdd(self, package):
        """Genera Pacchetto di Distribuzione da un PdA esistente."""
        # In produzione si leggerebbe package.package_file e si riorganizzerebbe per distribuzione
        buf = io.BytesIO()
        manifest = {
            "type": "PdD",
            "source_package_id": str(package.package_id),
            "created_at": timezone.now().isoformat(),
        }
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        buf.seek(0)
        return buf.getvalue()
