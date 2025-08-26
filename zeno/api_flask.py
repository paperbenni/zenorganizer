import asyncio
import uuid
from typing import Any, Dict

from flask import Flask, Response, jsonify, request

from . import storage
from .agents import build_deduplicator_agent

app = Flask(__name__)
logger = app.logger

# Simple in-memory task registry (task_id -> asyncio.Task)
# and a results mapping populated when tasks finish.
_tasks: Dict[str, asyncio.Task] = {}
_results: Dict[str, Dict[str, Any]] = {}


@app.route("/memories")
async def get_memories() -> Any:
    """Return stored memories as plain text.

    Storage is synchronous, so run it in a threadpool to avoid blocking the
    Flask async loop.
    """
    show_id = request.args.get("show_id") == "1"
    try:
        output = await storage.get_memories(show_id)
    except Exception as exc:  # pragma: no cover - surface runtime errors
        logger.exception("Failed to get memories")
        return jsonify({"error": "failed to get memories", "detail": str(exc)}), 500

    return Response(output, content_type="text/plain; charset=utf-8")


@app.route("/deduplicate", methods=["POST"])
async def deduplicate() -> Any:
    """Start a deduplication run.

    By default the deduplicator runs in the background and this endpoint will
    return a task id (202 Accepted). If the client passes ?wait=1 the request
    will block until completion and return the result (useful for debugging).
    """
    wait = request.args.get("wait", "0") in ("1", "true", "yes")
    if wait:
        try:
            dedup_agent = await build_deduplicator_agent()
            resp = await dedup_agent.run("Deduplicate memories")
            return jsonify({"output": getattr(resp, "output", None)})
        except Exception as exc:
            logger.exception("Deduplication failed (sync)")
            return jsonify({"error": str(exc)}), 500

    # Background execution path
    task_id = uuid.uuid4().hex

    async def _run_and_store() -> Any:
        try:
            # Build agent inside the task to avoid capturing coroutine objects
            agent = await build_deduplicator_agent()
            res = await agent.run("Deduplicate memories")
            _results[task_id] = {
                "status": "done",
                "output": getattr(res, "output", None),
            }
        except Exception as exc:  # pragma: no cover - keep task from crashing silently
            logger.exception("Deduplication task failed")
            _results[task_id] = {"status": "error", "error": str(exc)}

    task = asyncio.create_task(_run_and_store())
    _tasks[task_id] = task

    # Remove task entry after completion but keep results for inspection
    def _on_done(t: asyncio.Task, tid=task_id) -> None:
        _tasks.pop(tid, None)

    task.add_done_callback(_on_done)

    return jsonify({"task_id": task_id}), 202


@app.route("/tasks/<task_id>")
async def get_task_status(task_id: str) -> Any:
    """Get status/result for a background task started via /deduplicate.

    Returns 404 if the given id is unknown.
    """
    if task_id in _results:
        return jsonify(_results[task_id])

    task = _tasks.get(task_id)
    if task is None:
        return jsonify({"error": "unknown task id"}), 404

    if task.done():
        # Ensure any result has been stored by the task callback body
        return jsonify({"status": "done"})

    return jsonify({"status": "running"})


@app.route("/old_messages")
async def old_messages() -> Any:
    """Return the last `limit` messages as Markdown.

    Validates the `limit` query parameter and offloads synchronous storage
    access to a threadpool.
    """
    limit_str = request.args.get("limit", "20")
    try:
        limit = int(limit_str)
        if limit <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "invalid `limit` parameter"}), 400

    try:
        msgs = await storage.get_old_messages(limit)
    except Exception as exc:  # pragma: no cover - surface runtime errors
        logger.exception("Failed to get old messages")
        return jsonify({"error": "failed to get old messages", "detail": str(exc)}), 500

    parts: list[str] = ["# Old Messages\n\n"]
    for i, m in enumerate(msgs, 1):
        parts.append(f"## Message {i}\n")
        parts.append(f"**Parts:** {', '.join(type(p).__name__ for p in m.parts)}\n\n")

        for j, p in enumerate(m.parts, 1):
            parts.append(f"### Part {j}: {type(p).__name__}\n")
            content = getattr(p, "content", None)
            if content is not None:
                # If content is bytes, decode safely
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
    return Response(md, content_type="text/markdown; charset=utf-8")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
