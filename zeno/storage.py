from datetime import datetime
from typing import List

from sqlmodel import Session, create_engine, select

from .models import Memory, MessageArchive
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter


engine = create_engine("sqlite:///test.db", echo=True)


def init_db() -> None:
    """Create tables if they don't exist."""
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)


def get_memories(show_id: bool) -> str:
    memories = []
    output = ""
    with Session(engine) as session:  # type: ignore
        memories.extend(session.exec(select(Memory)).all())  # type: ignore
    for memory in memories:
        if show_id:
            output += f"\n---\nID: {memory.id}"
        output += f"""
{memory.created_time.strftime("%Y-%m-%d %H:%M")}
{memory.content}
---
        """
    return output
    return output

from pydantic_ai.messages import ToolReturnPart

def message_contains_toolreturnpart(messages: List[ModelMessage], index: int) -> bool:
    return any(isinstance(part, ToolReturnPart) for part in messages[index].parts)

def keep_recent_messages(messages: List[ModelMessage], limit: int) -> List[ModelMessage]:
    number_of_messages = len(messages)
    number_of_messages_to_keep = limit
    if number_of_messages <= number_of_messages_to_keep:
        return messages
    if message_contains_toolreturnpart(messages, number_of_messages - number_of_messages_to_keep):
        return messages
    return messages[-number_of_messages_to_keep:]

def get_old_messages(limit: int) -> List[ModelMessage]:
    # Collect messages across archives until we've reached the total `limit` messages.
    messages: list[ModelMessage] = []
    with Session(engine) as session:  # type: ignore
        # iterate newest archives first so we can stop early when limit reached
        # order_by defaults to ascending; use descending to get newest first
        archives = session.exec(  # type: ignore
            select(MessageArchive).order_by(MessageArchive.created_time.desc()).limit(limit)
        ).all()

    for archive in archives:
        messages.extend(ModelMessagesTypeAdapter.validate_json(archive.content))

    # We collected newest-first; return messages in chronological order (oldest->newest)
    messages = list(reversed(messages))
    return keep_recent_messages(messages, limit)


def store_message_archive(content: bytes) -> None:
    archive = MessageArchive(content=content, created_time=datetime.now())
    with Session(engine) as session:  # type: ignore
        session.add(archive)  # type: ignore
        session.commit()  # type: ignore
