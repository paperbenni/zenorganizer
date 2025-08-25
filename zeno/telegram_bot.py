import os
import dotenv
import logging
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .agents import build_chat_agent
from .storage import init_db, get_old_messages, store_message_archive

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
    # TODO: make this configurable or use the DB
    if message.from_user.id != 1172527123:
        await context.bot.send_message(chat_id=chat.id, text="You are not authorized to use this bot.")
        return

    agent = build_chat_agent()
    response = await agent.run(message.text, message_history=get_old_messages(20))
    messages = response.new_messages_json()
    # use storage helper to persist the message archive
    store_message_archive(messages)
    await context.bot.send_message(chat_id=chat.id, text=response.output)


def run_bot() -> None:
    dotenv.load_dotenv()
    init_db()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

    application = ApplicationBuilder().token(token).build()
    start_handler = CommandHandler("start", start)
    chat_handler = MessageHandler(filters.USER & filters.TEXT & (~filters.COMMAND), run_chat_agent)
    application.add_handler(start_handler)
    application.add_handler(chat_handler)
    application.run_polling()
