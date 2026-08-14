"""Document identity: stable slugs and collision-resistant short IDs.

Six AI tools that never talk to each other will eventually file the same topic
on the same day. The ``shortid`` mixes in the creating tool and the creation
timestamp so those two documents get different addresses without any tool
needing to look at what the others have already written.
"""

import hashlib
import re
import unicodedata

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(title):
    """Turn a human title into a lowercase-kebab slug."""
    decomposed = unicodedata.normalize("NFKD", title)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not cleaned:
        raise ValueError(f"title {title!r} contains no characters usable in a slug")
    return cleaned


def shortid(slug, tool, created_at):
    """Four hex chars derived from slug + creating tool + creation time."""
    seed = f"{slug}\x00{tool}\x00{created_at}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:4]


def make_id(title, tool, created_at):
    """The immutable document id: ``<slug>-<shortid>``."""
    slug = slugify(title)
    return f"{slug}-{shortid(slug, tool, created_at)}"
