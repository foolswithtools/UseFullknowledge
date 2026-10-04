"""Parse the timestamps the schema accepts, on every Python the repo supports.

The schema pattern allows a trailing ``Z`` and git emits one, but
``datetime.fromisoformat`` only accepts it from Python 3.11. Debian stable and
macOS's system Python are older, so ``kb.py check`` crashed there.
"""

import datetime


def parse_timestamp(value):
    """Return an aware datetime for an ISO 8601 timestamp, ``Z`` included."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(value)
