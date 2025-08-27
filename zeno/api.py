import asyncio
import uuid
import logging
from typing import Any, Dict

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, JSONResponse, Response

from . import storage
from .agents import build_deduplicator_agent

app = FastAPI()
logger = logging.getLogger("zeno.api")

# Simple in-memory task registry (task_id -> asyncio.Task) and results mapping
_tasks: Dict[str, asyncio.Task] = {}
_results: Dict[str, Dict[str, Any]] = {}


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
    """Start a deduplication run.

    - If wait is true the request blocks until the run completes and returns the
      agent output (useful for debugging).
    - Otherwise, spawn a background task and return a task_id (202 Accepted).
    """
    if wait:
        try:
            dedup_agent = await build_deduplicator_agent()
            resp = await dedup_agent.run("Deduplicate memories")
            return JSONResponse({"output": getattr(resp, "output", None)})
        except Exception as exc:
            logger.exception("Deduplication failed (sync)")
            return JSONResponse({"error": str(exc)}, status_code=500)

    task_id = uuid.uuid4().hex

    async def _run_and_store(tid: str) -> None:
        try:
            agent = await build_deduplicator_agent()
            res = await agent.run("Deduplicate memories")
            _results[tid] = {
                "status": "done",
                "output": getattr(res, "output", None),
            }
        except Exception as exc:  # pragma: no cover - keep task from crashing silently
            logger.exception("Deduplication task failed")
            _results[tid] = {"status": "error", "error": str(exc)}

    task = asyncio.create_task(_run_and_store(task_id))
    _tasks[task_id] = task

    def _on_done(t: asyncio.Task, tid=task_id) -> None:
        # remove the live-task entry but keep results around for inspection
        _tasks.pop(tid, None)

    task.add_done_callback(_on_done)

    return JSONResponse({"task_id": task_id}, status_code=202)


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> JSONResponse:
    """Get status/result for a background task started via /deduplicate.

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
