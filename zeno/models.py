from sqlalchemy import Column, Integer, String, DateTime, Text, Float, CheckConstraint
from sqlalchemy.orm import DeclarativeBase

from .utils import get_current_time


class Base(DeclarativeBase):
    pass


class Memory(Base):
    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_time = Column(DateTime, nullable=False)
    # relevance: value in [0.0, 1.0], default 1.0. Kept mostly unused for now.
    relevance = Column(Float, nullable=False, default=1.0)

    __table_args__ = (
        CheckConstraint(
            "relevance >= 0.0 AND relevance <= 1.0", name="ck_memory_relevance_range"
        ),
    )


class MessageArchive(Base):
    __tablename__ = "message_archive"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_time = Column(DateTime, nullable=False, default=get_current_time)
