import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AssessmentEdit(Base):

    __tablename__ = 'edits'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer)
    edit = Column(String)
    edit_date = Column(DateTime(), default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'edit': self.edit,
            'edit_date': self.edit_date.strftime("%Y-%m-%d %H:%M:%S")
        }


def create_all(engine):
    Base.metadata.create_all(bind=engine)
