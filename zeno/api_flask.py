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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
