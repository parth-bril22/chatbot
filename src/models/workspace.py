from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Workspace(Base):
    __tablename__ = "workspace"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String)
