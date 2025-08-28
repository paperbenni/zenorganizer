# Repository Guidelines

This document gives concise contributor rules specific to Zenorganizer.

## Project Structure & Module Organization

- **Source:** `zeno/` contains core modules (`api.py`, `agents.py`, `models.py`, `storage.py`, `telegram_bot.py`).
- **Entry point:** `main.py` launches the app.
- **Migrations:** `alembic/` and `alembic/versions/` hold DB migrations.
- **Config / env:** `example.env` and `.env` hold environment variables; `alembic.ini` for DB settings.
- **Data:** `data/` and `test.db` for local storage and testing artifacts.

## Build, Test, and Development Commands

- `uv run main.py` — run the application locally (use the project's `uv` wrapper).
- `uv sync` — run background sync and scheduled tasks.
- `uv run alembic upgrade head` — apply DB migrations.
- `just check` — run linting and formatting (configured in `Justfile`).
- `docker-compose up` — run services via Docker (reads `docker-compose.yml`).

## Coding Style & Naming Conventions

- Python, 4-space indentation. Follow standard Python idioms.
- Use descriptive module and function names (e.g., `zeno/storage.py`, `save_memory`).
- Keep agent functions in `zeno/agents.py`; handlers in `zeno/api.py`.
- Formatting: run `just check` to lint/format before committing; project preferences live in `pyproject.toml`.

## Testing Guidelines

- No formal test suite currently; add tests alongside new modules in a `tests/` folder.
- Name tests `test_<module>.py` and functions `test_<behavior>()`.
- For DB-related tests, use a temporary SQLite file or the provided `test.db`.

## Commit & Pull Request Guidelines

- Commit messages: short imperative summary (e.g., "add agent for /messages").
- PRs should include: description, linked issue if any, a short checklist of changes, and logs/screenshots for UI or behavioral changes.
- Keep PRs focused: one feature/bug per PR.

## Security & Configuration Tips

- Do not commit secrets. Use `.env` and `example.env` as templates.
- Rotate API keys stored in config and document where to set them in `example.env`.

If you want, I can add a `tests/` scaffold, CI config, or a `CONTRIBUTING.md` with expanded workflow.
