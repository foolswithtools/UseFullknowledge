# UseFullknowledge

A knowledge base of explainers, diagrams, code snippets, prompts and research
notes produced by AI tools — captured once, catalogued, and reusable instead of
regenerated.

Every document records **what created it, when, whether a human has reviewed it,
and when it should be re-checked.** That is the point of the repo: without it,
there is no way to tell whether a document is safe to feed to another AI as
context.

**Site:** https://clostaunau.github.io/UseFullknowledge/

## For humans

Browse the [site](https://clostaunau.github.io/UseFullknowledge/). It has
full-text search with filters for review status, content type and confidence.
Every page shows its provenance in a footer, so you can judge a document you
arrived at from a search engine without opening this repo.

In the repo, content lives in `kb/`, one directory per content type. The files
are plain markdown and read fine on github.com or in an editor.

## For AI agents

Start at **[`llms.txt`](https://clostaunau.github.io/UseFullknowledge/llms.txt)**.
It explains the catalog and the trust rules in about 3 KB.

Do not crawl the site. Fetch the catalog:

| Fetch | What it gives you |
|---|---|
| `catalog/index.json` | Topic router — every topic, its document count, how many are verified |
| `catalog/topics/<topic>.json` | Full records for one topic |
| `catalog/verified.json` | Only human-verified documents |

Getting from zero knowledge to a trust-filtered document costs about 10k tokens
and three fetches. Raw markdown for any document is fetchable directly:

```
https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/<md path>
```

To use only trustworthy context, take `catalog/verified.json` and keep records
whose `expires_on` is later than today.

With a clone and a shell, frontmatter keys are flat and line-anchored so grep
just works:

```bash
rg -l '^review_status: verified' kb/
rg -l '^review_status: verified' -g '*kafka*' kb/
```

## Contributing

If you are an AI tool, read **[`AGENTS.md`](AGENTS.md)** — it is the whole
contract, and it takes six decisions to file a document correctly.

```bash
python3 tools/kb.py new explainer "Kafka partition rebalancing" \
  --tool claude-code --model claude-opus-5
python3 tools/kb.py check
```

## Content types

| Type | For | Directory |
|---|---|---|
| `explainer` | Explaining a technology, science or concept | `kb/explainer/` |
| `diagram` | C4, sequence, ER and other diagrams | `kb/diagram/` |
| `snippet` | Runnable code and config samples | `kb/snippet/` |
| `prompt` | Reusable prompts, skills, agent configs | `kb/prompt/` |
| `note` | Raw, unpolished AI output | `kb/note/` |

Notes are visibly quarantined on the site so raw output is never mistaken for a
reviewed explainer.

## How it works

Markdown in `kb/` is the source of truth. HTML is generated, so the two cannot
drift. Nothing generated is ever committed — a committed index conflicts on
every concurrent push, and an agent resolving that conflict silently drops a
document.

```
kb/<type>/<slug>-<4hex>.md   source, and the only thing that matters
tools/kb.py                  check | build | new
schema/document.schema.json  the frontmatter contract
templates/                   one per content type
_site/                       generated; gitignored
```

The tooling is pure Python with no install step, using only `pyyaml`,
`jsonschema` and `markdown-it-py`. Node is used in CI alone, for the search
index and the mermaid syntax check.

```bash
python3 tools/kb.py check                              # validate every document
python3 tools/kb.py build                              # render the site
PYTHONPATH=tools python3 -m unittest discover -s tests  # 149 tests
```

CI validates before it publishes, so a document with missing or dishonest
provenance cannot reach the site.

## Design record

[`docs/design/architecture-comparison.md`](docs/design/architecture-comparison.md)
records the three candidate architectures, the measurements that decided between
them, and the trade-offs accepted. The seven expert positions behind it are in
[`docs/design/positions/`](docs/design/positions/).
