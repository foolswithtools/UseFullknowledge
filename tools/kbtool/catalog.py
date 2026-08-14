"""Generate the three-tier catalog.

A single flat catalog measures ~1 MB / ~270k tokens at 1,000 documents - larger
than most agents' entire context budget, and gzip does not help because HTTP
decompresses before the agent sees it. So retrieval is tiered:

    llms.txt                    ~3 KB   how to query, and the trust rules
    catalog/index.json          ~17 KB  topic router; grows with TOPIC count
    catalog/topics/<topic>.json ~6 KB   full records for one topic
    kb/<type>/<id>.md                   the document

Tier 1 grows with topic count rather than corpus size and Tier 2 stays roughly
constant, so the cost of finding something does not rise as the corpus grows.

Everything here must be byte-identical across rebuilds: the catalog is a cache,
and a cache that changes without its source changing cannot be drift-checked.
That is why no wall-clock timestamp is written anywhere in the output.
"""

import json
import pathlib

from kbtool.frontmatter import ParseError, parse
from kbtool.shelflife import expires_on
from kbtool.validate import iter_documents

SITE_BASE = "https://clostaunau.github.io/UseFullknowledge"
RAW_BASE = "https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main"


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys + fixed separators + trailing newline: deterministic bytes.
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def _entry(rel, data, today):
    entry = {
        "id": data["id"],
        "title": data["title"],
        "type": data["type"],
        "summary": data["summary"],
        "tags": sorted(data.get("tags", [])),
        "review_status": data.get("review_status", "unreviewed"),
        "confidence_basis": sorted(data.get("confidence_basis", [])),
        "volatility": data.get("volatility"),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "created_by_tool": data.get("created_by_tool"),
        "created_by_model": data.get("created_by_model"),
        "md": rel,
        "html": rel[:-3] + ".html",
    }
    # A precomputed absolute date, never a `stale` boolean: staleness depends on
    # the day the question is asked, so the caller compares this to today.
    entry["expires_on"] = expires_on(
        data["created_at"], data["volatility"], data.get("review_reviewed_at")
    )
    if data.get("review_reviewer"):
        entry["review_reviewer"] = data["review_reviewer"]
        entry["review_reviewed_at"] = data.get("review_reviewed_at")
    if data.get("sources"):
        entry["sources"] = data["sources"]
    return entry


def collect(root, today):
    """Parse every valid document into a catalog entry, sorted by id."""
    entries = []
    for rel, text in iter_documents(root):
        try:
            doc = parse(text)
        except ParseError:
            continue
        required = ("id", "title", "type", "summary", "created_at", "updated_at", "volatility")
        if not all(key in doc.data for key in required):
            continue
        entries.append(_entry(rel, doc.data, today))
    return sorted(entries, key=lambda e: e["id"])


def build_catalog(root, out_dir, today):
    """Write llms.txt and the three catalog tiers into ``out_dir``."""
    out = pathlib.Path(out_dir)
    entries = collect(root, today)

    by_topic = {}
    for entry in entries:
        for tag in entry["tags"]:
            by_topic.setdefault(tag, []).append(entry)

    # Tier 2 - one shard per topic, full records.
    for topic, docs in by_topic.items():
        _write_json(
            out / "catalog" / "topics" / f"{topic}.json",
            {"topic": topic, "documents": sorted(docs, key=lambda e: e["id"])},
        )

    # Tier 1 - the router. Deliberately carries no summaries.
    topics = [
        {
            "topic": topic,
            "documents": len(docs),
            "verified": sum(1 for d in docs if d["review_status"] == "verified"),
            "shard": f"catalog/topics/{topic}.json",
        }
        for topic, docs in sorted(by_topic.items())
    ]
    _write_json(
        out / "catalog" / "index.json",
        {"documents": len(entries), "topics": topics},
    )

    # Fast path for the query this repo exists to answer.
    _write_json(
        out / "catalog" / "verified.json",
        {"documents": [e for e in entries if e["review_status"] == "verified"]},
    )

    (out / "llms.txt").write_text(_llms_txt(entries, topics), encoding="utf-8")
    return entries


def _llms_txt(entries, topics):
    verified = sum(1 for e in entries if e["review_status"] == "verified")
    return f"""\
# UseFullknowledge

> A provenance-tracked knowledge base of explainers, diagrams, snippets, prompts
> and research notes produced by AI tools. Every document records what created
> it, when, whether a human reviewed it, and when it should be re-checked.

{len(entries)} documents across {len(topics)} topics. {verified} verified by a human.

## How to find something

Do NOT crawl the site. Fetch these instead, in order:

1. `{SITE_BASE}/catalog/index.json`
   The topic router: every topic, how many documents it has, how many are
   verified, and the shard to fetch next. Grows with topic count, not corpus
   size.
2. `{SITE_BASE}/catalog/topics/<topic>.json`
   Full records for one topic: id, title, summary, provenance, review status,
   and `expires_on`.
3. The document itself, as rendered HTML (`html`) or raw markdown (`md`).

Raw markdown for any document:
`{RAW_BASE}/<md path from the catalog>`

## Trust rules

Each record carries:

- `review_status` - one of `unreviewed`, `reviewed`, `verified`. Only a human
  can set `verified`; this is enforced in CI, so an agent cannot self-promote.
- `confidence_basis` - structured evidence, not a self-assessed score. Values
  include `executed-verified`, `primary-source-cited`, `human-expert-review`,
  and `model-recall-only`.
- `expires_on` - an absolute date. A document is stale when today is past it.
  Staleness is deliberately NOT stored, because it depends on the day you ask.
- `sources` - present whenever `confidence_basis` claims a citation.

**To use only trustworthy context:** fetch `{SITE_BASE}/catalog/verified.json`
and keep records whose `expires_on` is later than today.

Documents of `type: note` are raw, unreviewed AI output. Do not treat them as
curated explanations.

## If you have a shell and a clone

    rg -l '^review_status: verified' kb/
    rg -l '^review_status: verified' -g '*kafka*' kb/
    rg '^summary: ' kb/explainer/

Frontmatter keys are flat and line-anchored on purpose, so `rg '^key: value'`
always works.
"""
