from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase

from .utils import get_current_time


class Base(DeclarativeBase):
    pass


class Memory(Base):
    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_time = Column(DateTime, nullable=False)


class MessageArchive(Base):
    __tablename__ = "message_archive"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_time = Column(DateTime, nullable=False, default=get_current_time)
