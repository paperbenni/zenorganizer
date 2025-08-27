"""Tool functions exposed to AI agents.

Each function is an async callable intended for use by AI agents. Docstrings
contain only the minimal contract information agents need: a short
description, parameter names and types, and the return type.
"""

import os

from pydantic_ai import RunContext
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelResponse, TextPart
from pydantic_ai.usage import RequestUsage
from telegram import Bot

from .config import TELEGRAM_CHAT_ID
from .models import Memory
from .storage import AsyncSessionLocal, store_message_archive
from .utils import get_current_time, split_and_send

async def delete_memory(ctx: RunContext, id: int) -> None:
    """Delete Memory.

    Delete the memory with the given id.

    Parameters
    - id: int

    Returns
    - None
    """
    async with AsyncSessionLocal() as session:  # type: ignore
        memory = await session.get(Memory, id)
        if memory:
            await session.delete(memory)
            await session.commit()


async def store_memory(ctx: RunContext, content: str) -> None:
    """Save Memory.

    Store a new memory with the provided content.

    Parameters
    - content: str

    Returns
    - int: id of created memory
    """
    memory = Memory(content=content, created_time=get_current_time())
    async with AsyncSessionLocal() as session:  # type: ignore
        session.add(memory)
        await session.commit()
        # no return value needed
        return None


async def update_memory(ctx: RunContext, id: int, content: str) -> None:
    """Update Memory.

    Replace the content of an existing memory.

    Parameters
    - id: int
    - content: str

    Returns
    - Optional[int]: id if updated, else None
    """
    async with AsyncSessionLocal() as session:  # type: ignore
        memory = await session.get(Memory, id)
        if memory:
            memory.content = content
            memory.created_time = get_current_time()
            session.add(memory)
            await session.commit()
            # no return value needed
        return None


async def send_reminder(ctx: RunContext, message: str) -> None:
    """Send Reminder.

    Send `message` to the configured Telegram chat and record it in the message archive.

    Parameters
    - message: str

    Returns
    - None
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return

    bot = Bot(token=token)
    # Use split_and_send to handle messages longer than Telegram's limit
    await split_and_send(send=bot.send_message, text=message, chat_id=TELEGRAM_CHAT_ID)

    response = ModelResponse(
        parts=[TextPart(content=message)],
        usage=RequestUsage(),
        model_name=getattr(ctx, "model", None)
        and getattr(ctx.model, "model_name", "unknown"),
        timestamp=get_current_time(),
    )
    json_bytes = ModelMessagesTypeAdapter.dump_json([response])
    await store_message_archive(json_bytes)
