"""Validate flat frontmatter against the JSON Schema.

Errors are returned as ``"<path>: <message>"`` strings so both a human and a
contributing agent can act on them without opening the schema.
"""

import functools
import json
import pathlib

from jsonschema import Draft202012Validator

SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[2] / "schema" / "document.schema.json"


@functools.lru_cache(maxsize=1)
def _validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _describe(error):
    path = error.json_path
    # A failed `if/then` reports at the object root; name the missing key so the
    # message still tells a contributor which field to add.
    return f"{path}: {error.message}"


def validate(data):
    """Return a sorted list of human-readable problems. Empty means valid."""
    problems = [_describe(e) for e in _validator().iter_errors(data)]
    return sorted(set(problems))
