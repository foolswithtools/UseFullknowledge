# Taxonomy and conventions

The definitive statement of how content is organized, named, addressed and
tagged. `AGENTS.md` is the short imperative version for contributors; this is
the reasoning behind it.

## The organizing principle

**The mandatory directory axis is the least ambiguous axis, not the most
interesting one.**

Six AI tools that never talk to each other will classify the same document
differently about half the time. Any classification that lands in the *path*
turns that disagreement into a different URL — and a broken link. So the path
carries only the one thing every tool agrees on (what kind of artifact this is),
and everything genuinely contestable — subject, topic, domain — lives in
frontmatter where being wrong costs one line of YAML instead of an address.

```
kb/<type>/<slug>-<4hex>.md
```

Five type shelves, flat, no topic subdirectories:

| Type | For |
|---|---|
| `explainer` | Explaining a technology, science or concept. The bulk. |
| `diagram` | A diagram as the primary artifact |
| `snippet` | Runnable code, config samples, reference implementations |
| `prompt` | Reusable prompts, skills, agent configs |
| `note` | Raw, unpolished AI output and research notes |

### Why not a subject hierarchy

`kb/distributed-systems/kafka/...` reads beautifully until the first document
that is *"Kafka on Kubernetes for client Acme"*, which has three equally
defensible homes. Whichever is chosen, two future searches look in the wrong
place. A controlled domain vocabulary makes it worse rather than better: a
foreign agent whose PR is rejected for using an unknown domain does not open a
vocabulary PR, it jams the document into the nearest existing directory. Within
months the largest directory is `misc/` and the taxonomy is decorative.

### Why not a topic directory as well

Measured at 1,000 documents: every ripgrep query lands in 12–17 ms regardless of
layout. A topic directory bought about 2 ms — noise — while making every topic
reclassification a file move, and therefore a broken URL. Putting the topic slug
in the *filename* gives the same `rg -g '*kafka*'` prefilter with none of that.

### When to revisit

If one shelf passes **150 files**, add a single closed-list domain level chosen
from the actual topic census — not from a vocabulary guessed in advance.

## Naming and addressing

- Filename: `<slug>-<4hex>.md`, lowercase kebab.
- **The filename must equal the `id`.** CI enforces it.
- The 4 hex characters derive from slug + creating tool + creation timestamp, so
  two tools filing the same title on the same day get different addresses
  without either knowing the other exists.
- The `id` is immutable; the path may change. Old ids go in `aliases`.

The URL rule is invertible in both directions:

```
kb/explainer/foo-7f3a.md  ->  /kb/explainer/foo-7f3a.html   rendered
                          ->  /kb/explainer/foo-7f3a.md     source
```

## Tags are open, and stay open

Lowercase-kebab, two to four per document, no approved list. CI *reports*
vocabulary drift; it never fails on it. A tag vocabulary that fails CI is a
vocabulary agents route around by picking a wrong-but-existing tag — which is a
quality failure the validator cannot see. Roughly 240–280 tags where 200 would
do is the accepted cost.

**A document belonging to three topics gets three tags** and appears in three
catalog shards. There is no other mechanism, and none is needed. Symlinks are
specifically disqualified: `raw.githubusercontent.com` serves the path, not the
target's content.

## Frontmatter is flat, always

Never nested. This is not style.

Six tools produce six indentation habits that all parse to identical YAML — so
the validator passes all six — but the query an agent actually writes,
`rg '^review_status: verified'`, finds **1 of 6** against nested frontmatter and
**6 of 6** against flat. Nested returns "no verified documents exist" with exit
code 1 and no error, which is a silent false negative on the single most
important query in the corpus.

Nesting's usual justification — conditional requirements and per-type extensions
in JSON Schema — was tested and does not hold: flat keys express all of them via
`if`/`then` on `type`, with better error messages.

`format: date-time`, `format: uri` and `format: email` are **silent no-ops**
here, because `jsonschema` does not enforce formats without `rfc3339-validator`.
Every constraint in `schema/document.schema.json` is a `pattern` for that reason.

## The trust lifecycle

`unreviewed` → `reviewed` → `verified`. Everything starts `unreviewed`, and
forgetting to touch it can therefore only ever *lose* trust, never gain it.

**Only a human can set `verified`.** The schema requires
`review_reviewer_kind: human`, so an agent cannot self-promote. Review fields are
absent from the templates entirely rather than present-and-blank — a template is
the strongest prompt in the system, and any key present in one will receive a
value.

`confidence_basis` replaces a self-assessed confidence score, which from a
language model is close to worthless. It is a closed enum of evidence kinds, and
claiming `primary-source-cited` or `secondary-source-cited` obliges you to list
real `sources:` URLs or fail CI.

`updated_at` is a *claim*; git history is the *fact*. The validator reconciles
them and fails when they diverge by more than 24 hours in either direction.

## Staleness is computed, never stored

One required `volatility` enum drives one shelf-life table:

| Volatility | Shelf life | Example |
|---|---|---|
| `ephemeral` | 30 days | a workaround, a release note |
| `fast` | 90 days | a library API, a cloud console flow |
| `slow` | 2 years | a protocol, an architectural pattern, a notation |
| `evergreen` | 10 years | thermodynamics, sorting algorithms, information theory |

Judge the **advice**, not the subject. A clean-room test of the contract caught
this: a document about C4 notation (stable) whose guidance depends on which
renderer and model you use (not stable) is `fast`. Listing "C4 notation" as an
evergreen example invited exactly the inflation the rule warns against.

`expires_on` is computed at build time from the last review, or from creation if
never reviewed. **`stale` is never stored** — it depends on the day you ask, so
storing it would mean a daily write-back commit across the whole corpus and six
tools resolving the resulting conflicts. The catalog publishes the absolute date;
the caller compares it to today.

Staleness is a **warning**, never an error. Time passing is not a defect in a
commit, and a validator that turns CI red on a day nobody committed is one
people learn to bypass.

## Nothing generated is ever committed

`_site/` is gitignored. This was measured, not assumed: two tools branching from
the same base and each regenerating the catalog produce

```
CONFLICT (content): Merge conflict in catalog.json
```

while **both markdown files merge cleanly**. The source is conflict-free; only
the derivative conflicts, and an agent resolving that block picks a side and
drops a document. A committed SQLite index is worse — `Cannot merge binary
files`, and resolving it lost a row outright.

The rule that follows: **conventions are the contract, the catalog is a cache.**
If they ever disagree, the documents win and CI fails.

## Diagrams

Mermaid, in ```` ```mermaid ```` fences, using the native `C4Context`/`C4Container`
grammar for C4 rather than a flowchart imitation. `Container(booking, "Booking
Service", "Python 3.12, FastAPI", ...)` keeps the corpus queryable by ripgrep
alone, and the fence renders natively on github.com.

Renders are **not** committed — the same rule as HTML, so there is no second copy
to drift. Mermaid is vendored and self-hosted (`vendor/mermaid.min.js`), loaded
only on pages that contain a diagram, so a published page never calls an external
runtime.

C4 levels are linked by a shared `subject_system` slug:

```bash
rg -l 'subject_system: acme-booking' kb/
```

Build-time pre-rendering to static SVG is deliberately deferred. It costs 1.07 GB
of toolchain, cannot run on the author's machine at all, and the page contract is
designed so it can be added later without changing document format.
