from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base  = declarative_base()

class Variable(Base):
    __tablename__ = 'variable'
    id = Column(Integer, primary_key = True)
    name = Column(String)
    type = Column(String)
    value = Column(String)
    user_id = Column(Integer)