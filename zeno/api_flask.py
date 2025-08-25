from flask import Flask, request, jsonify, Response
import asyncio

from . import storage
from .agents import build_deduplicator_agent

app = Flask(__name__)


@app.route("/memories")
def get_memories():
    show_id = request.args.get("show_id") == "1"
    return Response(storage.get_memories(show_id), mimetype="text/plain")


@app.route("/deduplicate", methods=["POST"])
def deduplicate():
    dedup_agent = build_deduplicator_agent()
    # run the async agent synchronously for simplicity
    resp = asyncio.run(dedup_agent.run("Deduplicate memories"))
    return jsonify({"output": resp.output})


@app.route("/old_messages")
def old_messages():
    # Return the last `limit` messages (default 20) as a human-readable Markdown-like representation.
    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        limit = 20

    msgs = storage.get_old_messages(limit)
    md = "# Old Messages\n\n"
    for i, m in enumerate(msgs, 1):
        md += f"## Message {i}\n"
        md += f"**Parts:** {', '.join(type(p).__name__ for p in m.parts)}\n\n"
        for j, p in enumerate(m.parts, 1):
            md += f"### Part {j}: {type(p).__name__}\n"
            # Try to get a human-readable content for each part
            content = getattr(p, "content", None)
            if content is not None:
                md += f"{content}\n\n"
            else:
                # fallback to str
                md += f"{str(p)}\n\n"
        md += "---\n"
    return Response(md, mimetype="text/markdown")
   


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
