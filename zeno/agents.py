import os
from datetime import datetime
from typing import Callable

import pytz

import dotenv
import logfire
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets import FunctionToolset
from sqlalchemy.sql.functions import now

from . import storage
from .models import Memory
from .storage import get_memories

cleanerprefix = """# RULES
You are an agent tasked with cleaning up the memories of another agentic system.
The memories are all sorted by the time they were created.
The other system is not capable of deleting memories."""

tooldescriptions = {
    "delete": """## Delete Memory
Use this to delete a memory via its ID. Be very careful and conservative when deleting memories. When in doubt, then keep the memory. When in doubt, do not delete.""",
    "store": """## Save Memory
Use this tool to store information about the user. Extract and summarize interesting information from the user message and pass it to this tool.""",
    "update": """## Update Memory
Use this tool to update an existing memory by its ID. Provide the memory ID and the new content to replace the existing memory.""",
}


def get_time_prompt() -> str:
    now = datetime.now(pytz.timezone('Europe/Berlin'))
    return f"""
# INFO
Today is {now.strftime("%Y-%m-%d")}
The current time is {now.strftime("%H:%M:%S")} (European)
"""


def get_memories_prompt() -> str:
    mdmemories = storage.get_memories(True)
    return f"""
# Memories
Here are the last noteworthy memories that you've collected from the user, including the date and time this information was collected.
!! IMPORTANT!
Think carefully about your responses and take the user's preferences into account!
Also consider the date and time that a memory was shared in order to respond with the most up to date information.

Here are the Memories in Markdown format:

{mdmemories}

**end of memories**"""

import dotenv
dotenv.load_dotenv()

def get_openai_model() -> OpenAIModel:
    openai_model = OpenAIModel(
            os.environ["MODEL_NAME"],
            provider=OpenAIProvider(
                api_key=os.environ["OPENAI_API_KEY"],
                base_url=os.environ["OPENAI_BASE_URL"],
            ),
        )
    return openai_model


async def delete_memory(ctx: RunContext, id: int):
    """
    Delete a memory

    Args:
        id: The id of the memory
    """
    from sqlmodel import Session

    from .storage import engine

    with Session(engine) as session:  # type: ignore
        memory = session.get(Memory, id)  # type: ignore
        if memory:
            session.delete(memory)  # type: ignore
            session.commit()  # type: ignore


async def store_memory(ctx: RunContext, content: str):
    """
    Store a memory

    Args:
        content: The content of the memory
    """
    from sqlmodel import Session

    from .models import Memory
    from .storage import engine

    memory = Memory(content=content, created_time=datetime.now(pytz.timezone('Europe/Berlin')))
    with Session(engine) as session:  # type: ignore
        session.add(memory)  # type: ignore
        session.commit()  # type: ignore


async def update_memory(ctx: RunContext, id: int, content: str):
    """
    Update a memory's content by ID

    Args:
        id: The id of the memory to update
        content: The new content for the memory
    """
    from sqlmodel import Session

    from .models import Memory
    from .storage import engine

    with Session(engine) as session:  # type: ignore
        memory = session.get(Memory, id)  # type: ignore
        if memory:
            memory.content = content  # type: ignore
            memory.created_time = datetime.now(pytz.timezone('Europe/Berlin'))  # update timestamp to now
            session.add(memory)  # type: ignore
            session.commit()  # type: ignore

def build_chat_agent() -> Agent:
    def get_chat_instructions() -> str:
        return f"""# RULES
When a user sends a new message, decide if the user provided any noteworthy information that should be stored in memory. If so, call the Save Memory tool to store this information in memory.
Reminders should always go in memory, along with a time.
Anything containing updated information about a memory should be a memory.
If you notice anything in the conversation history which should be a memory, then also store that in a memory. Notify the user of what you have stored.
The chat history is reset frequently, so anything long lived should be a memory.
You can also mark memories which should be forgotten by inserting a memory stating that specific information is no longer important. A cleaning agent will then occasionally remove it.

# Tools
{tooldescriptions['store']}

{get_memories_prompt()}
{get_time_prompt()}
    """

    chat_agent = Agent(
        model=get_openai_model(),
        instructions=get_chat_instructions(),
        toolsets=[FunctionToolset(tools=[store_memory])],
    )

    return chat_agent


def build_splitter_agent() -> Agent:
    splitter_agent = Agent(
        model=get_openai_model(),
        toolsets=[FunctionToolset(tools=[delete_memory, store_memory, update_memory])],
        instructions=f"""{cleanerprefix}

# Tasks
## Split overaggregated memories
Memories can only be deleted in their entirety. If a memory states that part of an aggregated memory should be forgotten, then split that part into a separate memory.
If a memory contains information about something no longer relevant, like a reminder sent in the far past, then split that into a separate memory, and remove that information from the original memory.
Time sensitive information should always be kept separate from information that is not time sensitive.
Do not include logs about what you changed inside the memory content.

# Tools

{tooldescriptions['delete']}
{tooldescriptions['store']}
{tooldescriptions['update']}

{get_memories_prompt()}
{get_time_prompt()}


""",
    )

    return splitter_agent


