import json

from mediaire_toolbox.transaction_db import index

"""SQL Commands that need to be issued in order to migrate the TransactionsDB
from one version to another. Keyed by target version ID."""
MIGRATIONS = {
    2: [
        "ALTER TABLE transactions ADD COLUMN task_progress INT DEFAULT 0",
        "UPDATE transactions SET task_progress = 10 WHERE processing_state = 'spm_lesion'",
        "UPDATE transactions SET task_progress = 10 WHERE processing_state = 'spm_volumetry'",
        "UPDATE transactions SET task_progress = 80 WHERE processing_state = 'volumetry_assessment'",
        "UPDATE transactions SET task_progress = 90 WHERE processing_state = 'report'",
        "UPDATE transactions SET task_progress = 100 WHERE processing_state = 'send_to_pacs'"    
    ],
    3: [
        "ALTER TABLE transactions ADD COLUMN task_skipped INT DEFAULT 0",
    ],
    4: [
        "ALTER TABLE transactions ADD COLUMN task_cancelled INT DEFAULT 0",
    ],
    5: [
        "ALTER TABLE transactions ADD COLUMN status TEXT",
        "ALTER TABLE transactions ADD COLUMN institution TEXT",
        "ALTER TABLE transactions ADD COLUMN sequences TEXT",
        "UPDATE transactions SET status = 'sent_to_pacs' WHERE processing_state = 'send_to_pacs'",
        "UPDATE transactions SET status = 'unseen' WHERE processing_state != 'send_to_pacs'"
    ],
    6: [
        "ALTER TABLE transactions ADD COLUMN archived INT DEFAULT 0",
    ],
    7: [
        "ALTER TABLE transactions ADD COLUMN study_date TEXT",    
    ],
    8: [
        "ALTER TABLE transactions ADD COLUMN patient_consent INT DEFAULT 0",
    ]
}


def migrate_institution(session, model):
    for transaction in session.query(model).all():
        index.index_institution(transaction)


def migrate_sequences(session, model):
    for transaction in session.query(model).all():
        index.index_sequences(transaction)


def migrate_study_date(session, model):
    for transaction in session.query(model).all():
        index.index_study_date(transaction)


MIGRATIONS_SCRIPTS = {
    5: [
        migrate_institution,
        migrate_sequences,
    ],
    7: [
        migrate_study_date
    ]
}
