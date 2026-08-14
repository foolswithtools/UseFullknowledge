"""Compute staleness instead of storing it.

``expires_on`` and ``is_stale`` are derived at build time and never written back
into a document. Storing them would mean a daily write-back commit across the
whole corpus, and six tools resolving the resulting merge conflicts.

The clock starts at the last review, or at creation for anything never reviewed:
reviewing a document is what makes it trustworthy again.
"""

import datetime

# One required `volatility` enum drives every shelf life, so nobody has to
# hand-set a review-by date on a document about thermodynamics.
SHELF_LIFE_DAYS = {
    "ephemeral": 30,     # a release note, a today-only workaround
    "fast": 90,          # a library API, a cloud service's console flow
    "slow": 730,         # a protocol, an architectural pattern
    "evergreen": 3650,   # thermodynamics, sorting algorithms, C4 notation
}


def expires_on(created_at, volatility, reviewed_at=None):
    """Return the plain date on which this document should be re-reviewed."""
    if volatility not in SHELF_LIFE_DAYS:
        raise ValueError(f"unknown volatility {volatility!r}")

    anchor = reviewed_at or created_at
    start = datetime.datetime.fromisoformat(anchor).date()
    return (start + datetime.timedelta(days=SHELF_LIFE_DAYS[volatility])).isoformat()


def is_stale(expiry, today):
    """True when ``today`` is past ``expiry``. Both are plain ISO dates."""
    return datetime.date.fromisoformat(today) > datetime.date.fromisoformat(expiry)
