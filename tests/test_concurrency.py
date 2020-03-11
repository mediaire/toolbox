import unittest
import tempfile
import shutil
import os

from multiprocessing import Process

from sqlalchemy import create_engine

from mediaire_toolbox.transaction_db.transaction_db import TransactionDB, \
    TransactionDBException
from mediaire_toolbox.transaction_db.model import Transaction

TEST_RANGE = 10
TEST_PROCESS_RANGE = 10
TIMEOUT = 30


def child_process_fn(folder, name):
    transaction_db = _get_temp_db(folder)
    for _ in range(TEST_RANGE):
        transaction_db.create_transaction(Transaction(name=name))
        try:
            transaction_db.get_transaction(1)
        except TransactionDBException:
            pass


def _get_temp_db(temp_folder):
    return TransactionDB(
        create_engine(
            'sqlite:///' + os.path.join(temp_folder, 't.db') + 
            '?check_same_thread=False', connect_args={'timeout': TIMEOUT})
        )


class TestTransactionDBConcurrency(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.temp_folder = tempfile.mkdtemp(suffix='_test_concurrency_')

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.temp_folder)

    def test_concurrency(self):
        db = _get_temp_db(self.temp_folder)
        processes = [
            Process(
                target=child_process_fn,
                args=(self.temp_folder, 'Process_{}'.format(i),))
            for i in range(TEST_PROCESS_RANGE)
        ]
        for p in processes:
            p.start()
        for p in processes:
            p.join()
        for i in range(TEST_PROCESS_RANGE):
            self.assertEqual(
                TEST_RANGE,
                len([
                    t for t in db.session.query(Transaction)
                    .filter(Transaction.name == "Process_{}".format(i))]
                    ))
        last_transaction = (
            db.session.query(Transaction)
            .order_by(Transaction.transaction_id.desc()).first())
        self.assertEqual(
            last_transaction.transaction_id, TEST_RANGE * TEST_PROCESS_RANGE)
