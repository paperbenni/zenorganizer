def main():
    # Entry point for the package — run the telegram bot.
    # Run both the Telegram bot and a FastAPI app concurrently using asyncio.
    import asyncio
    from zeno.telegram_bot import run_bot
    from zeno.api import app as fastapi_app
    import uvicorn

    async def run_both():
        bot_task = asyncio.to_thread(run_bot)
        api_config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(api_config)
        api_task = asyncio.create_task(server.serve())
        await bot_task
        # Shutdown server when bot exits
        api_task.cancel()

    asyncio.run(run_both())


if __name__ == "__main__":
    main()
