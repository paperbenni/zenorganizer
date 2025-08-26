from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_time() -> datetime:
    """Get current datetime in Europe/Berlin timezone."""
    return datetime.now(tz=ZoneInfo("Europe/Berlin"))
