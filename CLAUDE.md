# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Summary
- Minimal Python async service that runs a Telegram bot and a small Flask API in the same process.
- Uses pydantic_ai Agents to implement memory/agent behavior; agents call back into local async "tool" functions which persist to a SQLite DB and send Telegram messages.

Key commands
- Development / run
  - just run               # uses uv to run main.py (preferred local shortcut)
  - uv sync
  - uv run main.py         # run the application directly with uv

  Note: This project uses the "uv" tool as the runtime/launcher for running
  the application and managing dependencies. Use `uv sync` to synchronize the
  environment from uv.lock and `uv run <script>` (for example `uv run main.py`)
  to run scripts with the project's pinned dependencies. Tools like `uvx` are
  used for invoking linters/formatters in the uv-managed environment.
- Lint / format / checks (shortcuts in justfile)
  - uvx ruff format       # format code with ruff
  - uvx ruff check        # ruff lint
  - uvx ty check          # type checks (project configured for ty)
- Database / data dir helpers
  - just ensure-data-dir   # create ./data and set ownership (used for nocodb setup)

Database migrations (alembic)
- Use the alembic CLI (installed in the uv-managed environment) to generate and apply migrations. Do not hand-edit alembic version files unless absolutely necessary; prefer alembic autogeneration.
- Typical workflow (run inside the uv environment):
  - uv run alembic revision --autogenerate -m "describe changes"
  - uv run alembic upgrade head
- Useful commands:
  - uv run alembic history --verbose
  - uv run alembic current
  - uv run alembic downgrade -1  # step back one revision
- Notes:
  - Make model/schema changes in zeno/models.py first, then run alembic revision --autogenerate to create a migration reflecting those changes.
  - The project uses SQLite; alembic autogenerate should work for most schema changes but inspect generated migrations before applying them to ensure correctness.
- Docker / nocodb (project helper)
  - docker compose up -d   # start nocodb (see justfile nocodb-up)
  - docker compose down
- Running agents / debugging via API
  - curl -X POST "http://localhost:8001/deduplicate?wait=1"  # run deduplicator synchronously for debugging
  - GET /memories and /old_messages endpoints are available on the Flask app (port 8001 by default)
- Tests
  - There are currently no tests in the repository. If tests are added, run them with:
    - python -m pytest
    - python -m pytest path/to/test_file.py::test_name  # run a single test

Environment and important variables
- Put secrets and configuration in a .env file (example.env is included).
- Environment variables referenced in code:
  - TELEGRAM_BOT_TOKEN    # required for bot and send_reminder tool
  - TELEGRAM_CHAT_ID      # optional override; default present in zeno/config.py
  - OPENAI_API_KEY        # used by pydantic_ai OpenAIProvider
  - MODEL_NAME            # model name passed to OpenAIModel
  - OPENAI_BASE_URL       # optional custom base URL for OpenAI provider
  - LOGFIRE_TOKEN         # optional, used to enable logfire instrumentation

High-level architecture and where to look
- Entry point
  - main.py
    - Starts: Flask dev server (in a background thread) + Telegram polling bot (polling in main thread)
    - Spawns background threads for periodic maintenance (dedup/aggregate/split/gc) and reminders

- Web API
  - zeno/api_flask.py
    - Lightweight Flask async endpoints for: /memories, /deduplicate (background task support), /tasks/<id>, /old_messages
    - Background task registry stored in-memory for short-lived debug tasks

- Telegram bot
  - zeno/telegram_bot.py
    - Uses python-telegram-bot ApplicationBuilder with polling
    - Handlers: /start and a message handler that forwards messages to the chat agent
    - Ensures DB init via zeno.storage.init_db() before starting

- Agents and decision logic
  - zeno/agents.py
    - Builds several Agent instances (pydantic_ai) wired to an OpenAIModel
    - Agents: chat_agent (handles incoming chat messages), deduplicator, aggregator, splitter, garbage_collector, reminder_agent
    - Agents are configured with human-readable instructions and a small set of tool function bindings

- Tool functions (what agents can call)
  - zeno/tools.py
    - Async functions exposed to agents: store_memory, update_memory, delete_memory, send_reminder
    - send_reminder uses python-telegram-bot Bot to send messages and persists the message archive

- Storage / DB
  - zeno/storage.py
    - Async helpers that read/write MessageArchive and Memory rows
    - Storage is implemented with async SQLAlchemy (async engine/session) and all storage helpers are async; call them with await
    - Ensures ./data directory exists when initialising DB
    - Provides get_memories, get_old_messages, store_message_archive, init_db
  - zeno/db.py
    - SQLAlchemy async engine/sessionmaker (sqlite+aiosqlite:///./data/zeno.db)
    - Schema creation is handled via Alembic migrations (do not create tables at runtime)
  - zeno/models.py
    - SQLAlchemy models: Memory and MessageArchive

- Utilities
  - zeno/utils.py
    - get_current_time() (Europe/Berlin timezone)
    - split_and_send() helper to safely send long Telegram messages

Data and persistence
- Local SQLite DB: ./data/zeno.db (DATABASE_URL constant in zeno/db.py and zeno/storage.py)
- Message archives stored as JSON text in MessageArchive.content

Developer notes for future Claude Code instances
- Look at zeno/agents.py first to understand available agents and the tool surface they expect.
- Tool functions in zeno/tools.py have the minimal contracts agents rely on; changes to their signatures must be reflected in the agent FunctionToolset wiring.
- The Flask API endpoints are small and are useful for manual testing and triggering agents (see /deduplicate and /tasks/<id>). The /deduplicate endpoint supports ?wait=1 to block the request until the agent run completes (useful for debugging).
- DB initialization: call zeno.storage.init_db() (or run the application) before invoking agents that persist memories.
- When modifying reminders/agent logic, inspect send_reminder and store_message_archive behavior—reminders both deliver (via Telegram) and write an archive entry so agents can avoid duplicate sends.

Files and areas to inspect for specific changes
- Agent prompts & rules: zeno/agents.py
- Agent-exposed tools: zeno/tools.py
- Persistence layer: zeno/storage.py, zeno/db.py, zeno/models.py
- Bot glue and handlers: zeno/telegram_bot.py
- HTTP endpoints for quick debugging: zeno/api.py (FastAPI)

Notes / caveats
- The project runs an ASGI FastAPI app (uvicorn) for development — this is intended for development/debugging, not production deployment.
- The application uses polling for the Telegram bot (Application.run_polling()). For production, consider webhook-based delivery.
- Timezone: get_current_time() returns Europe/Berlin; be mindful when reasoning about reminders/time-sensitive logic.
- There are no automated tests in the repo at present — add pytest tests under a tests/ directory and run with pytest.

If a CLAUDE.md already exists
- Suggest improvements instead of replacing it. (This run created the initial CLAUDE.md.)

Repository rule
- **Important:** Do not ever create git commits. Do not create, modify, or push commits in this repository; follow the contributor workflow described in project documentation instead.
