---
id: validate-iso-8601-timestamps-with-a-timezone-offset-b64f
title: "Validate ISO 8601 timestamps with a timezone offset"
type: snippet
summary: "A regex plus a parse check that accepts only ISO 8601 timestamps carrying an explicit timezone offset, for use where JSON Schema's format: date-time silently accepts anything."
tags: [python, validation, timestamps]
lang: python
lang_version: "3.12"
created_at: "2026-08-14T14:21:37+00:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-08-14T14:21:37+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [executed-verified, primary-source-cited]
sources:
  - "https://python-jsonschema.readthedocs.io/en/latest/validate/#validating-formats"
  - "https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat"
volatility: slow
---

## Summary

Accepts a timestamp only if it is ISO 8601 **and** carries a timezone offset.
Written because `jsonschema`'s `format: date-time` is a no-op unless the
optional `rfc3339-validator` package is installed — with it absent, the string
`2026-08-14` validates happily as a date-time, and a schema that looks like it
requires an offset requires nothing at all.

## Snippet

```python
import datetime
import re

# jsonschema's `format: date-time` is a silent no-op unless rfc3339-validator is
# installed, so anything that must have an offset needs an explicit pattern.
ISO_WITH_OFFSET = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def is_iso_with_offset(value):
    """True when `value` is an ISO 8601 timestamp carrying a timezone offset."""
    if not isinstance(value, str) or not ISO_WITH_OFFSET.match(value):
        return False
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None
```

## Usage

The regex alone would accept `2026-13-01T00:00:00Z`, so the parse is not
redundant: it rejects impossible dates that match the shape. The `tzinfo` check
is what actually enforces the offset.

Executed on Python 3.12.3 with these results:

| Input | Result |
|---|---|
| `2026-08-14T06:12:00-07:00` | accepted |
| `2026-08-14T06:12:00Z` | accepted |
| `2026-08-14T06:12:00.123456+00:00` | accepted |
| `2026-08-14T06:12:00` | rejected — no offset |
| `2026-08-14` | rejected — date only |
| `2026-08-14 06:12:00-07:00` | rejected — space instead of `T` |
| `2026-13-01T00:00:00Z` | rejected — month 13 |
| `not a timestamp` | rejected |
| `None` | rejected |

As a JSON Schema `pattern`, drop the `re` anchors and inline it:

```json
{ "type": "string",
  "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$" }
```

## Caveats

- `fromisoformat` accepts the full ISO 8601 grammar from Python 3.11 onward,
  including `Z`. On 3.10 and earlier it rejects `Z`, so the parse step would
  fail on input the regex accepts.
- Offsets are not validated for plausibility: `+99:00` matches the pattern and
  `fromisoformat` rejects it, but only because the offset exceeds 24 hours.
- Leap seconds (`:60`) are rejected. That is usually what you want.
- This says nothing about whether the offset is *correct*, only that one is
  present. A tool writing `+00:00` for a local time in Denver produces a
  well-formed lie.
