import datetime

from sqlalchemy import Column, Integer, String, Sequence, DateTime, Date, Enum, \
                        ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from passlib.apps import custom_app_context as pwd_context

from mediaire_toolbox.task_state import TaskState
from mediaire_toolbox import constants

Base = declarative_base()


class Transaction(Base):

    __tablename__ = 'transactions'

    """A general transaction, this could be used by any pipeline"""
    transaction_id = Column(Integer, Sequence(
        'transaction_id'), primary_key=True)
    study_id = Column(String(255))
    patient_id = Column(String(255))
    name = Column(String(255))
    birth_date = Column(Date())
    start_date = Column(DateTime(), default=datetime.datetime.utcnow)
    end_date = Column(DateTime())
    task_state = Column(Enum(TaskState))
    processing_state = Column(String(255))
    last_message = Column(String)
    error = Column(String())
    # new platform status: unseen / reviewed / sent_to_pacs 
    status = Column(String())
    # indexed from DICOM header, for free text search
    institution = Column(String())
    # indexed from Task object, for free text search
    sequences = Column(String())
    # indexed from DICOM header, for sorting
    study_date = Column(String())
    task_progress = Column(Integer, default=0)
    task_skipped = Column(Integer, default=0)
    task_cancelled = Column(Integer, default=0)
    archived = Column(Integer, default=0)
    patient_consent = Column(Integer, default=0)
    product_id = Column(Integer, default=1)

    def to_dict(self):
        return { 'transaction_id': self.transaction_id,
                 'study_id': self.study_id,
                 'patient_id': self.patient_id,
                 'name': self.name,
                 'birth_date': self.birth_date.strftime("%d/%m/%Y") 
                    if self.birth_date else None,
                 'start_date': self.start_date.strftime("%Y-%m-%d %H:%M:%S") 
                    if self.start_date else None,
                 'end_date': self.end_date.strftime("%Y-%m-%d %H:%M:%S") 
                    if self.end_date else None,
                 'task_state': self.task_state.name if self.task_state else None,
                 'processing_state': self.processing_state,
                 'study_date': self.study_date,
                 'last_message': self.last_message,
                 'task_progress': self.task_progress,
                 'error': self.error,
                 'task_skipped': self.task_skipped,
                 'task_cancelled': self.task_cancelled,
                 'status': self.status,
                 'institution': self.institution,
                 'sequences': self.sequences,
                 'archived': self.archived,
                 'patient_consent': self.patient_consent,
                 'product_id': self.product_id
                }

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


class SchemaVersion(Base):
    
    __tablename__ = 'schema_version'
    
    schema = Column(String(255), primary_key=True,
                    default=constants.TRANSACTIONS_DB_SCHEMA_NAME)
    schema_version = Column(Integer,
                            default=constants.TRANSACTIONS_DB_SCHEMA_VERSION)

    
def create_all(engine):
    Base.metadata.create_all(bind=engine)
