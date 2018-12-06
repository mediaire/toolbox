import datetime

from sqlalchemy import Column, Integer, String, Sequence, DateTime, Date, Enum
from sqlalchemy.ext.declarative import declarative_base

from mediaire_toolbox.task_state import TaskState

Base = declarative_base()

"""Metadata that indicates the version of the schema in the database.
We use our own schema migration routines. Don't forget to change the version
number here if you add more fields to the Transaction object, and implement
the migration SQL queries in transaction_db.migrate"""
SCHEMA_NAME = "TRANSACTION"
SCHEMA_VERSION = 2


class Transaction(Base):

    __tablename__ = 'transactions'

    """A general transaction, this could be used by any other pipeline"""
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
    task_progress = Column(Integer, default=0)

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
                 'last_message': self.last_message,
                 'task_progress': self.task_progress,
                 'error': self.error }

    def __repr__(self):
        return "<Transaction(transaction_id='%s', patient_id='%s', start_date='%s')>" % (
            self.transaction_id, self.patient_id, self.start_date)


class SchemaVersion(Base):
    
    __tablename__ = 'schema_version'
    
    schema = Column(String(255), primary_key=True, default=SCHEMA_NAME)
    schema_version = Column(Integer, default=SCHEMA_VERSION)

    
def create_all(engine):
    Base.metadata.create_all(bind=engine)
