"""
Titolario di classificazione e massimario di scarto (FASE 21).
"""

TITOLARIO_DEFAULT = [
    {
        "code": "1",
        "label": "Amministrazione generale",
        "children": [
            {"code": "1.1", "label": "Statuto e atti costitutivi", "retention": 0, "action": "permanent_preserve", "basis": "Permanente"},
            {"code": "1.2", "label": "Organigramma e funzionigramma", "retention": 10, "action": "review", "basis": "DPR 445/2000"},
            {"code": "1.3", "label": "Regolamenti interni", "retention": 0, "action": "permanent_preserve"},
            {"code": "1.4", "label": "Delibere e verbali", "retention": 0, "action": "permanent_preserve"},
            {"code": "1.5", "label": "Corrispondenza generale", "retention": 5, "action": "discard"},
        ],
    },
    {
        "code": "2",
        "label": "Gestione del personale",
        "children": [
            {"code": "2.1", "label": "Assunzioni e contratti", "retention": 10, "action": "review", "basis": "D.Lgs 276/2003"},
            {"code": "2.2", "label": "Buste paga e cedolini", "retention": 10, "action": "discard"},
            {"code": "2.3", "label": "Fascicoli personali", "retention": 50, "action": "review"},
            {"code": "2.4", "label": "Formazione e aggiornamento", "retention": 5, "action": "discard"},
        ],
    },
    {
        "code": "3",
        "label": "Gestione finanziaria e contabile",
        "children": [
            {"code": "3.1", "label": "Bilanci e rendiconti", "retention": 10, "action": "review", "basis": "Art. 2220 CC"},
            {"code": "3.2", "label": "Fatture e documenti fiscali", "retention": 10, "action": "discard", "basis": "DPR 633/1972"},
            {"code": "3.3", "label": "Contratti e convenzioni", "retention": 10, "action": "review"},
            {"code": "3.4", "label": "Mandati di pagamento", "retention": 10, "action": "discard"},
        ],
    },
    {
        "code": "4",
        "label": "Patrimonio e beni",
        "children": [
            {"code": "4.1", "label": "Inventari beni mobili/immobili", "retention": 0, "action": "permanent_preserve"},
            {"code": "4.2", "label": "Manutenzione e appalti", "retention": 10, "action": "review"},
        ],
    },
    {
        "code": "5",
        "label": "Attività istituzionale",
        "children": [
            {"code": "5.1", "label": "Procedimenti amministrativi", "retention": 10, "action": "review"},
            {"code": "5.2", "label": "Autorizzazioni e licenze", "retention": 0, "action": "permanent_preserve"},
            {"code": "5.3", "label": "Comunicazioni istituzionali", "retention": 5, "action": "discard"},
        ],
    },
    {
        "code": "6",
        "label": "Documentazione tecnica",
        "children": [
            {"code": "6.1", "label": "Progetti e elaborati tecnici", "retention": 20, "action": "review"},
            {"code": "6.2", "label": "Collaudi e certificazioni", "retention": 10, "action": "review"},
            {"code": "6.3", "label": "Manuali e specifiche", "retention": 10, "action": "review"},
        ],
    },
    {
        "code": "7",
        "label": "Sicurezza e privacy",
        "children": [
            {"code": "7.1", "label": "GDPR - Consensi e informative", "retention": 5, "action": "review", "basis": "GDPR art. 17"},
            {"code": "7.2", "label": "DVR - Sicurezza sul lavoro", "retention": 10, "action": "review", "basis": "D.Lgs 81/2008"},
            {"code": "7.3", "label": "Audit log e accessi", "retention": 5, "action": "discard"},
        ],
    },
]
