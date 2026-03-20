"""
Metadati minimi AGID (Allegato 5 Linee Guida 2024) per documenti, cartelle, fascicoli, email.
FASE 18.
"""

AGID_DOCUMENT_METADATA = {
    "identificativo": "Identificativo univoco del documento",
    "data_creazione": "Data e ora di creazione",
    "autore": "Autore/Operatore che ha creato il documento",
    "oggetto": "Oggetto/titolo del documento",
    "formato": "Formato del file (MIME type)",
    "impronta": "Hash SHA-256 del file",
    "versione": "Numero di versione",
    "stato": "Stato del documento",
    "classificazione": "Codice titolario di classificazione",
    "fascicolo": "Identificativo fascicolo di appartenenza",
    "protocollo": "Numero di protocollo se protocollato",
}

AGID_FOLDER_METADATA = {
    "identificativo": "Identificativo univoco della cartella",
    "nome": "Nome della cartella",
    "data_creazione": "Data di creazione",
    "autore": "Operatore che ha creato la cartella",
    "classificazione": "Codice titolario",
}

AGID_DOSSIER_METADATA = {
    "identificativo": "Codice identificativo del fascicolo",
    "oggetto": "Oggetto/titolo del fascicolo",
    "data_apertura": "Data apertura fascicolo",
    "responsabile": "Responsabile del fascicolo",
    "stato": "Stato (aperto/archiviato)",
    "uo": "Unità organizzativa responsabile",
    "data_chiusura": "Data chiusura/archiviazione",
    "classificazione": "Codice titolario",
    "indice_documenti": "Numero documenti nel fascicolo",
}

AGID_EMAIL_METADATA = {
    "identificativo": "Message-ID email",
    "tipo": "Tipo canale (PEC/email/PEO)",
    "mittente": "Indirizzo mittente",
    "destinatari": "Indirizzi destinatari",
    "oggetto": "Oggetto email",
    "data_ricezione": "Data e ora ricezione",
    "impronta": "Hash SHA-256 del file .eml",
}


def get_agid_metadata_for_document(document):
    """Estrae metadati AGID da un documento."""
    version = getattr(document, "current_version_obj", None)
    return {
        "identificativo": str(document.id),
        "data_creazione": document.created_at.isoformat() if getattr(document, "created_at", None) else "",
        "autore": document.created_by.email if getattr(document, "created_by", None) and document.created_by else "",
        "oggetto": getattr(document, "title", ""),
        "formato": getattr(version, "file_type", "") if version else "",
        "impronta": getattr(version, "checksum", "") if version else "",
        "versione": str(getattr(version, "version_number", 1)) if version else "1",
        "stato": getattr(document, "status", ""),
    }


def get_agid_metadata_for_folder(folder):
    """Estrae metadati AGID da una cartella."""
    return {
        "identificativo": str(folder.id),
        "nome": getattr(folder, "name", ""),
        "data_creazione": folder.created_at.isoformat() if getattr(folder, "created_at", None) else "",
        "autore": folder.created_by.email if getattr(folder, "created_by", None) and folder.created_by else "",
    }


def get_agid_metadata_for_dossier(dossier):
    """Estrae metadati AGID da un fascicolo."""
    uo = ""
    if getattr(dossier, "responsible", None) and dossier.responsible:
        from apps.organizations.models import OrganizationalUnitMembership
        m = OrganizationalUnitMembership.objects.filter(user=dossier.responsible, is_active=True).first()
        if m and m.organizational_unit:
            uo = m.organizational_unit.name or ""
    count = dossier.dossier_documents.count() if hasattr(dossier, "dossier_documents") else 0
    return {
        "identificativo": getattr(dossier, "identifier", ""),
        "oggetto": getattr(dossier, "title", ""),
        "data_apertura": dossier.created_at.isoformat() if getattr(dossier, "created_at", None) else "",
        "responsabile": dossier.responsible.email if getattr(dossier, "responsible", None) and dossier.responsible else "",
        "stato": getattr(dossier, "status", ""),
        "uo": uo,
        "data_chiusura": dossier.archived_at.isoformat() if getattr(dossier, "archived_at", None) and dossier.archived_at else "",
        "indice_documenti": count,
    }
