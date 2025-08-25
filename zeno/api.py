from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, JSONResponse

from . import storage
from .agents import build_deduplicator_agent

app = FastAPI()


@app.get("/memories")
def get_memories(show_id: bool = False):
    """Return the stored memories as plain text."""
    return PlainTextResponse(storage.get_memories(show_id))


@app.post("/deduplicate")
async def trigger_deduplicator():
    """Run the deduplicator agent to clean up duplicate/contradictory memories.

    Returns the agent's output string.
    """
    dedup_agent = build_deduplicator_agent()
    # run the agent; it uses tools (delete_memory) to modify the DB as needed
    response = await dedup_agent.run("Deduplicate memories")
    return JSONResponse({"output": response.output})