def build_aggregator_agent() -> Agent:
    aggregator_agent = Agent(
        model=get_openai_model(),
        toolsets=[FunctionToolset(tools=[store_memory, delete_memory])],
        instructions=f"""{cleanerprefix}

##Aggregate memories
If there are multiple memories which only make sense when put together, then delete them and add a new memory with the information from all of them.
For example a memory containing a list of things, and another memory adding things to that list should be aggregated into a single memory containing the entire list.
Examples of this include memories with missing information and another memory providing that information.
Make sure memories stay with a single responsibility, similar to programming. It is okay not to aggregate anything if that is what seems best.
Make sure that if the original memories were time sensitive to include the date the memories pertain to in the content.
Keep in mind aggregating a memory changes its creation date. If a memory is time sensitive, include the full date it pertains to in the memory content.
IMPORTANT: Keep information which should be deleted separately separate. Examples of this include reminders about information, and the information itself.
If you see instances of this, split the memories. Make sure to include the date.

# Tools
{tooldescriptions['store']}
{tooldescriptions['delete']}

{get_memories_prompt()}
{get_time_prompt()}
""",
    )

    return aggregator_agent


def build_deduplicator_agent() -> Agent:
    dedup_agent = Agent(
        model=get_openai_model(),
        toolsets=[FunctionToolset(tools=[delete_memory])],
        instructions=f"""{cleanerprefix}

##Deduplicate memories
If there are duplicate memories, memorizing the same thing, remove some of them and keep the last one.

##Remove contractictions
If there are memories which contradict each other, then assume the newest one is correct and remove the older contradicting ones.

# Tools
{tooldescriptions['delete']}

{get_memories_prompt()}
{get_time_prompt()}
""",
    )

    return dedup_agent


def build_garbage_collector_agent() -> Agent:

    garbage_collector_agent = Agent(
        model=get_openai_model(),
        toolsets=[FunctionToolset(tools=[delete_memory])],
        instructions=f"""{cleanerprefix}

# Tasks
##Remove old reminders and memories to be deleted
If there is a one time reminder, along with another memory claiming that exact reminder has already been sent, you can remove both the reminder and the memory noting that the reminder has been sent. If there are memories which note that another memory should be forgotten, remove both the memory to be forgotten and the note that it should be forgotten. If there is information which is only useful on a specific day, and that day is in the past, then remove that information. If the information could be useful in the future, keep it.
If a memory itself states it should be deleted, or if the memory and its deletion notice are in the same memory, also delete it.
BE SURE NOT TO REMOVE RECURRING REMINDERS.

# Tools
{tooldescriptions['delete']}

{get_memories_prompt()}
{get_time_prompt()}
""",
    )

    return garbage_collector_agent


def build_reminder_agent() -> Agent:
    """
    Agent that checks memories and sends telegram reminders when time-critical
    memories are due. Activated periodically (every 15 minutes).
    """

    async def send_reminder(ctx: RunContext, message: str):
        """
        Send a seminder message

        Args:
            message: The message to send
        """
        # send a telegram message to the hardcoded user (same as user check)
        import os

        # We can't easily access the live Application here; instead, use bot token and
        # python-telegram-bot's simple API to send a message.
        from telegram import Bot

        from .telegram_bot import Application

        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            return
        bot = Bot(token=token)
        # hardcoded chat id (same as in telegram bot user check)
        chat_id = 1172527123
        await bot.send_message(chat_id=chat_id, text=message)

        # Also save this reminder as a normal assistant message in the message archive
        # so it will be included in future `get_old_messages` calls. Construct a
        # ModelResponse containing a single TextPart and serialize it using the
        # same adapter used by `store_message_archive`.
        try:
            from pydantic_ai.messages import (
                ModelMessagesTypeAdapter,
                ModelResponse,
                RequestUsage,
                TextPart,
            )

            from .storage import store_message_archive

            response = ModelResponse(
                parts=[TextPart(content=message)],
                usage=RequestUsage(),
                model_name=ctx.model.model_name,
                timestamp=datetime.now(pytz.timezone('Europe/Berlin')),
            )
            # serialize to bytes the same way archives are stored
            json_bytes = ModelMessagesTypeAdapter.dump_json([response])
            store_message_archive(json_bytes)
        except Exception:
            # Don't let failures to persist the archive stop the reminder sending
            logfire.info("failed to store reminder message")

    reminder_agent = Agent(
        model=get_openai_model(),
        toolsets=[FunctionToolset(tools=[send_reminder, store_memory])],
        instructions=f"""# RULES
You are an agent tasked with sending a user reminders. You are given a list of memories and the current time. If a memory looks like the user should be reminded of, send the user a reminder with. Also record a new memory marking that the reminder has been sent, so that you will not remind the user more than they requested.
Pay attention to when a memory is relevant. You know the current date and time, only send reminders for memories which are currently relevant and time sensitive.
For example if a memory says to remind the user of something daily, send a reminder and also record a memory saying that on the current day, the reminder has already been sent.
If the reminder is a one-time thing, then send the reminder and save a memory saying the reminder can be deleted. Make sure it is clear which reminder the new memory is referring to, include the entire reminder memory if necessary

Do not send any reminders or do anything if no reminders are relevant
You are only activated every 15 minutes, with some unreliability, so anything 20 minutes into the future or into the past is definitely relevant. Relevance might span even further into the future or past if the reminder contains information about its length of relevance


# Tools
## Save Memory
Use this tool to store information about the user and reminders. Use this to store information about reminders you already did. NEVER mark a reminder as sent before you have not used the Send Reminder tool to send the reminder. If the send tool fails, retry up to 20 times, and if it still fails, then do not mark reminders as sent

## Send Reminder
Use this tool to send a reminder. Be very liberal with this. If something looks like it could be relevant, it probably is.

{get_memories_prompt()}
{get_time_prompt()}
""",
    )

    return reminder_agent
