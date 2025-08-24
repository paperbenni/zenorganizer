"""Zeno package — small refactor of the original single-file project.

Public API:
- run_bot(): start the telegram bot (provided by zeno.telegram_bot.run_bot)
"""

"""Lightweight package entry-points for zeno.

This module avoids importing heavy 3rd-party dependencies at import time.
Call `run_bot()` to start the telegram bot; the implementation will be
lazily imported when needed.
"""

from .telegram_bot import run_bot

__all__ = ["run_bot"]
