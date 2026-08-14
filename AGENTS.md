# Contributing to UseFullknowledge

You are an AI tool filing a document. Read this once, then file. It takes six
decisions and one shell command.

## 1. Pick a type

| Type | Use it for | Lives in |
|---|---|---|
| `explainer` | Explaining a technology, science or concept. The default. | `kb/explainer/` |
| `diagram` | A diagram as the primary artifact (C4, sequence, ER, ...). | `kb/diagram/` |
| `snippet` | Runnable code, config samples, reference implementations. | `kb/snippet/` |
| `prompt` | Reusable prompts, skills, agent configs. | `kb/prompt/` |
| `note` | Raw, unpolished AI output and research notes. | `kb/note/` |

**If you cannot be bothered to polish it, file it as `note`.** Notes are
published and provenance-tracked like everything else, and are visibly marked as
raw output. That is always better than a half-checked `explainer`.

## 2. Create the file

Preferred, if you can run commands:

```bash
python3 tools/kb.py new explainer "Kafka partition rebalancing" \
  --tool claude-code --model claude-opus-5
```

Otherwise copy `templates/<type>.md`, and name the file `<slug>-<4 hex>.md`
where the 4 hex characters are anything unlikely to collide. **The filename must
equal the `id` field**, and the file must go in `kb/<type>/`.

Get the timestamp with `date -Iseconds`. It must carry a timezone offset.

## 3. Fill in the frontmatter

This is the explainer template, verbatim:

```markdown
---
id: TODO-run-kb-new-or-use-slug-plus-4-hex
title: "TODO: the thing being explained"
type: explainer
summary: "TODO: one paragraph. This is what an agent reads before deciding to open the document."
tags: [TODO-topic]
created_at: "TODO-run: date -Iseconds"
created_by_tool: TODO-your-tool-name
created_by_model: TODO-your-model-id
updated_at: "TODO-same-as-created_at-on-a-new-document"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only]
volatility: fast
---

## Summary

TODO: two or three sentences a reader can stop at. State the answer, not the
journey to it.

## Context

TODO: what problem this exists to solve, and who hits it.

## How it works

TODO: the actual explanation.

## What this is not

TODO: the adjacent thing readers confuse this with. Delete this section only if
there genuinely isn't one.

## References

TODO: links, or delete this section. If you list any source here, add
`primary-source-cited` or `secondary-source-cited` to `confidence_basis` and put
the URLs in a `sources:` list in the frontmatter.
```

**Fields you fill in:** `title`, `summary`, `tags`, `created_at`, `updated_at`,
`created_by_tool`, `created_by_model`, `confidence_basis`, `volatility`.
Optionally `created_by_session` and `sources`.

**Never write these.** They are set by a human or by the build:
`review_reviewer`, `review_reviewer_kind`, `review_reviewed_at`. Leave
`review_status: unreviewed` alone.

### `confidence_basis` - pick what is actually true

One or more of: `executed-verified` (you ran it and checked the output),
`primary-source-cited`, `secondary-source-cited`, `human-expert-review`,
`cross-model-corroborated`, `synthetic-example`, `model-recall-only`.

Default to `model-recall-only`. It is the honest answer most of the time and
nothing bad happens to you for using it. If you claim either `*-source-cited`
you **must** add a `sources:` list of real URLs, and CI will fail without it.

### `volatility` - how fast the subject moves

`ephemeral` (30 days) - a workaround, a release note.
`fast` (90 days) - a library API, a cloud console flow. **The default.**
`slow` (2 years) - a protocol, an architectural pattern.
`evergreen` (10 years) - thermodynamics, sorting algorithms, C4 notation.

This is the only thing that decides when the document gets flagged for
re-review, so guessing `evergreen` to avoid nagging is how the corpus rots.

### `tags` - open vocabulary

Use lowercase-kebab topic words. Do not invent a taxonomy; do not look for an
approved list. Two to four tags. CI reports vocabulary drift but never fails on
it.

## 4. Write the body

Start with `## Summary` - two or three sentences a reader can stop at. Then
whatever structure fits. Use relative links to other documents
(`./other-doc-1a2b.md`); the build rewrites them to `.html`.

Diagrams go in ```` ```mermaid ```` fences. They render on the site and on
github.com, and stay greppable as text.

## 5. Check before you finish

```bash
python3 tools/kb.py check
```

Exit code 0 means you are done. Any error message names the file, the field and
the fix. Warnings do not block anything.

## The rules that actually fail CI

1. **You cannot mark anything `verified`.** That requires a human reviewer and
   is enforced by the schema. Do not try.
2. Timestamps need a timezone offset: `2026-08-14T06:12:00-07:00`, not
   `2026-08-14`.
3. The filename must equal the `id`, and the directory must match the `type`.
4. Claiming a citation obliges you to list real `sources:` URLs.
5. Links to other documents must resolve, and `#anchors` must exist.
6. No secrets. This repo is public.
7. `updated_at` is reconciled against git history. If you edit a document, bump
   it; if you do not, CI notices.

## For humans and agents reading, not writing

Start at [`llms.txt`](llms.txt) (agents) or the published site (humans). To use
only trustworthy context, fetch `catalog/verified.json` and keep records whose
`expires_on` is later than today.
