from sqlalchemy.orm import sessionmaker

from mediaire_toolbox.transaction_db.model import Transaction, create_all
from mediaire_toolbox.task_state import TaskState

import datetime


class TransactionDB:
    """Connection to a DB of transactions where we can track status, failures, 
    elapsed time, etc."""

    def __init__(self, engine):
        """
        Parameters
        ----------
        engine: SQLAlchemy engine
        """
        DBSession = sessionmaker(bind=engine)
        self.session = DBSession()
        create_all(engine)

    def create_transaction(self, t: Transaction) -> int:
        """will set the provided transaction object as queued, 
        add it to the DB and return the transaction id."""
        try:
            t.task_state = TaskState.queued
            self.session.add(t)
            self.session.commit()
            return t.transaction_id
        except:
            self.session.rollback()
            raise

    def get_transaction(self, id_: int) -> Transaction:
        try:
            return self._get_transaction_or_raise_exception(id_)
        finally:
            # we should always complete the lifetime of the connection,
            # otherwise we might run into timeout errors
            # (see https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html)
            self.session.commit()

    def _get_transaction_or_raise_exception(self, id_: int):
        t = self.session.query(Transaction).get(id_)
        if t:
            return t
        else:
            raise TransactionDBException("""
                transaction doesn't exist in DB (%s)
                """ % id)

    def set_processing(self,
                       id_: int,
                       new_processing_state: str,
                       last_message: str
                       ):
        """to be called when a transaction changes from one processing task
        to another
        
        Parameters
        ----------
        id_
            Transaction ID
        new_processing_state
            State this transaction has switched to
        last_message
            Payload (task object) as serialized JSON string
            We require a string to be compatible with most RDBMS
            For those which support JSON we can always cast in query time
            (https://stackoverflow.com/questions/16074375/postgresql-9-2-convert-text-json-string-to-type-json-hstore)
        """
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.processing_state = new_processing_state
            t.task_state = TaskState.processing
            t.last_message = last_message
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def set_failed(self, id_: int, cause: str):
        """to be called when a transaction fails. Save error information
        from 'cause'"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_state = TaskState.failed
            t.end_date = datetime.datetime.utcnow()
            t.error = cause
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def set_completed(self, id_: int):
        """to be called when the transaction completes successfully.
        Error field will be set explicitly to '' and end_date automatically
        adjusted."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_state = TaskState.completed
            t.end_date = datetime.datetime.utcnow()
            t.error = ''
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def close(self):
        self.session.close()


class TransactionDBException(Exception):

    def __init__(self, msg):
        super().__init__(self, msg)
