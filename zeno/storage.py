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

def get_old_messages(limit: int) -> List[ModelMessage]:
    messages: list[ModelMessage] = []
    with Session(engine) as session:  # type: ignore
        archives = session.exec(
            select(MessageArchive)
            .order_by(MessageArchive.created_time.desc())
            .limit(limit)
        ).all()

        for archive in reversed(archives):
            msgs = ModelMessagesTypeAdapter.validate_json(archive.content)
            messages.extend(msgs)
            if len(messages) >= limit:
                break

    # We collected newest-first; return messages in chronological order (oldest->newest)
    messages = list(messages)
    return messages


def store_message_archive(content: bytes) -> None:
    archive = MessageArchive(content=content, created_time=datetime.now())
    with Session(engine) as session:  # type: ignore
        session.add(archive)  # type: ignore
        session.commit()  # type: ignore
