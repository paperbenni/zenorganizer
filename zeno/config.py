import os

# Default chat id used by the bot and agents. Can be overridden with the
# TELEGRAM_CHAT_ID environment variable (useful for deployment/testing).
try:
    TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "1172527123"))
except (TypeError, ValueError):
    TELEGRAM_CHAT_ID = 1172527123
