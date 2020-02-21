import unittest
import tempfile
import shutil
import json
import os

from datetime import datetime
from sqlalchemy import create_engine

from mediaire_toolbox.transaction_db.transaction_db import TransactionDB
from mediaire_toolbox.transaction_db.model import (
    TaskState, Transaction, UserTransaction, User, Role, UserRole
)

from temp_db_base import TempDBFactory

temp_db = TempDBFactory('test_transaction_db')

class TestTransactionDB(unittest.TestCase):
        
    @classmethod
    def tearDownClass(self):
        temp_db.delete_temp_folder()

    def _get_test_transaction(self):
        t = Transaction()
        # we only need to fill metadata before creating a new transaction
        t.name = 'Pere'
        t.patient_id = '1'
        t.study_id = 'S1'
        t.birth_date = datetime(1982, 10, 29)
        return t
    
    def test_create_transaction_index_sequences(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()
        tr_1.last_message = json.dumps({
            'data': {
                'dicom_info': {
                    't1': {'header': {'SeriesDescription': 'series_t1_1'}},
                    't2': {'header': {'SeriesDescription': 'series_t2_1'}}}
            }
        })
        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)
        tr_2 = t_db.get_transaction(t_id)

        self.assertEqual('series_t1_1;series_t2_1',
                         tr_2.sequences)

    def test_get_transaction(self):
        engine = temp_db.get_temp_db()
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
        engine = temp_db.get_temp_db()
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
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        # to be called when a transaction fails
        t_db.set_failed(t_id, 'because it failed')
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.task_state, TaskState.failed)
        self.assertTrue(t.end_date > t.start_date)
        self.assertEqual(t.error, 'because it failed')

        t_db.close()

    def test_transaction_completed(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        # to be called when a transaction completes
        t_db.set_completed(t_id)
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.task_state, TaskState.completed)
        self.assertEqual(t.status, 'unseen')
        self.assertTrue(t.end_date > t.start_date)

        t_db.close()

    def test_transaction_archived(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)
        t = t_db.get_transaction(t_id)
        self.assertEqual(t.archived, 0)
        t_db.set_archived(t_id)
        t = t_db.get_transaction(t_id)
        self.assertEqual(t.archived, 1)
        t_db.close()
        
    def test_set_status(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        t_db.set_status(t_id, 'reviewed')
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.status, 'reviewed')

        t_db.close()

    def test_transaction_skipped(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        # to be called when a transaction is skipped
        t_db.set_skipped(t_id, 'because it is skipped')
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.task_skipped, 1)
        self.assertEqual(t.error, 'because it is skipped')

        t_db.close()

    def test_transaction_cancelled(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        # to be called when a transaction is skipped
        t_db.set_cancelled(t_id, 'because it is cancelled')
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.task_cancelled, 1)
        self.assertEqual(t.error, 'because it is cancelled')

        t_db.close()

    def test_change_last_message(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)

        # update last_message field
        t_db.set_last_message(t_id, 'last_message')
        t = t_db.get_transaction(t_id)

        self.assertEqual(t.last_message, 'last_message')

        t_db.close()

    @unittest.expectedFailure
    def test_fail_on_get_non_existing_transaction(self):
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        t_db.get_transaction(1)

    def test_transaction_with_user_id(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        t_id = t_db.create_transaction(tr_1, user_id)

        t = t_db.get_transaction(t_id)
        self.assertNotEqual(None, t)
        
        ut = t_db.session.query(UserTransaction) \
            .filter_by(transaction_id=t.transaction_id) \
            .filter_by(user_id=user_id).first()
        
        self.assertEqual(ut.user_id, user_id)
        self.assertEqual(t.transaction_id, ut.transaction_id)

        t_db.close()

    def test_transaction_with_product_id(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()
        tr_2 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1, product_id=1)
        t_id_2 = t_db.create_transaction(tr_2, product_id=2)

        t = t_db.get_transaction(t_id)
        self.assertNotEqual(None, t)
        self.assertEqual(1, t.product_id)

        t2 = t_db.get_transaction(t_id_2)
        self.assertNotEqual(None, t2)
        self.assertEqual(2, t2.product_id)

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

    def test_set_patient_consent(self):
        engine = temp_db.get_temp_db()
        tr_1 = self._get_test_transaction()

        t_db = TransactionDB(engine)
        t_id = t_db.create_transaction(tr_1)
        t = t_db.get_transaction(t_id)
        self.assertEqual(0, t.patient_consent)
        # set patient consent
        t_db.set_patient_consent(t_id)
        t = t_db.get_transaction(t_id)
        self.assertEqual(1, t.patient_consent)
        # unset patient consent
        t_db.unset_patient_consent(t_id)
        t = t_db.get_transaction(t_id)
        self.assertEqual(0, t.patient_consent)
        t_db.close()

    def test_add_user_ok(self):
        """test that we can add User entity"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        user = t_db.session.query(User).get(user_id)
        self.assertEqual('Pere', user.name)
        self.assertTrue(user.hashed_password)
    
    def test_remove_user_ok(self):
        """test that we can remove an existing user from the database"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        user = t_db.session.query(User).get(user_id)
        self.assertEqual('Pere', user.name)
        t_db.remove_user(user_id)
        user = t_db.session.query(User).get(user_id)
        self.assertFalse(user)
        
    @unittest.expectedFailure
    def test_add_user_already_exists(self):
        """test that we can't add duplicate users by user name"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        self.assertTrue(user_id >= 0)
        t_db.add_user('Pere', 'pwd')
    
    def test_add_role_ok(self):
        """test that we can add a Role entity"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        t_db.add_role('radiologist', 'whatever', 128)
        role = t_db.session.query(Role).get('radiologist')
        self.assertEqual('whatever', role.description)
        self.assertEqual(128, role.permissions)
            
    @unittest.expectedFailure
    def test_add_role_already_exists(self):
        """test that we can't add the same Role twice"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        t_db.add_role('radiologist', 'whatever')
        t_db.add_role('radiologist', 'whatever')

    def __user_has_role(self, t_db, user_id, role_id):
        return t_db.session.query(UserRole).filter_by(user_id=user_id)\
                                           .filter_by(role_id=role_id)\
                                           .first()

    def test_add_user_role_ok(self):
        """test that we can assign a role to a user"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        t_db.add_role('radiologist', 'whatever', 128)

        t_db.add_user_role(user_id, 'radiologist')
        
        self.assertTrue(self.__user_has_role(t_db, user_id, 'radiologist'))
        
    @unittest.expectedFailure
    def test_add_user_role_fail_on_non_existing_role(self):
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        
        t_db.add_user_role(user_id, 'radiologist')
    
    @unittest.expectedFailure    
    def test_add_user_role_fail_on_non_existing_user(self):
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        t_db.add_role('radiologist', 'whatever')

        t_db.add_user_role(1, 'radiologist')
    
    @unittest.expectedFailure
    def test_add_user_role_already_exists(self):
        """test that we can't assign twice the same role to a user"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        t_db.add_role('radiologist', 'whatever')

        t_db.add_user_role(user_id, 'radiologist')
        t_db.add_user_role(user_id, 'radiologist')

    def test_revoke_user_role_ok(self):
        """test that we can revoke a role from a user"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        t_db.add_role('radiologist', 'whatever', 128)
        
        t_db.add_user_role(user_id, 'radiologist')
        self.assertTrue(self.__user_has_role(t_db, user_id, 'radiologist'))
        t_db.revoke_user_role(user_id, 'radiologist')        
        self.assertFalse(self.__user_has_role(t_db, user_id, 'radiologist'))

    @unittest.expectedFailure
    def test_revoke_user_role_didnt_exist(self):
        """test that an Exception is thrown if we want to revoke an
        already revoked role from a user"""
        engine = temp_db.get_temp_db()
        t_db = TransactionDB(engine)
        user_id = t_db.add_user('Pere', 'pwd')
        t_db.add_role('radiologist', 'whatever')
        
        t_db.revoke_user_role(user_id, 'radiologist')        
