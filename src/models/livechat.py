from sqlalchemy import Column, Integer, String,DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Union

Base  = declarative_base()

class Agents(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key = True)
    name = Column(String)
    created_at = Column(DateTime)
    isavailable = Column(Boolean)
    user_id = Column(Integer)

class Account(Base):
    __tablename__ = 'accounts'
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer)