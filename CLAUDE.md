# CLAUDE.md

This repository is a provenance-tracked knowledge base.

**To file a document, follow [`AGENTS.md`](AGENTS.md).** It is the single
contribution contract and it applies to Claude Code exactly as it applies to
every other tool. Do not invent a different filing convention.

## Working in this repo

- Tooling is pure Python with no install step: `python3 tools/kb.py check`,
  `python3 tools/kb.py build`, `python3 tools/kb.py new <type> "<title>"`.
- Tests: `PYTHONPATH=tools python3 -m unittest discover -s tests`.
- Dependencies are limited to what ships in Debian's `python3-*` packages
  (`pyyaml`, `jsonschema`, `markdown-it-py`). Do not add a dependency without
  saying why the stdlib will not do.
- `_site/` is generated output. Never commit it, and never hand-edit anything
  the build produces - fix the source or the build script instead.
- Frontmatter keys are **flat, never nested**. Nested YAML makes
  `rg '^review_status: verified'` return zero results with no error, which is a
  silent false negative on the most important query in the corpus.

## Design record

`docs/design/architecture-comparison.md` records the three candidate
architectures, the measurements behind the decision, and why this one won.
Read it before proposing a structural change.
