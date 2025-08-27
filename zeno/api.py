import asyncio
import uuid
import logging
from typing import Any, Dict, Callable, Awaitable

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, JSONResponse, Response

from . import storage
from .agents import (
    build_deduplicator_agent,
    build_aggregator_agent,
    build_splitter_agent,
    build_garbage_collector_agent,
    build_reminder_agent,
)

app = FastAPI()
logger = logging.getLogger("zeno.api")

# Simple in-memory task registry (task_id -> asyncio.Task) and results mapping
_tasks: Dict[str, asyncio.Task] = {}
_results: Dict[str, Dict[str, Any]] = {}


async def _run_agent_and_store(
    tid: str, builder: Callable[[], Awaitable[Any]], run_arg: str
) -> None:
    """Build and run an agent, storing its result into _results under tid.

    This isolates the background execution logic so endpoints can reuse it.
    """
    try:
        agent = await builder()
        res = await agent.run(run_arg)
        _results[tid] = {"status": "done", "output": getattr(res, "output", None)}
    except Exception as exc:  # pragma: no cover - keep task from crashing silently
        logger.exception("Agent task failed: %s", run_arg)
        _results[tid] = {"status": "error", "error": str(exc)}


async def _handle_agent_request(
    builder: Callable[[], Awaitable[Any]], run_arg: str, wait: bool
) -> JSONResponse:
    """Common handler to either run an agent synchronously (wait=True) or spawn
    a background task and return a task id.

    The endpoint is responsible for HTTP concerns only; this helper centralizes
    orchestration so each route remains a thin wrapper.
    """
    if wait:
        try:
            agent = await builder()
            res = await agent.run(run_arg)
            return JSONResponse({"output": getattr(res, "output", None)})
        except Exception as exc:
            logger.exception("Agent run failed (sync): %s", run_arg)
            return JSONResponse({"error": str(exc)}, status_code=500)

    task_id = uuid.uuid4().hex
    task = asyncio.create_task(_run_agent_and_store(task_id, builder, run_arg))
    _tasks[task_id] = task

    def _on_done(t: asyncio.Task, tid=task_id) -> None:
        _tasks.pop(tid, None)

    task.add_done_callback(_on_done)
    return JSONResponse({"task_id": task_id}, status_code=202)


@app.get("/memories")
async def get_memories(show_id: int = Query(0, ge=0)) -> Response:
    """Return stored memories as plain text.

    Human readable
    """
    try:
        output = await storage.get_memories(show_id == 1)
    except Exception as exc:  # pragma: no cover - surface runtime errors
        logger.exception("Failed to get memories")
        return JSONResponse(
            {"error": "failed to get memories", "detail": str(exc)}, status_code=500
        )

    return PlainTextResponse(output, media_type="text/plain; charset=utf-8")


@app.post("/deduplicate")
async def deduplicate(wait: bool = Query(False)) -> JSONResponse:
    """Start a deduplication run."""
    return await _handle_agent_request(
        build_deduplicator_agent, "Deduplicate memories", wait
    )


@app.post("/aggregate")
async def aggregate(wait: bool = Query(False)) -> JSONResponse:
    """Run the memory aggregator agent (merge related memories)."""
    return await _handle_agent_request(
        build_aggregator_agent, "Aggregate memories", wait
    )


@app.post("/split")
async def split(wait: bool = Query(False)) -> JSONResponse:
    """Run the splitter agent to split over-aggregated memories."""
    return await _handle_agent_request(
        build_splitter_agent, "Split overaggregated memories", wait
    )


@app.post("/garbage_collect")
async def garbage_collect(wait: bool = Query(False)) -> JSONResponse:
    """Run the garbage collector agent to remove old/unneeded memories."""
    return await _handle_agent_request(
        build_garbage_collector_agent, "Garbage collect old/unneeded memories", wait
    )


@app.post("/reminders")
async def reminders(wait: bool = Query(False)) -> JSONResponse:
    """Run the reminder agent (checks and sends due reminders).

    Note: reminder agent's work may send messages via Telegram; running it
    synchronously (wait=True) will block until delivery attempts complete.
    """
    return await _handle_agent_request(
        build_reminder_agent, "Check for due reminders", wait
    )


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> JSONResponse:
    """Get status/result for a background task started via agent endpoints.

    Returns 404 if the given id is unknown.
    """
    if task_id in _results:
        return JSONResponse(_results[task_id])

    task = _tasks.get(task_id)
    if task is None:
        return JSONResponse({"error": "unknown task id"}, status_code=404)

    if task.done():
        return JSONResponse({"status": "done"})

    return JSONResponse({"status": "running"})


@app.get("/old_messages")
async def old_messages(limit: int = Query(20, ge=1)) -> Response:
    """Return the last `limit` messages as Markdown."""
    try:
        msgs = await storage.get_old_messages(limit)
    except Exception as exc:  # pragma: no cover - surface runtime errors
        logger.exception("Failed to get old messages")
        return JSONResponse(
            {"error": "failed to get old messages", "detail": str(exc)}, status_code=500
        )

    parts: list[str] = ["# Old Messages\n\n"]
    for i, m in enumerate(msgs, 1):
        parts.append(f"## Message {i}\n")
        parts.append(f"**Parts:** {', '.join(type(p).__name__ for p in m.parts)}\n\n")

        for j, p in enumerate(m.parts, 1):
            parts.append(f"### Part {j}: {type(p).__name__}\n")
            content = getattr(p, "content", None)
            if content is not None:
                if isinstance(content, (bytes, bytearray)):
                    try:
                        content = content.decode()
                    except Exception:
                        content = str(content)
                parts.append(f"{content}\n\n")
            else:
                parts.append(f"{str(p)}\n\n")
        parts.append("---\n")

    md = "".join(parts)
    return Response(md, media_type="text/markdown; charset=utf-8")
