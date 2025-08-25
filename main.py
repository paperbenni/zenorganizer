def main():
    # Entry point for the package — run the telegram bot and a Flask app
    # concurrently in the same process. Start the Flask dev server in a
    # background thread so both the API and the bot run together.
    import threading
    from zeno.telegram_bot import run_bot
    from zeno.api_flask import app as flask_app
    import logfire
    import os
    import dotenv
    import time
    import asyncio

    dotenv.load_dotenv()

    logfire_token = os.environ["LOGFIRE_TOKEN"]
    if logfire_token:
        print("Logging to LogFire!!!")
        logfire.configure(token=logfire_token)
        logfire.info('Hello, {place}!', place='World')
        logfire.instrument_pydantic_ai()

    def run_flask():
        # Use Flask's built-in server for dev usage.
        flask_app.run(host="0.0.0.0", port=8001)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Periodically run the deduplicator agent in a background thread.
    def run_periodic_maintenance(interval_hours: int = 10) -> None:
        from zeno.agents import (
            build_deduplicator_agent,
            build_aggregator_agent,
            build_splitter_agent,
            build_garbage_collector_agent,
        )
        import logging

        logger = logging.getLogger("zeno.periodic")

        while True:
            # initial short sleep to stagger startup
            time.sleep(600)
            try:
                logfire.info('Running gardening stuff')
                # 1) Deduplicate
                dedup_agent = build_deduplicator_agent()
                resp = asyncio.run(dedup_agent.run("Deduplicate memories"))
                logger.info("Deduplicator run complete: %s", getattr(resp, "output", "(no output)"))

                # 2) Aggregate
                aggregator = build_aggregator_agent()
                resp = asyncio.run(aggregator.run("Aggregate memories"))
                logger.info("Aggregator run complete: %s", getattr(resp, "output", "(no output)"))

                # 3) Splitter
                splitter = build_splitter_agent()
                resp = asyncio.run(splitter.run("Split overaggregated memories"))
                logger.info("Splitter run complete: %s", getattr(resp, "output", "(no output)"))

                # 4) Garbage collector
                gc = build_garbage_collector_agent()
                resp = asyncio.run(gc.run("Garbage collect old/unneeded memories"))
                logger.info("Garbage collector run complete: %s", getattr(resp, "output", "(no output)"))
            except Exception:
                logger.exception("Periodic maintenance failed")

            time.sleep(interval_hours * 3600)


    # Separate reminder loop runs more frequently (every 15 minutes)
    def run_reminder_loop(interval_minutes: int = 15) -> None:
        from zeno.agents import build_reminder_agent
        import logging

        logger = logging.getLogger("zeno.reminder")

        while True:
            try:
                reminder = build_reminder_agent()
                logfire.info('Running reminder agent')
                resp = asyncio.run(reminder.run("Check for due reminders", message_history=None))
                logger.info("Reminder agent run complete: %s", getattr(resp, "output", "(no output)"))
            except Exception:
                logger.exception("Reminder agent failed")
                logfire.info('Reminder agent failed')

            time.sleep(interval_minutes * 60)

    gardening_thread = threading.Thread(target=run_periodic_maintenance, daemon=True)
    gardening_thread.start()
    reminder_thread = threading.Thread(target=run_reminder_loop, daemon=True)
    reminder_thread.start()

    run_bot()


if __name__ == "__main__":
    main()
