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


def infoprompt() -> str:
    return f"""# INFO
Today is { datetime.now().strftime("%Y-%m-%d") }"""


def attach_memories_prompt(agent: Agent) -> None:
    @agent.system_prompt
    def _memories(ctx: RunContext) -> str:
        return f"""# Memories
Here are the last noteworthy memories that you've collected from the user, including the date and time this information was collected.
!! IMPORTANT!
Think carefully about your responses and take the user's preferences into account!
Also consider the date and time that a memory was shared in order to respond with the most up to date information.

Here are the Memories in Markdown format:

{storage.get_memories(True)}

**end of memories**"""


def get_model() -> OpenAIModel:
    return OpenAIModel(
        os.environ["MODEL_NAME"],
        provider=OpenAIProvider(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"],
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

    memory = Memory(content=content, created_time=datetime.now())
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
            memory.created_time = datetime.now()  # update timestamp to now
            session.add(memory)  # type: ignore
            session.commit()  # type: ignore


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

    attach_memories_prompt(chatagent)

    return chatagent


def build_splitter_agent() -> Agent:
    splitter_agent = Agent(
        model=get_model(),
        toolsets=[FunctionToolset(tools=[delete_memory, store_memory, update_memory])],
        system_prompt=f"""{cleanerprefix}

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

# INFO
Today is { datetime.now().strftime("%Y-%m-%d %H:%M:%S") }

""",
    )

    attach_memories_prompt(splitter_agent)

    return splitter_agent


def build_aggregator_agent() -> Agent:
    aggregator_agent = Agent(
        model=get_model(),
        toolsets=[FunctionToolset(tools=[store_memory, delete_memory])],
        system_prompt=f"""{cleanerprefix}

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

# INFO
Today is { datetime.now().strftime("%Y-%m-%d") }""",
    )

    attach_memories_prompt(aggregator_agent)

    return aggregator_agent


def build_deduplicator_agent() -> Agent:
    dedup_agent = Agent(
        model=get_model(),
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

    attach_memories_prompt(dedup_agent)

    return dedup_agent


def build_garbage_collector_agent() -> Agent:

    garbage_collector_agent = Agent(
        model=get_model(),
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

    attach_memories_prompt(garbage_collector_agent)

    return garbage_collector_agent
