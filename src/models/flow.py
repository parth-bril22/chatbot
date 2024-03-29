from sqlalchemy import JSON, Column, DateTime, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Flow(Base):
    __tablename__ = "flow"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    name = Column(String)
    diagram = Column(JSON)
    publish_token = Column(String)
    chats = Column(Integer)
    finished = Column(Integer)
    isEnable = Column(Boolean)
    status = Column(String)
    workspace_id = Column(Integer)
    workspace_name = Column(String)


class Chat(Base):
    __tablename__ = "chat"
    visitor_id = Column(Integer, primary_key=True)
    flow_id = Column(Integer)
    visited_at = Column(DateTime)
    updated_at = Column(DateTime)
    chat = Column(JSON)
    visitor_ip = Column(String)
    visitor_token = Column(String)


class EmbedScript(Base):
    __tablename__ = "embedscripts"
    id = Column(Integer, primary_key=True)
    file_name = Column(String)
    created_at = Column(DateTime)
    file_url = Column(String)
