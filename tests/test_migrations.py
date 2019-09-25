import unittest
import tempfile
import shutil
import json
import os

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine

from mediaire_toolbox.transaction_db import migrations
from mediaire_toolbox.transaction_db.transaction_db import TransactionDB
from mediaire_toolbox.transaction_db.model import Transaction

class TestTransactionDB(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.temp_folder = tempfile.mkdtemp(suffix='_test_transaction_db_')

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

        session = scoped_session(sessionmaker(bind=engine))
        migrations.migrate_institution(session, engine)
        session.commit()
        tr_2 = t_db.get_transaction(t_id)
        self.assertEqual('MockInstitution', tr_2.institution)

        t_db.close()