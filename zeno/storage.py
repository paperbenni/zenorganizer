from typing import List
import os

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from sqlalchemy import select, desc

from .models import Memory, MessageArchive
from .utils import get_current_time
from .db import AsyncSessionLocal

DATABASE_URL = "sqlite+aiosqlite:///./data/zeno.db"


async def init_db() -> None:
    """Ensure the database directory exists and verify schema presence.

    The application relies on Alembic to create and migrate the schema.
    This helper will ensure the ./data directory exists, then perform a
    lightweight check that the expected tables are present. If the schema
    appears to be missing, it raises a RuntimeError with guidance.
    """
    # Ensure the parent directory for the sqlite DB file exists
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

    # Perform a lightweight schema check by attempting a trivial query
    # against a known table. If the table doesn't exist, the database has
    # not been initialized via Alembic.
    try:
        async with AsyncSessionLocal() as session:
            # Query a known table (Memory) for a single row. If the table
            # is missing this will raise an OperationalError / DatabaseError.
            await session.execute(select(Memory).limit(1))
    except Exception as exc:
        raise RuntimeError(
            "Database schema not found. Initialize the database with Alembic: 'uv run alembic upgrade head'"
        ) from exc

    import logging
    logging.getLogger(__name__).info(
        "storage.init_db(): ensured data dir exists and verified DB schema via a lightweight check."
    )
    return


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
