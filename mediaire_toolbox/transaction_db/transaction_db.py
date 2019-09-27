import logging

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, scoped_session

from mediaire_toolbox.constants import TRANSACTIONS_DB_SCHEMA_NAME, \
                                       TRANSACTIONS_DB_SCHEMA_VERSION
from mediaire_toolbox.transaction_db.model import Transaction, \
                                                  SchemaVersion, \
                                                  create_all
from mediaire_toolbox.task_state import TaskState
from mediaire_toolbox.transaction_db import migrations
from mediaire_toolbox.transaction_db import index
import datetime

logger = logging.getLogger(__name__)


def get_transaction_model(engine):
    Base = automap_base()
    Base.prepare(engine, reflect=True)
    return Base.classes.transactions


def migrate_scripts(session, engine, current_version, target_version):
    model = get_transaction_model(engine)
    for version in range(current_version + 1, target_version + 1):
        try:
            for script in migrations.MIGRATIONS_SCRIPTS.get(
                    version, []):
                script(session, model)
            session.commit()
        except Exception as e:
            session.rollback()
            session.close()
            raise e
    session.close()


def migrate(session, engine, db_version):
    """Implementing database migration using a similar idea to Flyway:
    
    https://flywaydb.org/getstarted/firststeps/commandline
    
    We store the schema version in the database and we apply migrations in
    increasing order until we meet the current version.
    There are plenty of schema migration tools but at this point it's not clear
    if we need to add the complexity of such tools on our stack. So we do it
    ourselves here.
    
    After migrating with sql commands (changing dababase schema),
    we also run python scripts to index values parsed from the dicom header.
    Note that the schema_version does not correspond to the indexed values:
    i.e a schema_version of 5 does not mean the values are indexed.
    """
    from_schema_version = db_version.schema_version
    for version in range(from_schema_version + 1, TRANSACTIONS_DB_SCHEMA_VERSION + 1):
        logger.info("Applying database migration to version %s" % version)
        try:
            for command in migrations.MIGRATIONS[version]:
                session.execute(command).close()
            db_version.schema_version = version
            session.commit()
        except Exception as e:
            session.rollback()
            session.close()
            raise e
    for version in range(from_schema_version + 1, TRANSACTIONS_DB_SCHEMA_VERSION + 1):
        migrate_scripts(
            session, engine,
            from_schema_version, TRANSACTIONS_DB_SCHEMA_VERSION)


class TransactionDB:
    """Connection to a DB of transactions where we can track status, failures, 
    elapsed time, etc."""

    def __init__(self, engine):
        """
        Parameters
        ----------
        engine: SQLAlchemy engine
        """
        self.session = scoped_session(sessionmaker(bind=engine))
        create_all(engine)
        db_version = self.session.query(SchemaVersion).get(TRANSACTIONS_DB_SCHEMA_NAME)
        if not db_version:
            # it's the first time that we create the database
            # therefore we don't have a row in the table 'schema_version'
            # ... which indicates the version of the transactions DB
            self.session.add(SchemaVersion())
            self.session.commit()
        else:
            # check if the existing database is old, and if so migrate
            if db_version.schema_version < TRANSACTIONS_DB_SCHEMA_VERSION:
                migrate(self.session, engine, db_version)

    def create_transaction(self, t: Transaction) -> int:
        """will set the provided transaction object as queued, 
        add it to the DB and return the transaction id.
        
        If the transaction"""
        try:
            t.task_state = TaskState.queued
            self.session.add(t)
            self.session.commit()

            #index.index_institution(t)
            index.index_sequences(t)
            self.session.commit()
            return t.transaction_id
        except Exception:
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

    def set_completed(self, id_: int, clear_error: bool=True):
        """to be called when the transaction completes successfully.
        Error field will be set to '' only if clear_error = True.
        End_date automatically adjusted. Status is automatically set to 
        'unseen'."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_state = TaskState.completed
            t.status = 'unseen'
            t.end_date = datetime.datetime.utcnow()
            if clear_error:
                t.error = ''
            self.session.commit()
        except:
            self.session.rollback()
            raise
        
    def set_status(self, id_: int, status: str):
        """to be called e.g. when the radiologist visits the results of a study
        in the new platform ('reviewed') or the report is sent to the PACS
        ('sent_to_pacs') ..."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.status = status
            t.end_date = datetime.datetime.utcnow()
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def set_skipped(self, id_: int, cause: str=None):
        """to be called when the transaction is skipped. Save skip information
        from 'cause'"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_skipped = 1
            t.end_date = datetime.datetime.utcnow()
            if cause:
                t.error = cause
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def set_cancelled(self, id_: int, cause: str=None):
        """to be called when the transaction is cancelled. Save cancel information
        from 'cause'"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_cancelled = 1
            t.end_date = datetime.datetime.utcnow()
            if cause:
                t.error = cause
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def set_archived(self, id_: int):
        """to be called when the transaction is archived."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.archived = 1
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def set_last_message(self, id_: int, last_message: str):
        """Updates the last_message field of the transaction
        with the given string."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.last_message = last_message
            self.session.commit()
        except:
            self.session.rollback()
            raise

    def close(self):
        self.session.close()


class TransactionDBException(Exception):

    def __init__(self, msg):
        super().__init__(self, msg)
