from datetime import datetime

from pydantic import BaseModel


class MemoryCreate(BaseModel):
    content: str
    relevance: float | None = 1.0


class MemoryRead(MemoryCreate):
    id: int
    created_time: datetime

    # Pydantic v2: enable creation from attributes (ORM objects)
    model_config = {"from_attributes": True}


class MessageArchiveCreate(BaseModel):
    content: str  # JSON text


class MessageArchiveRead(MessageArchiveCreate):
    id: int
    created_time: datetime

    model_config = {"from_attributes": True}
