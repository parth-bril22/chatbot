from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base  = declarative_base()

class Slack(Base):
    __tablename__ = 'slack'
    id = Column(Integer, primary_key = True)
    channel_name = Column(String)
    channel_id = Column(String)
    workspace_name = Column(String)
    bot_token = Column(String)