import threading
import os
import dotenv
import asyncio
import logging
import time
import math

import logfire
from zeno.telegram_bot import run_bot
from zeno.api import app as api_app
from zeno.agents import (
    build_deduplicator_agent,
    build_aggregator_agent,
    build_splitter_agent,
    build_garbage_collector_agent,
    build_reminder_agent,
)


def setup_logfire() -> None:
    """Load environment and configure LogFire if a token is present."""
    dotenv.load_dotenv()

    token = os.environ.get("LOGFIRE_TOKEN")
    logger = logging.getLogger(__name__)
    if token:
        logger.info("Configuring LogFire instrumentation")
        logfire.configure(token=token, scrubbing=False)
        logfire.info("starting agent")
        logfire.instrument_pydantic_ai()


def _run_uvicorn() -> None:
    """Run the FastAPI app with uvicorn (used in a background thread)."""
    import uvicorn

    uvicorn.run(api_app, host="0.0.0.0", port=8001)


def start_api_thread() -> threading.Thread:
    """Start the web API in a daemon thread and return the Thread object."""
    t = threading.Thread(target=_run_uvicorn, daemon=True)
    t.start()
    return t


async def _periodic_maintenance_loop(
    interval_hours: int, offset_seconds: int = 300
) -> None:
    """Async loop for periodic maintenance tasks (dedup/aggregate/split/gc).

    Runs are aligned to wall-clock multiples of the interval, with an additional
    offset (in seconds) applied so maintenance runs do not collide with other
    periodic tasks such as reminders. The offset is taken modulo the interval
    length.
    """
    logger = logging.getLogger("zeno.periodic")
    interval_secs = interval_hours * 3600

    # Normalize offset to [0, interval_secs)
    offset = offset_seconds % interval_secs

    # Align to the next multiple of interval_secs, then apply the offset
    now = time.time()
    base_next = math.ceil((now - offset) / interval_secs) * interval_secs
    next_run = base_next + offset
    sleep_for = max(0, next_run - now)
    if sleep_for:
        await asyncio.sleep(sleep_for)

    while True:
        try:
            logfire.info("Running gardening stuff")

            dedup_agent = await build_deduplicator_agent()
            resp = await dedup_agent.run("Deduplicate memories")
            logger.info(
                "Deduplicator run complete: %s",
                getattr(resp, "output", "(no output)"),
            )

            aggregator = await build_aggregator_agent()
            resp = await aggregator.run("Aggregate memories")
            logger.info(
                "Aggregator run complete: %s",
                getattr(resp, "output", "(no output)"),
            )

            splitter = await build_splitter_agent()
            resp = await splitter.run("Split overaggregated memories")
            logger.info(
                "Splitter run complete: %s",
                getattr(resp, "output", "(no output)"),
            )

            gc = await build_garbage_collector_agent()
            resp = await gc.run("Garbage collect old/unneeded memories")
            logger.info(
                "Garbage collector run complete: %s",
                getattr(resp, "output", "(no output)"),
            )

        except Exception:
            logger.exception("Periodic maintenance failed")

        # compute next aligned run time (with offset) to avoid drift
        now = time.time()
        base_next = math.ceil((now - offset) / interval_secs) * interval_secs
        next_run = base_next + offset
        if next_run <= now:
            next_run += interval_secs
        await asyncio.sleep(next_run - now)


def start_periodic_thread(
    interval_hours: int = 10, offset_seconds: int = 300
) -> threading.Thread:
    """Start the periodic maintenance loop in a daemon thread.

    offset_seconds will be passed to the loop to offset the maintenance runs so
    they don't collide with the reminder runs.
    """

    def target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _periodic_maintenance_loop(interval_hours, offset_seconds)
        )

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return t


async def _reminder_loop(interval_minutes: int) -> None:
    """Async loop for reminder agent runs, aligned to wall-clock intervals."""
    logger = logging.getLogger("zeno.reminder")
    interval_secs = interval_minutes * 60

    now = time.time()
    next_run = math.ceil(now / interval_secs) * interval_secs
    sleep_for = max(0, next_run - now)
    if sleep_for:
        await asyncio.sleep(sleep_for)

    while True:
        try:
            reminder = await build_reminder_agent()
            logfire.info("Running reminder agent")
            resp = await reminder.run("Check for due reminders", message_history=None)
            logger.info(
                "Reminder agent run complete: %s",
                getattr(resp, "output", "(no output)"),
            )
        except Exception:
            logger.exception("Reminder agent failed")
            logfire.info("Reminder agent failed")

        now = time.time()
        next_run = math.ceil(now / interval_secs) * interval_secs
        if next_run <= now:
            next_run += interval_secs
        await asyncio.sleep(next_run - now)


def start_reminder_thread(interval_minutes: int = 15) -> threading.Thread:
    """Start the reminder loop in a daemon thread."""

    def target() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_reminder_loop(interval_minutes))

    t = threading.Thread(target=target, daemon=True)
    t.start()
    return t


def main() -> None:
    """Small entrypoint: configure logging, start background threads and run bot."""
    setup_logfire()

    start_api_thread()
    # Start maintenance with a small offset so it doesn't collide with reminders.
    # Default reminder interval is 15 minutes (900s) and maintenance offset is 5 minutes (300s),
    # which results in maintenance runs offset from reminder ticks. Adjust offsets via args/env later.
    start_periodic_thread(offset_seconds=300)
    start_reminder_thread()

    run_bot()


if __name__ == "__main__":
    main()
