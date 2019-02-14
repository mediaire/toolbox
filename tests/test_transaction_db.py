import unittest
import tempfile
import shutil
import json
import os

from datetime import datetime
from sqlalchemy import create_engine

from mediaire_toolbox.transaction_db.transaction_db import TransactionDB
from mediaire_toolbox.transaction_db.model import (
    TaskState, Transaction, UserTransaction
)

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

    def _get_test_transaction(self):
        t = Transaction()
        # we only need to fill metadata before creating a new transaction
        t.name = 'Pere'
        t.patient_id = '1'
        t.study_id = 'S1'
        t.birth_date = datetime(1982, 10, 29)
        return t

    def test_get_transaction(self):
        engine = self._get_temp_db(1)
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)
        # the engine returns the ID of the newly created transaction
        tr_2 = t_db.get_transaction(t_id)

        self.assertEqual(tr_1.name, tr_2.name)
        self.assertEqual(tr_1.patient_id, tr_2.patient_id)
        self.assertEqual(tr_1.study_id, tr_2.study_id)
        self.assertTrue(tr_2.start_date)
        self.assertEqual(t_id, tr_2.transaction_id)
        self.assertEqual(tr_2.task_state, TaskState.queued)

        t_db.close()

    def test_change_processing_state(self):
        engine = self._get_temp_db(2)
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)
        # called when a transaction changes its processing state
        t_db.set_processing(t_id, 'spm_volumetry', '{}', 10)
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.processing_state, 'spm_volumetry')
        self.assertEqual(t.task_state, TaskState.processing)
        self.assertEqual(t.task_progress, 10)

        t_db.close()

    def test_transaction_failed(self):
        engine = self._get_temp_db(3)
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        # to be called when a transaction fails
        t_db.set_failed(t_id, 'because it failed')
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.task_state, TaskState.failed)
        self.assertEqual(t.error, 'because it failed')

        t_db.close()

    def test_transaction_completed(self):
        engine = self._get_temp_db(4)
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        # to be called when a transaction completes
        t_db.set_completed(t_id)
        t = t_db.get_transaction(t_id)

        self.assertTrue(t.end_date > t.start_date)

        t_db.close()

    @unittest.expectedFailure
    def test_fail_on_get_non_existing_transaction(self):
        engine = self._get_temp_db(5)
        t_db = TransactionDB(engine)
        t_db.get_transaction(1)

    def test_transaction_with_user_id(self):
        engine = self._get_temp_db(6)
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1, 1)

        t = t_db.get_transaction(t_id)
        self.assertNotEqual(None, t)
        
        ut = t_db.session.query(UserTransaction) \
            .filter_by(transaction_id=t.transaction_id) \
            .filter_by(user_id=1).first()
        
        self.assertEqual(ut.user_id, 1)
        self.assertEqual(t.transaction_id, ut.transaction_id)

        t_db.close()
        
    def test_migrations(self):
        temp_folder = tempfile.mkdtemp(suffix='_test_migrations_transaction_db_')
        temp_db_path = os.path.join(temp_folder, 't_v1.db')
        shutil.copy('tests/fixtures/t_v1.db', temp_db_path)
        engine = create_engine('sqlite:///' + temp_db_path)
        # should execute all migrations code
        t_db = TransactionDB(engine)
        # add a new transaction with the current model
        t = Transaction()
        t_db.create_transaction(t)
        shutil.rmtree(temp_folder)
        
    def test_json_serialization(self):
        t = self._get_test_transaction()
        t.task_state = TaskState.completed
        t.start_date = datetime.utcnow()
        t.end_date = datetime.utcnow()
        self.assertTrue(t.to_dict()['task_state'] == 'completed')
        json.dumps(t.to_dict())
