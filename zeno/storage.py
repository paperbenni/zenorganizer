from typing import List

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, desc, select

from .models import Memory, MessageArchive
from .utils import get_current_time

DATABASE_URL = "sqlite+aiosqlite:///./data/zeno.db"
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create database tables if they do not exist."""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_memories(show_id: bool) -> str:
    """Return stored memories as plain text."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Memory))
        memories = result.scalars().all()

    parts: list[str] = []
    for memory in memories:
        if show_id:
            parts.append(f"\n---\nID: {memory.id}")
        parts.append(
            f"{memory.created_time.strftime('%Y-%m-%d %H:%M')}\n{memory.content}\n---"
        )
    return "\n".join(parts)


async def get_old_messages(limit: int) -> List[ModelMessage]:
    """Return the most recent message archives as a flat list of ModelMessage.

    Archives are read newest-first from the DB; we reverse them to produce
    chronological order for consumption by the chat agent.
    """
    messages: list[ModelMessage] = []
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MessageArchive)
            .order_by(desc(MessageArchive.created_time))
            .limit(limit)
        )
        archives = result.scalars().all()

    archivecounter = 0
    for archive in reversed(archives):
        msgs = ModelMessagesTypeAdapter.validate_json(archive.content)
        messages.extend(msgs)
        archivecounter += 1
        if archivecounter >= limit:
            break

    return list(messages)


async def store_message_archive(content: bytes) -> None:
    """Persist a serialized message archive."""
    archive = MessageArchive(content=content, created_time=get_current_time())
    async with AsyncSessionLocal() as session:
        session.add(archive)
        await session.commit()
