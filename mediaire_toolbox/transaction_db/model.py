from sqlalchemy import Column, Integer, String, Sequence, DateTime, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
import datetime

from mediaire_toolbox.task_state import TaskState

Base = declarative_base()


class Transaction(Base):

    __tablename__ = 'transactions'

    """A general transaction, this could be used by any other pipeline"""
    transaction_id = Column(Integer, Sequence(
        'transaction_id'), primary_key=True)
    study_id = Column(String(256))
    patient_id = Column(String(128))
    name = Column(String(64))
    birth_date = Column(Date())
    start_date = Column(DateTime(), default=datetime.datetime.utcnow)
    end_date = Column(DateTime())
    task_state = Column(Enum(TaskState))
    processing_state = Column(String(64))
    last_message = Column(String)
    error = Column(String())

    def __repr__(self):
        return "<Transaction(transaction_id='%s', patient_id='%s', start_date='%s')>" % (
            self.transaction_id, self.patient_id, self.start_date)


def create_all(engine):
    Base.metadata.create_all(bind=engine)
