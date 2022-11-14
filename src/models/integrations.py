from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Slack(Base):
    __tablename__ = "slack"
    id = Column(Integer, primary_key=True)
    channel_name = Column(String)
    channel_id = Column(String)
    workspace_name = Column(String)
    bot_token = Column(String)
    user_id = Column(Integer)


class SendEmail(Base):
    __tablename__ = "send_email"
    id = Column(Integer, primary_key=True)
    from_email = Column(String)
    secret = Column(String)
    user_id = Column(Integer)
