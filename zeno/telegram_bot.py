import logging
import os

import dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .storage import get_old_messages, init_db, store_message_archive

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat is None:
        return
    await context.bot.send_message(chat_id=chat.id, text="Hello tere")


async def run_chat_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.message
    if chat is None or message is None:
        return
    if message.text is None:
        return
    print("sender from")
    print(message.from_user)
    if message.from_user is None:
        return
    # Check against configured allowed chat id
    from .config import TELEGRAM_CHAT_ID

    if message.from_user.id != TELEGRAM_CHAT_ID:
        await context.bot.send_message(
            chat_id=chat.id, text="You are not authorized to use this bot."
        )
        return
    from .agents import build_chat_agent

    chatagent = await build_chat_agent()
    history = await get_old_messages(10)
    response = await chatagent.run(message.text, message_history=history)
    messages = response.new_messages_json()
    # use storage helper to persist the message archive
    await store_message_archive(messages)
    await context.bot.send_message(chat_id=chat.id, text=response.output)


def run_bot() -> None:
    dotenv.load_dotenv()
    # Ensure DB initialized before running the bot
    import asyncio as _asyncio

    _asyncio.run(init_db())

    # Ensure main thread has an event loop for libraries that call get_event_loop()
    try:
        _asyncio.get_running_loop()
    except RuntimeError:
        _asyncio.set_event_loop(_asyncio.new_event_loop())

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

    application = ApplicationBuilder().token(token).build()
    start_handler = CommandHandler("start", start)
    chat_handler = MessageHandler(
        filters.USER & filters.TEXT & (~filters.COMMAND), run_chat_agent
    )
    application.add_handler(start_handler)
    application.add_handler(chat_handler)
    application.run_polling()
