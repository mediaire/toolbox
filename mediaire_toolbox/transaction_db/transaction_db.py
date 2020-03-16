import logging

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, scoped_session

from mediaire_toolbox.constants import TRANSACTIONS_DB_SCHEMA_NAME, \
    TRANSACTIONS_DB_SCHEMA_VERSION
from mediaire_toolbox.transaction_db.model import Transaction, \
    SchemaVersion, \
    create_all, \
    UserTransaction, \
    User, \
    Role, \
    UserRole

from mediaire_toolbox.transaction_db.exceptions import TransactionDBException
from mediaire_toolbox.transaction_db import migrations
from mediaire_toolbox.transaction_db import index
from mediaire_toolbox.task_state import TaskState
from mediaire_toolbox.transaction_db.t_db_retry import t_db_retry

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

    def __init__(self, engine, create_db=True):
        """
        Parameters
        ----------
        engine: SQLAlchemy engine
        create_db: bool
            If true, database will be updated/created
        """
        self.session = scoped_session(sessionmaker(bind=engine))
        if create_db:
            create_all(engine)
            db_version = self.session.query(
                SchemaVersion).get(TRANSACTIONS_DB_SCHEMA_NAME)
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

    def create_transaction(
            self, t: Transaction,
            user_id=None, product_id=None) -> int:
        """will set the provided transaction object as queued,
        add it to the DB and return the transaction id.

        If the transaction has a last_message JSON with chosen T1/T2,
        it will index the sequence names as well.

        Parameters
        ----------
        user_id: int
        product_id: int
        """
        try:
            t.task_state = TaskState.queued
            if product_id:
                t.product_id = product_id
            self.session.add(t)
            # when we commit, we get the transaction ID
            self.session.commit()
            if user_id:
                user = self.session.query(User).get(user_id)
                if not user:
                    raise TransactionDBException(("The provided user doesn't "
                                                  "exist"))
                ut = UserTransaction()
                ut.user_id = user_id
                ut.transaction_id = t.transaction_id
                self.session.add(ut)
            self.session.commit()

            # index.index_institution(t)
            index.index_sequences(t)
            self.session.commit()
            return t.transaction_id
        except Exception:
            self.session.rollback()
            if(t.transaction_id):
                self.session.delete(t)
            raise

    @t_db_retry
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

    @t_db_retry
    def set_queued(self,
                   id_: int,
                   last_message: str = None):
        """queues the Transaction and sets its processing state as 
        'waiting'. This signals consumers that this transaction shouldn't
        continue and will be polled in the future.
        
        Parameters
        ----------
        id_
            Transaction ID
        last_message
            stringified JSON metadata to save"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_state = TaskState.queued
            t.processing_state = 'waiting'
            if last_message:
                t.last_message = last_message
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
    def peek_queued(self):
        """Peeks the oldest queued transaction from the database, if any.
        Note that this is a peek, not a poll operation, so unless the 
        transaction is moved into processing state, it will be returned
        again on a subsequent call.
        
        Returns
        -------
            A Transaction object, or None"""
        # NOTE assumming that a transaction with low
        # transactions_id is created earlier
        queued = self.session.query(Transaction) \
            .filter(Transaction.task_state == TaskState.queued) \
            .filter(Transaction.processing_state == 'waiting') \
            .order_by(Transaction.transaction_id.asc())
        if queued:
            return queued.first()
        return None

    @t_db_retry
    def set_processing(self,
                       id_: int,
                       new_processing_state: str,
                       last_message: str,
                       task_progress: int=0
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
            if not t.start_date:
                # set start date first time transaction was set to processing
                t.start_date = datetime.datetime.utcnow()
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
    def set_failed(self, id_: int, cause: str):
        """to be called when a transaction fails. Save error information
        from 'cause'"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_state = TaskState.failed
            if not t.start_date:
                # set start date if doesnt exist
                t.start_date = datetime.datetime.utcnow()
            if not t.end_date:
                t.end_date = datetime.datetime.utcnow()
            t.error = cause
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
    def set_completed(self, id_: int, clear_error: bool=True):
        """to be called when the transaction completes successfully.
        Error field will be set to '' only if clear_error = True.
        End_date automatically adjusted. Status is automatically set to 
        'unseen' (unless it was already reviewed)."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_state = TaskState.completed
            if not t.status or t.status == '':
                t.status = 'unseen'
            if not t.start_date:
                # set start date if doesnt exist
                t.start_date = datetime.datetime.utcnow()
            if not t.end_date:
                t.end_date = datetime.datetime.utcnow()
            if clear_error:
                t.error = ''
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
    def set_status(self, id_: int, status: str):
        """to be called e.g. when the radiologist visits the results of a study
        in the new platform ('reviewed') or the report is sent to the PACS
        ('sent_to_pacs') ..."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.status = status
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
    def set_skipped(self, id_: int, cause: str=None):
        """to be called when the transaction is skipped. Save skip information
        from 'cause'"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_skipped = 1
            if cause:
                t.error = cause
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
    def set_cancelled(self, id_: int, cause: str=None):
        """to be called when the transaction is cancelled. Save cancel information
        from 'cause'"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.task_cancelled = 1
            if cause:
                t.error = cause
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
    def set_archived(self, id_: int):
        """to be called when the transaction is archived."""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.archived = 1
            self.session.commit()
        except:
            self.session.rollback()
            raise

    @t_db_retry
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

    @t_db_retry
    def set_patient_consent(self, id_: int):
        """Mark this transaction ID with data usage patient consent"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.patient_consent = 1
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    @t_db_retry
    def unset_patient_consent(self, id_: int):
        """Mark this transaction ID with NO data usage patient consent"""
        try:
            t = self._get_transaction_or_raise_exception(id_)
            t.patient_consent = 0
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    @t_db_retry
    def add_user(self, name, password):
        """For multi-tenant transaction DBs, add a new user to it.
        
        The provided (clear) password will be hashed in the database.
        Returns the user ID set by the database upon successful insert.
        
        TransactionDBException will be thrown if a user with the same
        name already exists."""
        try:
            user = self.session.query(User).filter_by(name=name).first()
            if user:
                raise TransactionDBException(("A user with the same "
                                              "name already exists"))

            user = User()
            user.name = name
            user.hashed_password = user.password_hash(password)
            self.session.add(user)
            self.session.commit()
            user = self.session.query(User).filter_by(name=name).first()
            return user.id
        finally:
            self.session.rollback()

    @t_db_retry
    def add_role(self, role_id: str, role_description: str,
                 permissions: int):
        """For multi-tenant transaction DBs, where users have certain roles,
        add a new role in the database.
        
        TransactionDBException will be thrown if the role already exists."""
        try:
            role = self.session.query(Role).filter_by(role_id=role_id).first()
            if role:
                raise TransactionDBException(("The role already exists"))

            role = Role()
            role.role_id = role_id
            role.description = role_description
            role.permissions = permissions
            self.session.add(role)
            self.session.commit()
        finally:
            self.session.rollback()

    def __pre_conditions_user_role(self, user_id, role_id):
        user = self.session.query(User).get(user_id)
        if not user:
            raise TransactionDBException(("The user doesn't exist"))

        role = self.session.query(Role).get(role_id)
        if not role:
            raise TransactionDBException(("The role doesn't exist"))

    @t_db_retry
    def add_user_role(self, user_id: int, role_id: str):
        """
        Assign a role to a user.
        
        Parameters:
        -----------
            user_id: the numeric user ID returned by the database from a user
              which already exists in the Users table.
            role_id: the role identifier (string) which should exist in the
              roles table already.
        
        TransactionDBException will be thrown if the user-role assignment
        already exists.

        Other exceptions will be thrown by the database if the user doesn't 
        exist or the role doesn't exist.
        """
        try:
            user_role = self.session.query(UserRole).filter_by(user_id=user_id)\
                                                    .filter_by(role_id=role_id)\
                                                    .first()
            if user_role:
                raise TransactionDBException(("The role is already assigned"
                                              " to this user."))

            self.__pre_conditions_user_role(user_id, role_id)

            user_role = UserRole()
            user_role.role_id = role_id
            user_role.user_id = user_id
            self.session.add(user_role)
            self.session.commit()
        finally:
            self.session.rollback()

    @t_db_retry
    def revoke_user_role(self, user_id: int, role_id: str):
        """Revoke a role from a user.
        
        Parameters:
        -----------
            user_id: the numeric user ID returned by the database from a user
              which already exists in the Users table.
            role_id: the role identifier (string) which should exist in the
              roles table already.
                     
        TransactionDBException will be thrown if the user-role assignment
        didn't exist in the first place.
        """
        try:
            user_role = self.session.query(UserRole).filter_by(user_id=user_id)\
                                                    .filter_by(role_id=role_id)\
                                                    .first()
            if not user_role:
                raise TransactionDBException(("The role wasn't assigned"
                                              " to this user."))

            self.session.delete(user_role)
            self.session.commit()
        finally:
            self.session.rollback()

    @t_db_retry
    def remove_user(self, user_id: int):
        """Remove a user from the database"""
        try:
            user = self.session.query(User).get(user_id)
            if not user:
                raise TransactionDBException("The user doesn't exist")
            self.session.delete(user)
            self.session.commit()
        finally:
            self.session.rollback()

    def close(self):
        self.session.close()
