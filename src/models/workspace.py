from xmlrpc.client import Boolean
from psycopg2 import Date
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from .users import User, Base 

# Base  = declarative_base()

class Worksapce(Base):
    __tablename__ = 'workspace'
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey("user_info.id", ondelete = "CASCADE"))
    name = Column(String)
    deleted = Column(Boolean)