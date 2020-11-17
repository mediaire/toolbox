import datetime

from sqlalchemy import Column, Integer, String, Sequence, DateTime, Date, Enum, \
                        ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import deferred
from passlib.apps import custom_app_context as pwd_context

from mediaire_toolbox.task_state import TaskState
from mediaire_toolbox import constants

Base = declarative_base()


# TODO Change to a dataclass when moving to Python 3.7
class Transaction(Base):

    __tablename__ = 'transactions'

    """A general transaction, this could be used by any pipeline"""
    transaction_id = Column(Integer, Sequence(
        'transaction_id'), primary_key=True)

    # study info
    study_id = Column(String(255))
    patient_id = Column(String(255))
    name = Column(String(255))
    birth_date = Column(Date())
    # TODO convert this to date
    study_date = Column(String())
    patient_consent = Column(Integer, default=0)
    # indexed from DICOM header, for free text search
    institution = Column(String())

    # transaction dates
    start_date = Column(DateTime())
    end_date = Column(DateTime())
    # time when the transaction was created
    creation_date = Column(DateTime())

    # transaction types
    version = Column(String(31))
    analysis_type = Column(String(31))
    qa_score = Column(String(31))
    product_id = Column(Integer, default=1)

    # transaction states
    task_state = Column(Enum(TaskState))
    processing_state = Column(String(255))
    task_progress = Column(Integer, default=0)
    task_skipped = Column(Integer, default=0)
    task_cancelled = Column(Integer, default=0)
    archived = Column(Integer, default=0)

    error = Column(String())
    # new platform status: unseen / reviewed / sent_to_pacs
    status = Column(String())
    # indexed from Task object, for free text search
    sequences = Column(String())
    # indexed from DICOM header, for sorting
    last_message = deferred(Column(String))

    # misc
    data_uploaded = Column(DateTime())
    billable = Column(String())

    def _datetime_to_str(self, dt):
        return (
            dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None
        )

    def _str_to_datetime(self, str_):
        return (
            datetime.datetime.strptime(str_, "%Y-%m-%d %H:%M:%S")
            if str_ else None
        )

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'study_id': self.study_id,
            'patient_id': self.patient_id,
            'name': self.name,
            'birth_date': self.birth_date.strftime("%d/%m/%Y")
            if self.birth_date else None,
            'study_date': self.study_date,
            'patient_consent': self.patient_consent,
            'institution': self.institution,

            'start_date': self._datetime_to_str(self.start_date),
            'end_date': self._datetime_to_str(self.end_date),
            'creation_date': self._datetime_to_str(self.creation_date),

            'version': self.version,
            'analysis_type': self.analysis_type,
            'qa_score': self.qa_score,
            'product_id': self.product_id,

            'task_state': self.task_state.name if self.task_state else None,
            'processing_state': self.processing_state,
            'task_progress': self.task_progress,
            'task_skipped': self.task_skipped,
            'task_cancelled': self.task_cancelled,
            'archived': self.archived,
            'error': self.error,
            'status': self.status,
            'sequences': self.sequences,
            'last_message': self.last_message,

            'data_uploaded': self._datetime_to_str(self.data_uploaded),
            'billable': self.billable,
        }

    def read_dict(self, d: dict):
        """Read transaction from dictionary"""
        self.transaction_id = d.get('transaction_id')

        self.study_id = d.get('study_id')
        self.patient_id = d.get('patient_id')
        self.name = d.get('name')
        birth_date = d.get('birth_date')
        self.birth_date = datetime.datetime.strptime(
            birth_date, "%d/%m/%Y") if birth_date else None
        self.study_date = d.get('study_date')
        self.patient_consent = d.get('patient_consent')
        self.institution = d.get('institution')

        self.start_date = self._str_to_datetime(d.get('start_date'))
        self.end_date = self._str_to_datetime(d.get('end_date'))
        self.creation_date = self._str_to_datetime(d.get('creation_date'))

        self.version = d.get("version")
        self.analysis_type = d.get("analysis_type")
        self.qa_score = d.get("qa_score")
        self.product_id = d.get('product_id')

        self.task_state = TaskState[
            d.get('task_state')] if d.get('task_state') else None
        self.processing_state = d.get('processing_state')
        self.task_progress = d.get('task_progress')
        self.task_skipped = d.get('task_skipped')
        self.task_cancelled = d.get('task_cancelled')
        self.archived = d.get('archived')
        self.error = d.get('error')
        self.status = d.get('status')
        self.sequences = d.get('sequences')
        self.last_message = d.get('last_message')

        self.data_uploaded = self._str_to_datetime(d.get('data_uploaded'))
        self.billable = d.get('billable')
        return self

    def __repr__(self):
        return "<Transaction(transaction_id='%s', patient_id='%s', start_date='%s')>" % (
            self.transaction_id, self.patient_id, self.start_date)


class User(Base):

    """for multi-tenant pipelines, users might be required"""
    __tablename__ = 'users'

    id = Column(Integer, Sequence('id'), primary_key=True)
    name = Column(String(255), unique=True)
    hashed_password = Column(String(128))
    added = Column(DateTime(), default=datetime.datetime.utcnow)

    @staticmethod
    def password_hash(password):
        return pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.hashed_password)

    def to_dict(self):
        return { 'id': self.id,
                 'name': self.name,
                 'hashed_password': self.hashed_password,
                 'added': self.added.strftime("%Y-%m-%d %H:%M:%S") }

    def read_dict(self, d: dict):
        self.id = d.get('id')
        self.name = d.get('name')
        self.hashed_password = d.get('hashed_password')
        added = d.get('added')
        self.added = datetime.datetime.strptime(
            added, "%Y-%m-%d %H:%M:%S") if added else None
        return self


class UserTransaction(Base):

    """for multi-tenant pipelines, transactions might be associated with users"""
    __tablename__ = 'users_transactions'

    user_id = Column(Integer, ForeignKey('users.id'),
                     primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions.transaction_id'),
                            primary_key=True)

    def to_dict(self):
        return { 'user_id': self.user_id,
                 'transaction_id': self.transaction_id }

    def read_dict(self, d: dict):
        self.user_id = d.get('user_id')
        self.transaction_id = d.get('transaction_id')
        return self


class UserRole(Base):

    """for multi-tenant pipelines, users might have different roles in the
    associated platform"""
    __tablename__ = 'users_roles'

    user_id = Column(Integer, ForeignKey('users.id'),
                     primary_key=True)
    role_id = Column(String(64), ForeignKey('roles.role_id'),
                     primary_key=True)

    def to_dict(self):
        return { 'user_id': self.user_id,
                 'role_id': self.role_id }

    def read_dict(self, d: dict):
        self.user_id = d.get('user_id')
        self.role_id = d.get('role_id')
        return self


class UserPreferences(Base):
    
    """for multi-tenant pipelines, users might have different preferences
    like the language they want their reports in"""
    __tablename__ = 'users_preferences'

    user_id = Column(Integer, ForeignKey('users.id'),
                     primary_key=True)
    report_language = Column(String(255))

    def to_dict(self):
        return { 'user_id': self.user_id,
                 'report_language': self.report_language }

    def read_dict(self, d: dict):
        self.user_id = d.get('user_id')
        self.report_language = d.get('report_language')
        return self
    

class Role(Base):

    """for multi-tenant pipelines, users might have different roles in the
    associated platform"""
    __tablename__ = 'roles'

    role_id = Column(String(64),
                     primary_key=True)
    description = Column(String)
    # encoded permissions for this role, 1 bit for each
    permissions = Column(Integer)

    def to_dict(self):
        return {'role_id': self.user_id}

    def read_dict(self, d: dict):
        self.role_id = d.get('role_id')
        return self


class SchemaVersion(Base):

    __tablename__ = 'schema_version'

    schema = Column(String(255), primary_key=True,
                    default=constants.TRANSACTIONS_DB_SCHEMA_NAME)
    schema_version = Column(Integer,
                            default=constants.TRANSACTIONS_DB_SCHEMA_VERSION)


def create_all(engine):
    Base.metadata.create_all(bind=engine)
