from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, BOOLEAN
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "user_info"
    id = Column(Integer, primary_key=True)
    email = Column(String)
    password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(DateTime)
    token = Column(String)
    pwd_token = relationship(
        "Password_tokens",
        back_populates="user",
        uselist=False,
        cascade="all, delete",
        passive_deletes=True,
    )


class Password_tokens(Base):
    __tablename__ = "password_tokens"
    id = Column(
        Integer, ForeignKey("user_info.id", ondelete="CASCADE"), primary_key=True
    )
    uuid = Column(String)
    time = Column(DateTime)
    used = Column(BOOLEAN)
    user = relationship("User", back_populates="pwd_token")
