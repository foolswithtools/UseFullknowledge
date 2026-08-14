"""Parse YAML frontmatter without letting YAML's conveniences corrupt provenance.

Three YAML behaviours are actively dangerous for this repo and are disabled here:

* Unquoted ISO timestamps resolve to ``datetime`` objects and re-emit with a
  space instead of ``T``, so a timezone-offset check would inspect text the
  author never wrote. Timestamps stay strings.
* Duplicate keys silently override, which can overwrite provenance with a later
  value. Duplicates raise.
* YAML 1.1 resolves bare ``no``/``on``/``off`` to booleans, so a tag literally
  named ``no`` would become ``False`` and vanish from the catalog. Only
  ``true``/``false`` resolve as booleans.
"""

import re

import yaml

FENCE = "---"


class ParseError(Exception):
    """Raised when a document's frontmatter cannot be trusted."""


class _KbLoader(yaml.SafeLoader):
    """SafeLoader with the three unsafe-for-provenance behaviours removed."""


# Timestamps must survive as the exact text the author wrote, and YAML 1.1's
# yes/no/on/off bool set must go before a restricted one can replace it.
_DROPPED = {"tag:yaml.org,2002:timestamp", "tag:yaml.org,2002:bool"}
_KbLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag not in _DROPPED]
    for key, resolvers in _KbLoader.yaml_implicit_resolvers.items()
}

# Restrict YAML 1.1's bool set to true/false so tags like `no` stay strings.
for _ch in list("tTfF"):
    _KbLoader.yaml_implicit_resolvers.setdefault(_ch, [])
_KbLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def _no_duplicates(loader, node, deep=False):
    seen = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ParseError(
                f"duplicate key {key!r} in frontmatter "
                f"(line {key_node.start_mark.line + 1} repeats line {seen[key]}); "
                f"remove one - a duplicate silently overrides the first value"
            )
        seen[key] = key_node.start_mark.line + 1
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_KbLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


class Document:
    """Parsed frontmatter plus the body, with line numbers for error messages."""

    def __init__(self, data, body, lines, raw_frontmatter):
        self.data = data
        self.body = body
        self._lines = lines
        self.raw_frontmatter = raw_frontmatter

    def line_of(self, key):
        """1-based line number of ``key`` in the file, or None if absent."""
        return self._lines.get(key)


def parse(text):
    """Parse a document. Raises ParseError if the frontmatter is untrustworthy."""
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n")

    if not text.startswith(FENCE + "\n"):
        raise ParseError(
            "no frontmatter: the file must begin with a line containing exactly '---'"
        )

    rest = text[len(FENCE) + 1 :]
    end = rest.find("\n" + FENCE)
    if end == -1:
        raise ParseError(
            "unterminated frontmatter: no closing '---' line was found"
        )

    raw = rest[:end]
    body = rest[end + len(FENCE) + 1 :].lstrip("\n")

    try:
        loaded = yaml.load(raw, Loader=_KbLoader)
    except ParseError:
        raise
    except yaml.YAMLError as exc:
        raise ParseError(f"frontmatter is not valid YAML: {exc}") from exc

    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ParseError("frontmatter must be a mapping of key: value pairs")

    # Frontmatter starts on line 2 of the file (line 1 is the opening fence).
    lines = {}
    for offset, line in enumerate(raw.split("\n")):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
        if match and match.group(1) not in lines:
            lines[match.group(1)] = offset + 2

    return Document(loaded, body, lines, raw)
