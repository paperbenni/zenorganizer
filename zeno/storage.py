from typing import List
import os

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, desc

from .models import Memory, MessageArchive, Base
from .utils import get_current_time

DATABASE_URL = "sqlite+aiosqlite:///./data/zeno.db"
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Create database tables if they do not exist.

    Ensure the directory for the SQLite database file exists before creating
    tables so that the engine can create the DB file successfully.
    """
    # If using a sqlite URL, extract the file path and ensure its parent dir exists
    if DATABASE_URL.startswith("sqlite") and "///" in DATABASE_URL:
        try:
            db_path = DATABASE_URL.split("///", 1)[1]
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        except Exception:
            # fall back to attempting to create a generic ./data directory
            try:
                os.makedirs("./data", exist_ok=True)
            except Exception:
                pass

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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


async def store_message_archive(content: bytes | str) -> None:
    """Persist a serialized message archive.

    Accepts bytes or str. If bytes are provided, decode to UTF-8 text
    before storing because the DB column is TEXT and archives are JSON.
    """
    if isinstance(content, (bytes, bytearray)):
        content = content.decode()

    archive = MessageArchive(content=content, created_time=get_current_time())
    async with AsyncSessionLocal() as session:
        session.add(archive)
        await session.commit()
