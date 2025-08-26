from datetime import datetime

import pytz


def get_current_time() -> datetime:
    """Get current datetime in Europe/Berlin timezone."""
    return datetime.now(pytz.timezone("Europe/Berlin"))
