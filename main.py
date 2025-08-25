def main():
    # Entry point for the package — run the telegram bot and a Flask app
    # concurrently in the same process. Start the Flask dev server in a
    # background thread so both the API and the bot run together.
    import threading
    from zeno.telegram_bot import run_bot
    from zeno.api_flask import app as flask_app

    def run_flask():
        # Use Flask's built-in server for dev usage.
        flask_app.run(host="0.0.0.0", port=8001)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Periodically run the deduplicator agent in a background thread.
    def run_periodic_maintenance(interval_hours: int = 10) -> None:
        import time
        import asyncio
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

    dedup_thread = threading.Thread(target=run_periodic_maintenance, daemon=True)
    dedup_thread.start()

    run_bot()


if __name__ == "__main__":
    main()
