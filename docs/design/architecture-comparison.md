# Knowledge Base Architecture — Three Candidates, Scored

**Status:** Phase 1 deliverable. Awaiting decision.
**Date:** 2026-08-14
**Inputs:** seven expert positions in [`positions/`](positions/), plus direct measurement on this machine.

---

## How to read this

Three architectures that a reasonable person could pick between for different reasons.
They are not variations on one idea: they differ in **organizing structure**, **index
strategy**, **retrieval model**, and **how much machinery has to keep working**.

Everything numeric here was **measured**, not estimated. Commands are shown in
[Appendix A](#appendix-a--measurements). Where evidence was inconclusive, it says so.

---

## What the measurements already settled

Five questions turned out to have empirical answers. These are **not** points of
difference between the candidates — they are constraints all three must respect, and
two of them killed a design that looked reasonable on paper.

### 1. Frontmatter must be flat. This one is not close.

The most important query in the system is *"give me only `verified` documents about X."*
I wrote the same document six ways — the six indentation habits six uncoordinated tools
would produce — and confirmed **all six parse to identical YAML**. A validator passes all
six. Then I ran the query an agent would actually write:

| Frontmatter shape | Docs found by the agent's query | Failure mode |
|---|---|---|
| **Nested** (`review:` → `status:`) | **1 of 6** | silent — `exit=1`, no error |
| **Flat** (`review_status:`) | **6 of 6** | none |

Nested YAML returns *"no verified documents exist"* rather than an error. An agent cannot
tell a true negative from a broken query. That is the single most dangerous outcome in a
system whose entire purpose is trust filtering.

The metadata expert's argument for nesting was that it enables conditional requirements
and per-type extensions in JSON Schema. **I tested that claim and it is false.** Flat keys
express every one of them via `if`/`then` on `type` — including the load-bearing
"`verified` requires a *human* reviewer" rule — and produce *better* error messages:

```
'review_reviewer' is a required property
$.review_reviewer_kind: 'human' was expected
$.created_at: '2026-08-14' does not match '^\d{4}-\d{2}-\d{2}T...'
```

Nesting loses 5/6 recall and gains nothing. **Verdict: flat, in all three candidates.**

### 2. `format:` in JSON Schema is a silent no-op here

`format: date-time`, `format: uri`, and `format: email` all **accept invalid input
silently** — `rfc3339-validator` is absent, and jsonschema does not enforce formats
without it. `2026-08-14` validates as a timestamp. Every format constraint must be a
`pattern` regex, or the timezone requirement is unenforced fiction.

### 3. Never commit a generated artifact

Two tools branching from the same base, each adding a document and regenerating the index:

```
Auto-merging catalog.json
CONFLICT (content): Merge conflict in catalog.json
```

But — and this is the whole argument — **both markdown files merged cleanly.** The source
is conflict-free. Only the derived artifact conflicts, and an agent resolving that
`<<<<<<<` block picks a side and silently drops a document.

The same test with a committed SQLite index is worse:

```
warning: Cannot merge binary files: idx.db
```

Resolving it **lost a row outright.** Binary indexes cannot be merged at all — data loss
is guaranteed, not risked. This kills committed-SQLite as an index strategy (Candidate C).

### 4. At 1,000 documents, path depth buys nothing measurable

| Layout | Query time (best of 5) |
|---|---|
| Flat `kb/<type>/<slug>.md` — full scan | 14 ms |
| Topic subdirectory — full scan | 17 ms |
| Topic subdirectory + `-g '*kafka*'` prefilter | 15 ms |
| **Flat, slug in filename + `-g '*kafka*'`** | **12 ms** ← fastest |

The retrieval expert wanted a topic directory for a free glob prefilter. **Putting the
topic slug in the filename delivers that prefilter without the directory level** — and is
marginally faster. The directory earns nothing and costs a file move (a broken URL) every
time a topic is reclassified.

### 5. Python-only, zero installs

`markdown-it-py 3.0.0`, `PyYAML 6.0.1` (with `CSafeLoader`), and `jsonschema 4.10.3` are
already present in system `dist-packages`. It renders CommonMark + tables and leaves
```` ```mermaid ```` fences as `<pre><code class="language-mermaid">` — exactly the hook a
diagram renderer needs. **No `pip install`, no `npm ci`, no lockfile.** A full build of
1,000 documents measured **5.15 s**, so incremental builds are YAGNI until ~6,000 docs.

---

## Candidate A — "Grep Substrate"

> *Minimum machinery. If the build script dies, almost nothing is lost.*

**Structure.** `kb/<type>/<slug>.md`. Five flat shelves: `explainer/`, `diagram/`,
`snippet/`, `prompt/`, `note/`. Topic lives only in frontmatter.

**Index.** One generated `catalog.json` (flat array) + `llms.txt`. Built into `_site/`,
never committed.

**Agent retrieval.** ripgrep over conventions is primary. The catalog is a convenience.

**Human retrieval.** Generated index and tag pages. **No full-text search.**

**Diagrams.** Mermaid fences, vendored client-side `mermaid.min.js`. Nothing pre-rendered.

**Build.** Python, ~400 lines, stdlib + preinstalled libs. Actions artifact deploy,
validate gates deploy.

### Worked example

```
kb/explainer/kafka-partition-rebalancing.md
kb/diagram/acme-booking-c4-container.md
```

```yaml
---
id: kafka-partition-rebalancing
title: "Kafka partition rebalancing"
type: explainer
summary: "How Kafka reassigns partitions across consumer group members."
tags: [kafka, consumer-groups, distributed-systems]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-08-14T06:12:00-07:00"
review_status: unreviewed
confidence_basis: [primary-source-cited]
volatility: fast
sources: ["https://kafka.apache.org/documentation/#basic_ops_consumer_group"]
---
```

**A document belonging to three topics:** three tags. No mechanism needed — this is the
one thing flat-plus-facets handles for free.

### Why it would be a good choice

- **Survives neglect better than anything else here.** Six months untouched costs
  literally nothing: the documents are the system.
- Lowest contribution friction — one directory decision, and it's the one an agent gets
  right (content type is self-evident; topic is not).
- Smallest build surface, so the fewest things can break.
- Fastest to get running and the easiest to reason about at 3am.

### Why it would be a bad choice

- **Serves only one of three agent access modes well.** An HTTPS-only agent has no cheap
  entry point: the flat catalog measures **1.08 MB / ~270k tokens** at 1,000 docs — larger
  than most agents' entire context budget, and gzip does not help because HTTP
  decompresses before the agent sees it.
- **No human search.** At 1,000 docs across 200 unrelated topics, browsing tag pages is a
  poor substitute, and this is the failure the user will feel first.
- ~700 explainers in one directory: GitHub's file browser paginates, and `ls` becomes
  useless. Navigable only via generated pages — which is exactly the thing this candidate
  refuses to depend on.

### If maintenance lapses six months

Nearly nothing breaks. Stale `review_by` dates accumulate; the site keeps serving; grep
keeps working. **Best-in-class here.**

---

## Candidate B — "Tiered Catalog" *(recommended)*

> *Three independent retrieval paths, each degrading into the next.*

**Structure.** `kb/<type>/<topic-slug>-<shortid>.md`. Same five flat shelves as A, but the
topic slug is in the **filename**, buying the free `-g` glob prefilter measured above
without a directory level. A 4-char `shortid` makes same-day filename collisions between
two tools structurally impossible.

**Frontmatter.** Flat, ~10 required fields. Immutable `id` decoupled from path; renames
leave an alias entry so links survive.

**Index.** A **three-tier** generated catalog, sized so every tier is one comfortable read:

| Tier | Artifact | Size | Grows with |
|---|---|---|---|
| 0 | `llms.txt` | ~3 KB | fixed |
| 1 | `catalog/index.json` (topic router) | ~17 KB | **topic** count |
| 2 | `catalog/topics/<topic>.json` | ~6 KB | fixed (~6 KB regardless of corpus) |
| 3 | the document | ~13 KB | — |

Measured cost for an HTTPS-only agent going from zero knowledge to a trust-filtered
document: **~10k tokens, three fetches.** Against ~270k tokens for the flat catalog — a
27× reduction that *improves* as the corpus grows, because Tier 1 tracks topic count and
Tier 2 is size-stable.

**Agent retrieval.** Tiered catalog for HTTPS-only and IDE agents; ripgrep conventions as
the always-works substrate underneath. The governing rule: **conventions are the contract,
the catalog is a cache — if they disagree, the documents win and CI fails.**

**Human retrieval.** Generated nav + **Pagefind** search with facets on `review_status`,
`type`, `confidence`. ~125 KB baseline, ~31 KB per query — versus lunr's 18.2 MB index
downloaded before the first keystroke.

**Diagrams.** Mermaid source in fences, client-side vendored mermaid (~325 KB gzipped for
a C4 page via lazy-loaded ESM). The page contract is designed so **build-time pre-render
can be added later without changing document format** — deliberately deferred, because
the prerender toolchain costs 1.07 GB and cannot run on this machine at all.

**Build.** Python for validate/catalog/render. Node used **only** in CI, **only** for
Pagefind, and the build degrades cleanly if it is absent. Actions artifact deploy;
validation gates deploy; catalog regenerated and drift-checked with `git diff --exit-code`.

### Worked example

```
kb/explainer/kafka-partition-rebalancing-7f3a.md
kb/diagram/acme-booking-c4-container-2b91.md
```

```yaml
---
id: kafka-partition-rebalancing-7f3a
title: "Kafka partition rebalancing"
type: explainer
summary: >-
  How Kafka reassigns partitions across consumer group members, why
  stop-the-world rebalances stall consumers, and what cooperative sticky
  assignment changes.
tags: [kafka, consumer-groups, distributed-systems]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
created_by_session: "sess_01H9XKQ2"
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [primary-source-cited]
volatility: fast
sources: ["https://kafka.apache.org/documentation/#basic_ops_consumer_group"]
---
```

The C4 diagram, same shelf pattern, with type extensions the validator requires only for
`type: diagram`:

```yaml
---
id: acme-booking-c4-container-2b91
title: "Acme Booking — C4 Container diagram"
type: diagram
summary: "Containers of the Acme booking platform and their runtime dependencies."
tags: [c4, architecture, acme-booking]
diagram_notation: mermaid
c4_level: container
subject_system: acme-booking
created_at: "2026-08-14T06:20:00-07:00"
created_by_tool: cursor
created_by_model: gpt-5
updated_at: "2026-08-14T06:20:00-07:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [human-expert-review]
volatility: slow
---
```

**Derived at build, never stored:** `expires_on` (from `volatility`), `is_stale`,
`git_updated_at`, `revision_count`. Storing them would mean daily write-back commits and
six-way merge conflicts.

**A document belonging to three topics:** one canonical file, three tags, and it appears
in three Tier-2 shards. Measured duplication overhead: ~11%.

### Why it would be a good choice

- **The only candidate that serves all three agent access modes** (shell clone, HTTPS-only,
  IDE file tools) with the *same* trust filter.
- Trust filtering is genuinely cheap and genuinely correct — the thing the user says is
  the whole point.
- Human search that actually works on a phone, for ~4 KB of facet index.
- Degrades in a defined order: catalog → conventions → plain markdown on github.com.

### Why it would be a bad choice

- **Redundancy means two places to be wrong.** Trust fields live in frontmatter *and* the
  catalog. A validator bug or a half-finished build could publish a catalog asserting
  `verified` for a document that is not. Mitigated by a mandatory catalog-vs-source diff
  in CI — but this is the failure mode most likely to bite.
- **The topic router is a vocabulary bottleneck.** Everything rests on an agent matching
  its question to one of ~200 slugs. A wrong guess yields *plausible but incorrect*
  results — the most dangerous kind of retrieval miss. Aliases help, but only reactively.
- **Cross-topic synthesis is served badly.** *"What do we know about consistency across
  all topics?"* means scanning 200 shards or falling back to grep. This design optimizes
  hard for lookup over synthesis.
- Most moving parts of the three. It is the most *machinery* that must keep working.

### If maintenance lapses six months

The site keeps serving (last successful deploy stays live). Stale docs accumulate and are
flagged, not hidden. Real rot risks: a deprecated Actions version failing the workflow, and
Pagefind drifting. Because the catalog is generated per-build and never committed, it
cannot silently drift — it is either rebuilt or absent. **Middle of the pack.**

---

## Candidate C — "Subject Hierarchy + Rich Semantics"

> *A real library: semantically correct, deeply browsable, richest metadata.*

**Structure.** Subject-first `kb/<domain>/<topic>/<type>-<slug>.md`, e.g.
`kb/distributed-systems/kafka/explainer-partition-rebalancing.md`. A controlled vocabulary
of ~12 domains in `_meta/domains.yml`. Artifacts about one subject colocate.

**Frontmatter.** Nested, PROV-O-aligned, with `.prov.jsonld` sidecars.

**Index.** Per-directory `README.md` files (browsable natively on github.com) plus a
committed **SQLite FTS5** database.

**Diagrams.** Committed SVG beside source, consistency enforced by a `source_sha256` gate.

### Worked example

```
kb/distributed-systems/kafka/explainer-partition-rebalancing.md
kb/architecture/acme-booking/diagram-c4-container.md
```

### Why it would be a good choice

- **Best human browsing without any build.** The subject tree is navigable on github.com
  as-is, and per-directory READMEs mean the repo explains itself in a plain file browser.
- Colocation is genuinely pleasant: everything about Kafka in one place.
- Richest provenance semantics; the only candidate that could answer real graph questions
  ("what did this session produce?").
- SQL gives exact structured queries — measured **1.2 ms** for a trust-filtered FTS5 query.

### Why it would be a bad choice

- **The committed index is fatal.** 4.35 MB binary; git reports `Cannot merge binary
  files`; resolving a conflict **lost a row in testing**. At ~300 commits/year that is
  **~1.27 GB/year** of undeltifiable blob in a repo whose text corpus is ~4 MB. And an
  HTTPS-only agent cannot use it at all — there is no `sqlite3` CLI on this machine, and
  no way to query a binary over `raw.githubusercontent.com`.
- **The controlled vocabulary is the thing that will actually kill it.** A foreign agent
  needing a domain that doesn't exist gets its PR rejected by CI. Its realistic behavior is
  not to open a vocabulary PR — it is to jam the document into the nearest existing domain.
  Within months `misc/` is the largest directory and the taxonomy is decorative.
- **The taxonomy collapses on real documents.** *"Kafka on Kubernetes for client Acme"* has
  three equally defensible homes. Whichever is chosen, two future searches look in the
  wrong place — and unlike a tag, the choice is baked into the URL.
- Nested frontmatter costs 5/6 grep recall (measured above).
- Highest contribution friction: domain + topic + type + slug, where domain and topic are
  exactly the decisions agents fabricate.

### If maintenance lapses six months

**Worst of the three.** The SQLite index goes stale and is silently wrong rather than
absent; per-directory READMEs drift from directory contents; the domain vocabulary
ossifies while content piles into `misc/`. Recovery requires a re-filing pass no one will do.

---

## The skeptic's objections, and the answers

Stress-tested at **1,000 documents / 200 topics / 6 tools that never talk.**

| # | Objection | Severity | Hits | Answer |
|---|---|---|---|---|
| 1 | Flat catalog blows the context window (270k tokens) | **FATAL** | A | Unanswered in A — this is A's disqualifying flaw for HTTPS agents. B's tiering fixes it (~10k tokens). |
| 2 | Committed binary index causes silent data loss | **FATAL** | C | Unanswerable. Measured row loss on merge. Kills C's index strategy outright. |
| 3 | Controlled vocabulary rejected → agent dumps into `misc/` | **FATAL** | C | No defense exists that a foreign agent will honor. B avoids it: tags are open, with CI *reporting* drift rather than failing on it. |
| 4 | Nested frontmatter silently returns 0 results | **FATAL** | C | Fixed by mandating flat keys everywhere (measured 6/6 vs 1/6). |
| 5 | Two tools, same filename, same day | SERIOUS | A, C | B's 4-char `shortid` makes collision structurally impossible. A and C rely on slug uniqueness and will collide. |
| 6 | Generated index conflicts on concurrent pushes | SERIOUS | all | Never commit generated artifacts; build into `_site/`. Verified: source markdown merges cleanly even when the index conflicts. |
| 7 | A document ends up `verified` without a human reading it | SERIOUS | all | Schema rule: `review_status: verified` requires `review_reviewer_kind: human` — **tested, fails correctly**. Reinforced by omitting review fields from templates entirely, so no agent is ever prompted for a value it would invent. |
| 8 | `updated_at` drifts from reality when an agent forgets to bump it | SERIOUS | all | Frontmatter is a *claim*; git is the *fact*. Validator reconciles against `git log` and fails on >24h divergence. Catalog publishes both. |
| 9 | 700 files in one directory | ANNOYANCE | A, B | Real but cosmetic: the browsing surface is generated. Trigger to revisit: >150 files in one shelf. |
| 10 | Stale docs turn CI red on a day nobody committed | ANNOYANCE | all | Staleness is a **WARNING**, never an error. Time passing is not a commit defect — and a validator that cries wolf gets `--no-verify`'d to death. |

**What kills the project regardless of candidate:** none of this matters if filing a
document is more expensive than regenerating it. The contribution path has to be cheaper
than asking the model again — which is why the friction budget (27 decisions cut to 6) and
the "never ask an agent for a value it will fabricate" rule matter more than any indexing
decision here. **The runner-up risk:** the user never actually reviews anything, so the
corpus is 100% `unreviewed` and the trust lifecycle is decorative. Worth deciding up front
whether `reviewed` will realistically ever be set.

---

## Scores

1 = poor, 5 = excellent. Criteria are the ones named in the goal.

| Criterion | A — Grep Substrate | B — Tiered Catalog | C — Subject Hierarchy |
|---|:---:|:---:|:---:|
| Agent retrieval quality | 2 | **5** | 2 |
| Human browsability | 2 | **4** | 4 |
| Contribution friction (5 = lowest) | **5** | 4 | 1 |
| Resistance to topic sprawl | 3 | **4** | 1 |
| Maintenance burden (5 = lightest) | **5** | 3 | 1 |
| Build complexity (5 = simplest) | **5** | 3 | 1 |
| Link durability | 3 | **5** | 2 |
| **Total** | **25** | **28** | **12** |

A wins on simplicity and survivability. B wins where the user said the value is: agent
retrieval and trust filtering. C is not competitive — three independent FATAL findings.

---

## Recommendation: **Candidate B — Tiered Catalog**

The user's stated problem is not "I need somewhere to put files." It is *"I cannot tell
whether a document is trustworthy enough to feed to another AI."* That makes
**trust-filtered agent retrieval the primary success criterion**, and B is the only
candidate that delivers it across all three access modes at a measured ~10k tokens.

B is not the simplest option, and that is a real cost — it has the most machinery of the
two viable candidates. The reason to accept it: **B contains A.** Its path and frontmatter
conventions are exactly A's, so if every generated artifact vanished tomorrow, B degrades
*into* A rather than into rubble. The extra machinery is additive, not load-bearing.

**Three amendments to B, from the measurements:**

1. **Ship A's substrate first, B's catalog second.** Conventions + validator + markdown
   render is a working system on its own. The tiered catalog is worth building only once
   there is content to route.
2. **Defer Pagefind and diagram pre-rendering** behind explicit triggers (Pagefind at ~300
   docs; prerender only if diagram pages measurably hurt on mobile). Both are additive and
   neither changes the document format.
3. **Tags are open, not controlled.** CI *reports* vocabulary drift; it never fails on it.
   The alternative is `misc/`.

### What I need from you

**This is the decision gate — I have not built anything.** Please confirm:

- **Which candidate** (or a variant — e.g. "B, but skip Pagefind entirely").
- **Will you realistically review documents?** If `reviewed`/`verified` will never be set
  in practice, the lifecycle should collapse to two states and the design gets simpler.
- **Enabling GitHub Pages.** It is currently off (`has_pages: false`). It needs Settings →
  Pages → Source → "GitHub Actions" set once. I have admin via `gh` and may be able to do
  it by API — say whether you want me to, or whether you'll click it yourself.

---

## Appendix A — Measurements

All run on this machine, 2026-08-14: Python 3.12.3, Node 22.23.2, ripgrep 14.1.0, git 2.43.0.

| Finding | Method |
|---|---|
| Nested frontmatter → 1/6 recall; flat → 6/6 | Six semantically-identical YAML variants; `yaml.safe_load` to confirm equivalence; `rg -l` for each shape |
| Flat keys express all conditionals | `Draft202012Validator` with `allOf`/`if`/`then` over flat keys; 6 negative cases, all rejected with actionable messages |
| `format:` is a silent no-op | `Draft202012Validator` against `date-time`/`uri`/`email` with invalid values → zero errors; `rfc3339_validator` import fails |
| Path depth ≈ irrelevant at 1,000 docs | Generated 1,000 docs in both layouts; `rg -l` best-of-5, with and without `-g` prefilter |
| Generated index conflicts; source does not | Two branches from one base, each adding a doc + regenerating `catalog.json`; `git merge` |
| SQLite index unmergeable, loses data | Same two-branch test with an FTS5 DB; `git merge` → `Cannot merge binary files`; post-resolution row count |
| FTS5 size / speed | 1,000-doc FTS5 build: 4.35 MB, 0.14 s build, 1.2 ms trust-filtered query |
| Python toolchain sufficient, zero installs | `markdown_it` 3.0.0 / `yaml` 6.0.1 + `CSafeLoader` / `jsonschema` 4.10.3 in `/usr/lib/python3/dist-packages`; render smoke test |

Figures carried from expert positions (see `positions/` for their methods): flat catalog
1.08 MB / 270k tokens; tiered path ~10k tokens; lunr 18.2 MB; Pagefind rewrites 133/134
chunks on a one-word edit; puppeteer route 1.07 GB and cannot launch here; full build of
1,000 docs 5.15 s; Mermaid 11.16.1 parses native `C4Container`/`C4Context`.
