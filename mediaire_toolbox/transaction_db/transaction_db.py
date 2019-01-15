import logging
from sqlalchemy.orm import sessionmaker

from mediaire_toolbox.constants import TRANSACTIONS_DB_SCHEMA_NAME, \
                                       TRANSACTIONS_DB_SCHEMA_VERSION
from mediaire_toolbox.transaction_db.model import Transaction, \
                                                  SchemaVersion, \
                                                  create_all
from mediaire_toolbox.task_state import TaskState
from mediaire_toolbox.logging import base_logging_conf
from mediaire_toolbox.transaction_db import migrations
import datetime

base_logging_conf.basic_logging_conf()
logger = logging.getLogger(__name__)


def migrate(session, db_version):
    """Implementing database migration using a similar idea to Flyway:
    
    https://flywaydb.org/getstarted/firststeps/commandline
    
    We store the schema version in the database and we apply migrations in
    increasing order until we meet the current version.
    There are plenty of schema migration tools but at this point it's not clear
    if we need to add the complexity of such tools on our stack. So we do it
    ourselves here."""
    from_schema_version = db_version.schema_version
    for version in range(from_schema_version + 1, TRANSACTIONS_DB_SCHEMA_VERSION + 1):
        logger.info("Applying database migration to version %s" % version)
        try:
            for command in migrations.MIGRATIONS[version]:
                session.execute(command)
            db_version.schema_version = version
            session.commit()
        except Exception as e:
            session.rollback()
            raise e 


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
        db_version = self.session.query(SchemaVersion).get(TRANSACTIONS_DB_SCHEMA_NAME)
        if not db_version:
            # it's the first time that we create the database
            # therefore we don't have a row in the table 'schema_version'
            # ... which indicates the version of the transactions DB
            db_version.schema_version = TRANSACTIONS_DB_SCHEMA_VERSION
            self.session.add(db_version)
            self.session.commit()
        else:
            # check if the existing database is old, and if so migrate
            if db_version.schema_version < TRANSACTIONS_DB_SCHEMA_VERSION:
                migrate(self.session, db_version)

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
                       last_message: str,
                       task_progress:int=0
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
        task_progress
            Signals the relative progress to completion of the task
        """
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.processing_state = new_processing_state
            t.task_state = TaskState.processing
            t.last_message = last_message
            t.task_progress = task_progress
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
