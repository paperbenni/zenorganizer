import os

# Chat id used by the bot and agents. Must be set via TELEGRAM_CHAT_ID environment variable.
# This is required for security - no default value is provided.
try:
    TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
except (KeyError, TypeError, ValueError) as e:
    raise RuntimeError(
        "TELEGRAM_CHAT_ID environment variable must be set to a valid integer. "
        "This is required for bot security and cannot have a default value."
    ) from e
