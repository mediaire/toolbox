import unittest
import tempfile
import shutil
import json
import os

from sqlalchemy import create_engine

from mediaire_toolbox.transaction_db import migrations
from mediaire_toolbox.transaction_db.transaction_db import TransactionDB
from mediaire_toolbox.transaction_db.transaction_db import get_transaction_model
from mediaire_toolbox.transaction_db.model import Transaction


class TestMigration(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.temp_folder = tempfile.mkdtemp(suffix='_test_migration_')

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.temp_folder)

    def _get_temp_db(self, test_index):
        return create_engine('sqlite:///' +
                             os.path.join(self.temp_folder,
                                          't' + str(test_index) + '.db') +
                             '?check_same_thread=False')

    def test_migrate_institution(self):
        engine = self._get_temp_db(2)
        t_db = TransactionDB(engine)
        last_message = {
            'data': {
                'dicom_info': {
                    't1': {
                        'header': {
                            'InstitutionName': 'MockInstitution'
                        }}}}}
        tr_1 = Transaction()
        tr_1.last_message = json.dumps(last_message)
        t_id = t_db.create_transaction(tr_1)

        # remove institution field
        session = t_db.session
        tr_2 = t_db.get_transaction(t_id)
        tr_2.institution = ''
        session.commit()
        self.assertEqual('', t_db.get_transaction(t_id).institution)

        # execute migrate python script
        model = get_transaction_model(engine)
        migrations.migrate_institution(session, model)
        session.commit()
        tr_2 = t_db.get_transaction(t_id)
        self.assertEqual('MockInstitution', tr_2.institution)

        t_db.close()

    def test_migrate_sequences(self):
        engine = self._get_temp_db(3)
        t_db = TransactionDB(engine)
        last_message = {
            'data': {
                'dicom_info': {
                    't1': {
                        'header': {
                            'SeriesDescription': 'T1_sequence'
                        }
                    },
                    't2': {
                        'header': {
                            'SeriesDescription': 'T2_sequence'
                    }}}}}
        tr_1 = Transaction()
        tr_1.last_message = json.dumps(last_message)
        t_id = t_db.create_transaction(tr_1)

        # remove sequences field
        session = t_db.session
        tr_2 = t_db.get_transaction(t_id)
        tr_2.institution = ''
        session.commit()
        self.assertEqual('', t_db.get_transaction(t_id).institution)

        # execute migrate python script
        model = get_transaction_model(engine)
        migrations.migrate_sequences(session, model)
        session.commit()
        tr_2 = t_db.get_transaction(t_id)
        self.assertEqual('T1_sequence;T2_sequence', tr_2.sequences)

        t_db.close()
