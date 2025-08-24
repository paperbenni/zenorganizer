from datetime import datetime
from typing import Callable

import dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets import FunctionToolset
import os

from . import storage
from .models import Memory
from .storage import get_memories


def getModel() -> OpenAIModel:
    return OpenAIModel(
        os.environ["MODEL_NAME"],
        provider=OpenAIProvider(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"],
        ),
    )


cleanerprefix = """# RULES
You are an agent tasked with cleaning up the memories of another agentic system.
The memories are all sorted by the time they were created.
The other system is not capable of deleting memories."""

tooldescriptions = {
    "delete": """## Delete Memory
Use this to delete a memory via its ID. Be very careful and conservative when deleting memories. When in doubt, then keep the memory. When in doubt, do not delete.""",
    "store": """## Save Memory
Use this tool to store information about the user. Extract and summarize interesting information from the user message and pass it to this tool.""",
}


def infoprompt() -> str:
    return f"""# INFO
Today is { datetime.now().strftime("%Y-%m-%d") }"""


def get_model() -> OpenAIModel:
    dotenv.load_dotenv()
    return OpenAIModel(
        "github_copilot/gpt-5-mini",
        provider=OpenAIProvider(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url="https://litellm.paperbenni.xyz/v1",
        ),
    )


async def delete_memory(ctx: RunContext, id: int):
    """
    Delete a memory

    Args:
        id: The id of the memory
    """
    from .storage import engine
    from sqlmodel import Session

    with Session(engine) as session:
        memory = session.get(Memory, id)
        if memory:
            session.delete(memory)
            session.commit()


async def store_memory(ctx: RunContext, content: str):
    """
    Store a memory

    Args:
        content: The content of the memory
    """
    from sqlmodel import Session
    from .models import Memory

    memory = Memory(content=content, created_time=datetime.now())
    with Session(storage.engine) as session:
        session.add(memory)
        session.commit()


def build_chat_agent() -> Agent:
    chatagent = Agent(
        model=get_model(),
        toolsets=[FunctionToolset(tools=[store_memory])],
        system_prompt=f"""# RULES
When a user sends a new message, decide if the user provided any noteworthy information that should be stored in memory. If so, call the Save Memory tool to store this information in memory.
Reminders should always go in memory, along with a time.
Anything containing updated information about a memory should be a memory.
If you notice anything in the conversation history which should be a memory, then also store that in a memory. Notify the user of what you have stored.
The chat history is reset frequently, so anything long lived should be a memory.
You can also mark memories which should be forgotten by inserting a memory stating that specific information is no longer important. A cleaning agent will then occasionally remove it.

# Tools
## Save Memory
Use this tool to store information about the user. Extract and summarize interesting information from the user message and pass it to this tool.

# INFO
Today is { datetime.now().strftime("%Y-%m-%d") }
        """,
    )

    @chatagent.system_prompt
    def get_memories_prompt(ctx: RunContext) -> str:
        return f"""# Memories
Here are the last noteworthy memories that you've collected from the user, including the date and time this information was collected.
!! IMPORTANT!
Think carefully about your responses and take the user's preferences into account!
Also consider the date and time that a memory was shared in order to respond with the most up to date information.

Here are the Memories in Markdown format:

{storage.get_memories(True)}

**end of memories**"""

    return chatagent


def build_deduplicator_agent() -> Agent:
    dedup_agent = Agent(
        model=getModel(),
        toolsets=[FunctionToolset(tools=[delete_memory])],
        system_prompt=f"""{cleanerprefix}

##Deduplicate memories
If there are duplicate memories, memorizing the same thing, remove some of them and keep the last one.

##Remove contractictions
If there are memories which contradict each other, then assume the newest one is correct and remove the older contradicting ones.

# Tools
{tooldescriptions['delete']}

# INFO
Today is { datetime.now().strftime("%Y-%m-%d") }""",
    )

    @dedup_agent.system_prompt
    def get_memories_prompt(ctx: RunContext) -> str:
        return f"""# Memories
Here are the last noteworthy memories that you've collected from the user, including the date and time this information was collected.

Here are the Memories in Markdown format:

{storage.get_memories(True)}

**end of memories**"""

    return dedup_agent


def build_garbage_collector_agent() -> Agent:

    garbage_collector_agent = Agent(
        model=getModel(),
        toolsets=[FunctionToolset(tools=[delete_memory])],
        system_prompt=f"""{cleanerprefix}

# Tasks
##Remove old reminders and memories to be deleted
If there is a one time reminder, along with another memory claiming that exact reminder has already been sent, you can remove both the reminder and the memory noting that the reminder has been sent. If there are memories which note that another memory should be forgotten, remove both the memory to be forgotten and the note that it should be forgotten. If there is information which is only useful on a specific day, and that day is in the past, then remove that information. If the information could be useful in the future, keep it.
If a memory itself states it should be deleted, or if the memory and its deletion notice are in the same memory, also delete it.
BE SURE NOT TO REMOVE RECURRING REMINDERS.

# Tools
{tooldescriptions['delete']}

# INFO
Today is { datetime.now().strftime("%Y-%m-%d") }
        """,
    )

    @garbage_collector_agent.system_prompt
    def get_memories_prompt(ctx: RunContext) -> str:
        return f"""# Memories
Here are the last noteworthy memories that you've collected from the user, including the date and time this information was collected.

Here are the Memories in Markdown format:

{get_memories(True)}
**end of memories**"""

    return garbage_collector_agent
