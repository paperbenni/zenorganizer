# CRUSH.md

Build / run / lint / test
- Run app (dev): just run  (uses `uv run main.py` under the pinned environment)
- Sync environment: uv sync
- Run single script: uv run <script.py>
- Format: uvx ruff format
- Lint: uvx ruff check
- Typecheck: uvx ty check
- Run tests: just test  (runs `uv run pytest`)
- Run pytest directly: uv run pytest
- Run a single test: uv run pytest tests/path/to/test_file.py::test_name
  or: python -m pytest tests/path/to/test_file.py::test_name

Code style & conventions
- Formatting: use ruff (uvx ruff format) — run before commits/PRs.
- Indentation: 4 spaces.
- Imports: group and order as: stdlib, third-party, local (one blank line between groups). Prefer absolute imports within project.
- Typing: use explicit type hints for public functions and async functions; prefer typing from `typing` and project-provided stub packages.
- Async: storage and IO helpers are async; prefer `async def` and `await` for DB/network ops.
- Naming: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants.
- Error handling: avoid bare `except:`; catch specific exceptions, log and re-raise or wrap when appropriate. Use structured logging (logfire) where available.
- DB/migrations: modify models in zeno/models.py, then run alembic autogenerate + review migrations.
- Tests: place tests under tests/, name files test_*.py and functions test_*(). Use temporary SQLite files or ./data for DB tests.

Secrets & repo rules
- Keep secrets out of git: use .env (example.env provided).
- Repo rule: do NOT create git commits or push from automated agents without explicit user permission.

Cursor / Copilot rules
- No .cursor rules or .cursorrules found in repository.
- No .github/copilot-instructions.md present.

Keep this file concise; update with new commands or rules as the project evolves.