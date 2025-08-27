from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_time() -> datetime:
    """Get current datetime in Europe/Berlin timezone."""
    return datetime.now(tz=ZoneInfo("Europe/Berlin"))


async def split_and_send(send, text: str, chat_id: int | None = None, max_length: int = 4096, **kwargs):
    """Send `text` directly if it's short enough, otherwise fall back to a
    very simple splitter.

    This is intended as a rare fallback for unusually long messages.
    """
    if not text:
        return

    # If the message fits within the limit, send it directly (no extra work).
    if len(text) <= max_length:
        send_kwargs = {"text": text, **kwargs}
        send_kwargs = {k: v for k, v in send_kwargs.items() if v is not None}
        try:
            if chat_id is not None:
                await send(chat_id=chat_id, **send_kwargs)
            else:
                await send(**send_kwargs)
        except TypeError:
            # fallback to positional signature
            if chat_id is not None:
                await send(chat_id, text, **{k: v for k, v in send_kwargs.items() if k != "text"})
            else:
                await send(text, **{k: v for k, v in send_kwargs.items() if k != "text"})
        return

    # Very basic splitting: window the text and prefer splitting at a newline,
    # then at a space; otherwise hard cut.
    chunks: list[str] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + max_length, n)
        window = text[start:end]
        split_at = window.rfind("\n")
        if split_at == -1:
            split_at = window.rfind(" ")
        if split_at == -1:
            chunk = text[start:end]
            start = end
        else:
            chunk = text[start : start + split_at]
            start = start + split_at + 1
        chunks.append(chunk)

    for chunk in chunks:
        if not chunk:
            continue
        send_kwargs = {"text": chunk.strip(), **kwargs}
        send_kwargs = {k: v for k, v in send_kwargs.items() if v is not None}
        try:
            if chat_id is not None:
                await send(chat_id=chat_id, **send_kwargs)
            else:
                await send(**send_kwargs)
        except TypeError:
            if chat_id is not None:
                await send(chat_id, chunk, **{k: v for k, v in send_kwargs.items() if k != "text"})
            else:
                await send(chunk, **{k: v for k, v in send_kwargs.items() if k != "text"})
