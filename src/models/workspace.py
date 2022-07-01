from xmlrpc.client import Boolean
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base  = declarative_base()
class Workspace(Base):
    __tablename__ = 'workspace'
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey("user_info.id", ondelete = "CASCADE"))
    name = Column(String)
    deleted = Column(Boolean)