from datetime import datetime

import pytz
from sqlmodel import Field, SQLModel


class Memory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: str
    created_time: datetime


class MessageArchive(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: bytes
    created_time: datetime = Field(default_factory=lambda: datetime.now(pytz.timezone('Europe/Berlin')))
