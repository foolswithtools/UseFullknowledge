---
id: position-metadata-provenance
title: "Frontmatter Schema and Provenance Governance"
type: explainer
created_at: "2026-08-14T11:20:00-07:00"
updated_at: "2026-08-14T11:20:00-07:00"
created_by:
  agent: claude-code
  model: claude-opus-5
  session_ref: "panel/design-phase-1"
confidence:
  basis: [primary-source-cited, model-recall-only]
  level: medium
volatility: slow
review:
  status: unreviewed
sources:
  - title: "DCMI Metadata Terms"
    url: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
  - title: "schema.org TechArticle"
    url: https://schema.org/TechArticle
  - title: "W3C PROV-O: The PROV Ontology"
    url: https://www.w3.org/TR/prov-o/
  - title: "SPDX License List"
    url: https://spdx.org/licenses/
  - title: "C2PA Specification"
    url: https://c2pa.org/specifications/
license: CC-BY-4.0
---

# Position: Frontmatter Schema and Provenance Governance

**Author role:** Metadata & Provenance Governance Specialist
**Charge:** What fields make trust machine-decidable?

---

## 0. The thesis in one paragraph

Trust is not a number an LLM writes about itself. Trust is a **join** between four
independently-sourced facts: (a) what process produced the content, (b) what evidence that
process had, (c) whether a human has since looked at it, and (d) whether enough time has
passed that (a)–(c) no longer apply. My schema exists to make those four facts
*separately recordable and separately falsifiable*. The single most important design move
in this document is that **the confidence LEVEL is derived from a structured evidence
BASIS, and capped by it** — an agent cannot claim `high` while admitting it only had model
recall. The second most important is that **`updated_at` is a claim and git is the fact**,
and the catalog publishes both so a lying frontmatter is visibly a lie rather than
silently authoritative.

---

## 1. Three empirical findings that constrain the design

I tested these in this environment before designing around them. They are not theoretical.

### 1.1 `format: date-time` in JSON Schema is a silent no-op here

`jsonschema` 4.10.3 only enforces `format: date-time` if the optional `rfc3339-validator`
package is installed. It is not. Result:

```
'2026-08-14T09:00:00-07:00'  OK
'2026-08-14T09:00:00'        OK   <-- no offset, accepted
'2026-08-14'                 OK   <-- not even a time, accepted
```

**Ruling:** the hard requirement "ISO 8601 with explicit timezone offset" CANNOT be
expressed as `format: date-time`. It must be a `pattern` regex. Every timestamp field in
the schema uses:

```
^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?[+-]\d{2}:\d{2}$
```

Note this deliberately **rejects `Z`**. `Z` is a valid RFC 3339 offset, but accepting both
forms means two spellings of the same instant, which breaks naive string comparison and
string-based ripgrep queries. One spelling. Numeric offset only. `+00:00` for UTC. This is
the kind of thing that costs nothing on day one and is unfixable at 1,000 documents.

### 1.2 PyYAML silently converts unquoted timestamps into Python objects

```yaml
a: 2026-08-14T09:00:00-07:00   ->  datetime.datetime  (not a str!)
c: 2026-08-14                  ->  datetime.date
```

Worse, round-tripping `a` through `yaml.safe_dump` emits `2026-08-14 09:00:00-07:00` —
**a space instead of the `T`**, which is no longer ISO 8601 and no longer matches the
regex. A string-typed JSON Schema rejects the object outright, producing a confusing
"2026-08-14 09:00:00-07:00 is not of type 'string'" error for frontmatter that looks
perfectly correct to a human.

**Ruling:** all timestamps MUST be quoted in frontmatter. The validator coerces
`datetime`/`date` objects back to canonical strings before schema validation and emits a
`W-QUOTE` warning telling the contributor to quote them, and `--fix` quotes them in place.
This must be stated in `AGENTS.md` in one line, because five of the six contributing tools
will get it wrong otherwise.

### 1.3 `allOf: [if/then]` gives usable errors; `oneOf` does not

Tested with the real base+extension schema:

```
missing per-type block -> "'code' is a required property"
```

That is a message an agent can act on. The same constraint expressed as `oneOf` over five
type variants produces "is not valid under any of the given schemas", which is useless.

**Ruling:** per-type extensions are `allOf` of `if/then` clauses keyed on `type`, never
`oneOf`. Free readable errors, no custom error-mapping code.

---

## 2. What to borrow from the standards, and what to skip

| Standard | Verdict | What I take | What I refuse, and why |
|---|---|---|---|
| **Dublin Core / DCMI Terms** | Borrow at the **output** layer only | `dcterms.created`, `dcterms.modified`, `dcterms.creator`, `dcterms.source`, `dcterms.license` as HTML `<meta>` names | Do NOT use `dcterms:`-prefixed keys as the YAML vocabulary. Namespaced keys in YAML are a typo farm for six independent tools, and DC has no concept of review status, confidence, or staleness — the four things this repo actually exists for. DC is an interchange vocabulary, not an authoring one. |
| **schema.org** | **Borrow heavily.** The one standard with real consumers | `TechArticle`, `SoftwareSourceCode`, `ImageObject`, `CreativeWork`; `dateCreated`, `dateModified`, `author`, `review`/`reviewedBy`, `creativeWorkStatus`, `citation`, `expires`, `license`, `programmingLanguage` | Don't invent unregistered top-level terms. Anything schema.org lacks (confidence, basis, C4 level, volatility) goes in `additionalProperty` as `PropertyValue`, which is the sanctioned extension point. |
| **W3C PROV-O** | Borrow the **discipline**, skip the **graph** | Exactly three flattened predicates: `wasAttributedTo` (→ `created_by`), `wasDerivedFrom` (→ `derived_from`), `actedOnBehalfOf` (→ the human owner behind the agent). Plus one opaque nod to `prov:Activity` via `session_ref`. | A full PROV graph — Activity nodes, `wasInformedBy` chains, `qualifiedGeneration`, bundles — is **not achievable here and would be actively harmful**. It requires six mutually-ignorant tools to mint globally consistent Activity URIs. They will not. What you'd get is 1,000 orphan activity nodes with no edges: the *appearance* of a provenance graph with none of the connectivity, which is worse than an honest flat record. Revisit only if a single orchestrator ever mediates all writes. |
| **SPDX** | Borrow **one field** | `license` must be a valid SPDX license identifier (`CC-BY-4.0`, `MIT`, `CC0-1.0`), validated against a small bundled allow-list of ~8 ids | No SPDX documents, no SBOM, no `PackageLicenseDeclared`, no per-file tags. This is a prose knowledge base, not a software distribution. One string. |
| **C2PA** | Borrow the **mental model**, refuse the **cryptography** | The idea that provenance is a *chain of assertions about what each tool did*, and that a rendered artifact should be bindable to its source. Implemented as: `content_sha256` of the markdown body computed **into the catalog**, and for diagrams a `source_sha256` recorded at render time so rendered/source drift is detectable. | No COSE signing, no X.509, no trust list, no manifest store. There is no key-management story for a public repo with no auth and six agents; a signature nobody can verify is theater. **Git is the substitute for the signature**: the commit DAG is a tamper-evident, already-present, already-free integrity log, and `git log --show-signature` upgrades it later if the owner wants signed commits. |

**One rule I want to underline because it gets violated constantly:** never put a hash of a
file inside that file. `content_sha256` lives in the generated `catalog.json`, computed over
the body *below* the frontmatter. Putting it in the frontmatter is self-referential and
guarantees either a chicken-and-egg build or a permanently-wrong field.

---

## 3. Answers to the six critical questions

### Q1. Making `confidence` mean something

**Premise I accept: a self-assessed scalar from an LLM is worthless.** `confidence: 0.85`
is a token sampled from a distribution, not a measurement. Any scheme that stores a free
scalar will produce a corpus where 900 of 1,000 documents say "high".

**The fix: the level is not stated, it is EARNED.** `confidence.basis` is a required array
drawn from a closed enum of *evidence kinds* — things that either happened during
authoring or did not:

| `basis` value | Meaning — what physically happened | Level ceiling |
|---|---|---|
| `human-expert-review` | A named human with domain knowledge read it end to end | `high` |
| `executed-verified` | The code/commands were actually run and output observed | `high` |
| `primary-source-cited` | Claims traced to spec/RFC/official docs/paper, URLs in `sources` | `high` |
| `cross-model-corroborated` | ≥2 distinct models independently produced consistent content | `medium` |
| `secondary-source-cited` | Blogs, StackOverflow, tutorials, cited in `sources` | `medium` |
| `synthetic-example` | Illustrative/invented, not claimed to describe a real system | `low` |
| `model-recall-only` | No external verification of any kind. Weights only. | `low` |

`confidence.level ∈ {low, medium, high}` is **optional**. If omitted, the build **derives**
it as the max ceiling across the declared basis values. If present, the validator enforces
`stated_level <= derived_ceiling`. An author may state *lower* than earned — honest
self-doubt is always permitted — but **never higher**. `confidence: {basis: [model-recall-only], level: high}` is a **CI failure**, not a warning. That single rule is what converts
confidence from vibes into a decidable property.

Two enforcement teeth that make basis non-gameable at low cost:

1. **Citation cross-check.** If `basis` contains any `*-source-cited` value, `sources` must
   be a non-empty array and every entry must have a `url`. Claiming citation without
   citing is a hard failure. This is the check that stops `primary-source-cited` from
   becoming a free "high" token.
2. **Corroboration cross-check.** `cross-model-corroborated` requires
   `corroborated_by` listing ≥1 model identifier distinct from `created_by.model`.

`basis` is an array because real documents are mixed: a Kafka explainer can be
`[primary-source-cited, executed-verified]` for the parts that were run and cited, and the
ceiling correctly comes out `high`.

**Honest limit:** a lying agent can still write `executed-verified` without executing
anything. Nothing in a static repo can prevent that. What the scheme *does* buy is that the
lie is now (a) a specific, falsifiable, reviewable claim rather than an opinion, (b)
attributable to a named `created_by.agent` so a systematically-lying tool can be identified
and its whole corpus demoted with one grep, and (c) invisible-to-nobody: it appears in the
rendered HTML footer. Deterrence and attribution, not prevention. Claiming otherwise would
be dishonest.

### Q2. Keeping `updated_at` honest when an agent forgets to bump it

**Framing: frontmatter `updated_at` is a CLAIM. `git log` is the FACT.** The design does not
try to make the claim self-enforcing; it makes the fact always visible next to it.

Verified working:

```
$ git log -1 --format=%aI -- README.md
2026-08-13T22:51:19-07:00
```

**The reconciliation rule the validator enforces**, run in CI over changed files only:

```
for each file F in (git diff --name-only $BASE...$HEAD -- '*.md'):
    git_ts   = git log -1 --format=%aI -- F        # last commit touching F
    fm_ts    = frontmatter.updated_at
    delta    = |git_ts - fm_ts|

    if fm_ts > git_ts + 1h              -> FAIL  E-FUTURE   (future-dated claim)
    if delta > 24h                      -> FAIL  E-DRIFT    (forgot to bump)
    if body_hash changed
       and review.status != unreviewed
       and updated_by.kind == "agent"   -> FAIL  E-DEMOTE   (see below)
```

Rationale for each number:

- **24h tolerance, not zero.** An agent cannot know the commit timestamp at write time —
  the commit does not exist yet. A zero-tolerance rule is unsatisfiable and would be
  disabled within a week. 24h absorbs write-then-commit-later and timezone sloppiness while
  still making "written last November, claimed as current" impossible.
- **+1h future allowance** covers clock skew between an agent's environment and the CI
  runner, and nothing more.
- **Changed files only.** A document committed once and never touched again keeps a stable
  git timestamp and a stable `updated_at` forever, and is never re-checked. The check has
  O(changed files) cost, not O(corpus), so it stays fast at 1,000 docs.

**What happens on mismatch:**

- CI: hard fail with the exact expected value in the message
  (`E-DRIFT kb/kafka.md: updated_at says 2025-11-02T10:00:00-08:00, git says
  2026-08-14T09:12:33-07:00 (285 days). Run: python3 tools/validate.py --fix`).
- Local: `tools/validate.py --fix` rewrites `updated_at` from git, and a
  `pre-commit` hook runs `--fix` so the common path never reaches CI red.
- Escape hatch for mechanical churn (bulk reformat, mass link rewrite): a commit trailer
  `Provenance-Exempt: mechanical` skips the drift check for that commit. Deliberately a
  commit trailer and not a frontmatter field, so it is scoped to one act and leaves an
  audit trail in `git log` instead of a permanent opt-out sitting in a document.

**The belt-and-braces part, and the bit I care about most:** `catalog.json` carries
**both** `updated_at` (the claim) and `git_updated_at` + `revision_count` (the facts, read
from git at build time), for every document. Even if a claim slips through — via `--fix`
misuse, an exempt commit, a direct push bypassing CI — a consuming agent can compare the
two fields itself. The validator bounds the gap; the catalog makes the gap inspectable. A
provenance system whose only integrity check is its own validator has a single point of
failure.

**The E-DEMOTE rule** deserves its own line because it closes the nastiest hole: an agent
edits a document the human previously marked `verified`, and the `verified` badge silently
now vouches for text no human ever read. Rule: **if a commit changes the body hash of a
document whose `review.status` is above `unreviewed`, and `updated_by.kind == "agent"`, CI
fails unless the same commit resets `review.status` to `unreviewed`.** Human updaters may
re-affirm in place but must bump `review.reviewed_at`. Review status is a statement about a
specific body of text, and it must not survive that text changing under it.

### Q3. Staleness without babysitting

**Nobody hand-sets a review-by date. Ever.** Per-document dates rot instantly: at 1,000
docs, six tools will invent six conventions and half the dates will be wrong.

Instead, one required enum — `volatility` — one word, chosen at authoring time, mapped
through a single table in `_meta/shelf-life.yml`:

```yaml
# _meta/shelf-life.yml  -- the ONLY place shelf life is defined
shelf_life_days:
  ephemeral:   30    # preview APIs, model-specific quirks, bleeding-edge tool behavior
  fast:        90    # actively developed libraries, frameworks, cloud service APIs
  moderate:   365    # mature protocols, stable tooling, established practice
  slow:      1095    # ratified standards, RFCs, architecture patterns, algorithms
  evergreen: 3650    # mathematics, physics, thermodynamics, complexity theory
default: fast        # fail-closed: unknown volatility is treated as fast-moving
```

**Staleness is COMPUTED at build time, never stored in frontmatter.** This is the load-
bearing decision. Storing `stale: true` in markdown would require the build to write back
into source files, producing daily commit churn, merge conflicts between six agents, and a
field that is wrong every day the build doesn't run.

```
freshness_anchor = review.reviewed_at  if review.status != unreviewed  else updated_at
expires_at       = freshness_anchor + shelf_life_days[volatility]
stale            = build_time > expires_at
```

`expires_at` and `stale` are emitted into `catalog.json` and into the rendered HTML
(`<meta name="ukb:expires-at">`, and a visible amber "Review due" banner). They are pure
functions of committed source plus the wall clock, so they can never drift out of sync —
regenerating the catalog is idempotent.

A thermodynamics explainer says `volatility: evergreen` and is untouched for a decade. A
`langchain` migration guide says `volatility: fast` and goes amber after 90 days. That is
exactly the requirement, at a cost of one enum token per document.

Three deliberate details:

- **`evergreen` is 10 years, not infinite.** A document that can never expire can never be
  re-examined, and "eternal truth" is a claim humans get wrong. Ten years forces one look.
- **Why `volatility` is REQUIRED despite my own ruthlessness about required fields:** it is
  the only field in the entire schema that cannot be derived, defaulted safely, or
  recovered later. Topic volatility is a judgment about subject matter that only the author
  holds; git doesn't know it and no heuristic can infer it across 200 unrelated topics.
- **Anti-gaming, honestly labelled as weak:** an agent can dodge staleness nagging by
  writing `evergreen` on a React tutorial. Soft rule: `evergreen` or `slow` on a document
  whose body matches a version-pin pattern (`\d+\.\d+\.\d+`, `npm install`, `pip install`)
  emits warning `W-VOLATILITY` — a warning, not a failure, because the false-positive rate
  is too high for a hard gate. This is gameable and I am not going to pretend otherwise.

### Q4. "Give me only `verified`, non-stale documents about X" from repo contents alone

**Fields involved:** `review.status`, computed `stale` / `expires_at`, `type`, and the
topical fields (`title`, `summary`, `tags`, `topics`).

**Tier 1 — canonical, via generated `catalog.json` + jq.** Verified working:

```bash
jq -r --arg q 'kafka' '
  .documents[]
  | select(.review_status == "verified")
  | select(.stale == false)
  | select(([.title, .summary] + .tags + .topics | join(" ") | ascii_downcase | test($q)))
  | .raw_url
' catalog.json
```

Tested against a fixture: returns the verified non-stale Kafka doc, correctly excludes both
the unreviewed CRISPR doc and the stale Kafka ACLs doc. Exit 0. One file fetch, one jq pass,
no index server, works offline, works from `raw.githubusercontent.com`.

**Tier 2 — degraded, ripgrep only, if the catalog is missing or distrusted.** Verified
working with ripgrep 14.1.0:

```bash
rg -U --multiline-dotall -l '^---\n(.*\n)*?  status: verified' docs/ \
  | xargs rg -l -i 'kafka'
```

This finds `verified` documents but **cannot compute staleness**, since staleness needs
arithmetic against the clock. That is the honest cost of not storing `stale` in the file.
The mitigation is that `expires_at` *is* materialized into the generated HTML and the
catalog, and the fallback path is one `python3 -c` away from a full answer. I accept the
tradeoff: a slightly weaker degraded mode in exchange for markdown that never churns.

**Precondition for both:** the query only works if `research-note` documents can never
reach `verified`. Hard schema rule: `type: research-note` caps `review.status` at
`reviewed`. Raw AI output must be structurally incapable of impersonating a curated,
verified explainer — that separation is a hard requirement of the brief and I enforce it in
the schema rather than by convention.

### Q5. Minimum viable required set

**The principle I use to decide, stated once and applied mechanically:**

> **REQUIRE what is only knowable at creation time and unrecoverable afterwards.
> DEFAULT everything that is a lifecycle state or recoverable from git.**

Every required field is friction, and friction at 6 tools × 1,000 documents is where a
schema dies. So: eight required fields.

| Field | Required? | Reasoning under the principle |
|---|---|---|
| `id` | **YES** | Stable address; link durability depends on it; cannot be reconstructed after a rename. |
| `title` | **YES** | Human and agent entry point. Deriving from `# H1` is a fragile heuristic when six tools format differently. |
| `type` | **YES** | Selects the schema branch and the query surface. Path-inference is not durable across reorganizations. |
| `created_at` | **YES** | **Not recoverable from git.** A doc written by ChatGPT last November and committed today has a git-add date of today. This is precisely the user's stated core problem; it is the field the whole system exists for. |
| `updated_at` | **YES** | Trivially cheap (copy `created_at`), and the brief demands unambiguity. Auto-fillable by `--fix`, so the friction is near zero. |
| `created_by.agent` + `.model` | **YES** | Only knowable at generation. Unrecoverable. The other half of the user's core problem ("unverified model"). |
| `confidence.basis` | **YES** | A record of what evidence the authoring process actually had. Nobody can reconstruct this next month. Creation-time fact. |
| `volatility` | **YES** | Cannot be derived across an unbounded topic space; the only safe default (`fast`) is wrong for most explainers. |

**Deliberately NOT required — and why each cut is safe:**

| Field | Default | Why omission is safe |
|---|---|---|
| `review.status` | `unreviewed` | **Fail-closed.** The default is the least-trusted state. An agent that forgets loses trust rather than gaining it, so forgetting can never cause harm. This is a lifecycle state that a human adds later — requiring it at creation is pure friction for zero safety. |
| `confidence.level` | derived from `basis` | Derivation is strictly better than assertion (Q1). |
| `license` | repo-level `LICENSE` | Inherits. Only needed to override. |
| `summary`, `tags`, `topics` | absent | Improve retrieval, never affect trust. Warned (`W-DISCOVERY`), never failed. A doc that is hard to find is a smaller problem than a doc nobody filed because the schema was exhausting. |
| `session_ref`, `derived_from`, `corroborated_by` | absent | Genuinely unavailable from many tools. Requiring a field half your contributors cannot supply teaches them to fabricate it — the worst possible outcome for a provenance system. |
| `updated_by` | absent | **Conditionally required:** must be present iff `updated_at != created_at`. |
| `sources` | absent | **Conditionally required:** must be non-empty iff `basis` contains a `*-source-cited` value. |
| `review.reviewer`, `review.reviewed_at` | absent | **Conditionally required:** iff `review.status != unreviewed`. |

Conditional requirements are the release valve that keeps the unconditional set at eight.
An agent that knows nothing writes eight fields; an agent that claims something extra pays
for the claim.

**The `updated_at` sentinel decision — mirror `created_at`.** Considered and rejected:

- **Blank/absent** — this is exactly the "blank-and-guessable" failure the brief names. Every
  consumer invents its own fallback. Rejected.
- **Explicit `null`** — type-erodes the field. Every jq expression, every sort, every
  comparison in every consuming agent needs a null guard, and the ones that forget crash or
  silently mis-sort. At six independent consumers, some will forget. Rejected.
- **Sentinel string (`never`, `0000-...`)** — breaks the timestamp pattern, so the schema
  needs a union type, and `never` sorts before every real date in string comparison, which
  is coincidentally right and dangerously so. Rejected.
- **Mirror `created_at`** — **chosen.** The field is *always* a valid, comparable,
  same-typed timestamp. Sorting, filtering, and staleness math need zero special cases.
  And no information is lost: "never updated" remains perfectly decidable as
  `updated_at == created_at && updated_by == null`, corroborated by `revision_count == 1`
  from git in the catalog. A uniform type with a derivable predicate beats a special case
  in every consumer.

### Q6. Per-content-type variance

**Base schema for all five types**, then a `type`-keyed extension block. The extension is a
single nested object named for the type family, so a contributing agent has exactly one
place to look and the `if/then` error message names it directly.

| Type | Extension key | Required inside | Why the base is insufficient |
|---|---|---|---|
| `explainer` | *(none)* | — | The base schema is complete. Do not invent fields for the majority case. |
| `diagram` | `diagram` | `notation`, `source_path`, `rendered_path`, `c4_level` | The trust question for a diagram is *"does the rendered PNG/SVG still match the Mermaid source?"* — a question that does not exist for prose. `source_sha256` (hash of the source at render time) makes rendered/source drift detectable, which is the C2PA idea applied where it actually earns its keep. `c4_level` is a required enum (`context`/`container`/`component`/`code`/`dynamic`/`deployment`/`n-a`) because C4 level is the primary retrieval facet for diagrams and is not inferable from the source. |
| `snippet` | `code` | `language`, `language_version`, `verification` | The brief requires recording *what version it was valid for*. `language_version` is a **range** (`">=3.10,<4"`), not a point, because that is what "valid for" actually means. `verification ∈ {executed, compiled, linted, not-run}` is the type-local, checkable analogue of `confidence.basis`, and the validator enforces coherence: `verification: executed` requires `executed-verified` in `basis`. `dependencies` pins versions. |
| `artifact` (prompts/skills/agent configs) | `artifact` | `kind`, `target_tools` | A prompt's trust is *tool- and model-relative*: a skill that works in Claude Code may fail in Cursor. `model_tested_on` records where it was actually observed to work. `kind ∈ {prompt, skill, agent-config, system-prompt}`. |
| `research-note` | `research` | `raw` | Must carry `raw: true` and is schema-capped at `review.status: reviewed`. This type exists to be structurally distinguishable from curated content, so its extension is a *restriction*, not an addition — the only one in the schema. |

---

## 4. Complete worked example — explainer

```yaml
---
id: kafka-partition-rebalancing
title: "Kafka Partition Rebalancing: Eager vs Cooperative Protocols"
summary: >-
  How consumer group rebalancing works in Apache Kafka, why eager rebalancing
  causes stop-the-world pauses, and how the cooperative-sticky assignor avoids them.
type: explainer
topics: [distributed-systems, messaging]
tags: [kafka, consumer-groups, rebalancing, kip-429]

created_at: "2025-11-02T14:07:00-07:00"
created_by:
  agent: chatgpt
  model: gpt-5.1
  session_ref: "chatgpt://conv/8f2a-1c04"

updated_at: "2026-08-11T09:42:00-07:00"
updated_by:
  kind: human
  name: "Chris Lostaunau"
  contact: chris.lostaunau@gmail.com

review:
  status: verified
  reviewer: "Chris Lostaunau"
  reviewed_at: "2026-08-11T09:42:00-07:00"
  note: "Checked assignor behaviour against KIP-429 and a local 3-broker cluster."

confidence:
  level: high
  basis:
    - primary-source-cited
    - executed-verified
    - human-expert-review

volatility: moderate

sources:
  - title: "KIP-429: Kafka Consumer Incremental Rebalance Protocol"
    url: https://cwiki.apache.org/confluence/display/KAFKA/KIP-429
    kind: primary
    accessed: "2026-08-11"
  - title: "Apache Kafka 3.7 Documentation - Consumer Configs"
    url: https://kafka.apache.org/37/documentation.html#consumerconfigs
    kind: primary
    accessed: "2026-08-11"

derived_from: []
license: CC-BY-4.0
---
```

Read this and the user's core question answers itself in one glance: **written by GPT-5.1
in November 2025, verified by a named human in August 2026 against primary sources and a
real cluster, moderate volatility so it goes amber in August 2027.** That is the whole
point of the schema.

Contrast — the same document at minimum viable (an agent that knows nothing else):

```yaml
---
id: kafka-partition-rebalancing
title: "Kafka Partition Rebalancing"
type: explainer
created_at: "2026-08-14T11:03:00-07:00"
updated_at: "2026-08-14T11:03:00-07:00"
created_by:
  agent: cursor
  model: claude-sonnet-4.6
confidence:
  basis: [model-recall-only]
volatility: fast
---
```

This validates. It resolves to `review.status: unreviewed`, `confidence.level: low`
(ceiling), `expires_at: 2026-11-12`. It is honestly labelled as low-trust, which is a
*success*, not a failure — the system's job is to let cheap low-trust content in while
making it impossible to mistake for the reviewed article.

## 5. Worked example — diagram

```yaml
---
id: c4-container-payments-platform
title: "C4 Container Diagram: Payments Platform"
type: diagram
topics: [architecture]
tags: [c4, payments, container-diagram]

created_at: "2026-08-14T10:15:00-07:00"
created_by:
  agent: claude-code
  model: claude-opus-5
  session_ref: "claude-code://session/2026-08-14/c05b8801"
updated_at: "2026-08-14T10:15:00-07:00"

review:
  status: reviewed
  reviewer: "Chris Lostaunau"
  reviewed_at: "2026-08-14T10:40:00-07:00"

confidence:
  basis: [human-expert-review]

volatility: fast

diagram:
  notation: mermaid              # mermaid | structurizr-dsl | plantuml | graphviz
  c4_level: container            # context|container|component|code|dynamic|deployment|n-a
  source_path: ./payments-platform.container.mmd
  rendered_path: ./payments-platform.container.svg
  source_sha256: "9f2c1ab7e4d05583a1f7c9e2b6d8043f5c71ae92b0d4f6389c2a1e7b5d3049af"
  subject_system: "Acme Payments Platform"
  renderer: "mermaid-cli@11.4.0"
---
```

`source_sha256` is the hash of `source_path` **as of the last render**. At build time the
build re-hashes the source: mismatch means the `.svg` is stale relative to the `.mmd`, and
CI fails with `E-RENDER-DRIFT`. This is the only place I import C2PA's binding idea,
because it is the only place where two artifacts must agree and cannot be checked by
reading. `volatility: fast` is correct here for a client system diagram — architecture
drawings go wrong quickly and silently.

## 6. Worked example — code snippet

```yaml
---
id: snippet-kafka-cooperative-consumer
title: "Kafka consumer with cooperative-sticky assignor (Python)"
type: snippet
topics: [distributed-systems]
tags: [kafka, python, confluent-kafka]

created_at: "2026-08-14T10:52:00-07:00"
created_by:
  agent: aider
  model: gpt-5.1-codex
updated_at: "2026-08-14T10:52:00-07:00"

review:
  status: unreviewed

confidence:
  basis: [executed-verified]

volatility: fast

code:
  language: python
  language_version: ">=3.10,<4"
  verification: executed
  verified_at: "2026-08-14T10:52:00-07:00"
  entrypoint: ./consumer.py
  dependencies:
    - "confluent-kafka==2.6.1"
  runtime_notes: "Run against Kafka 3.7 in Docker; requires a reachable broker on :9092."
---
```

Note `confidence.basis: [executed-verified]` with `review.status: unreviewed`: the code was
*run*, but no human read it. Those are genuinely different claims and the schema keeps them
separate — collapsing them into one "trust score" is exactly the mistake this design
avoids. Derived level: `high`. Cross-check: `verification: executed` requires
`executed-verified` in `basis`. Consistent.

---

## 7. Required vs optional field table

Legend: **R** = required (CI fails), **C** = conditionally required, **O** = optional,
**D** = derived/computed (never written in frontmatter).

| Field | Type | R/C/O/D | Condition / default |
|---|---|---|---|
| `id` | string, `^[a-z0-9][a-z0-9-]{2,63}$` | **R** | — |
| `title` | string, ≥3 chars | **R** | — |
| `type` | enum(explainer, diagram, snippet, artifact, research-note) | **R** | — |
| `created_at` | ISO 8601 + numeric offset, quoted | **R** | — |
| `updated_at` | ISO 8601 + numeric offset, quoted | **R** | mirrors `created_at` if never updated |
| `created_by.agent` | string | **R** | — |
| `created_by.model` | string | **R** | `"unknown"` permitted, `""` is not |
| `confidence.basis` | array of evidence enum, ≥1 | **R** | — |
| `volatility` | enum(ephemeral, fast, moderate, slow, evergreen) | **R** | — |
| `updated_by.kind` | enum(human, agent) | **C** | required iff `updated_at != created_at` |
| `updated_by.name` | string | **C** | required with `updated_by.kind` |
| `updated_by.model` | string | **C** | required iff `updated_by.kind == agent` |
| `review.reviewer` | string | **C** | required iff `review.status != unreviewed` |
| `review.reviewed_at` | timestamp | **C** | required iff `review.status != unreviewed` |
| `sources[]` | array of {title,url,kind,accessed} | **C** | non-empty iff `basis` has `*-source-cited` |
| `corroborated_by` | array of model ids | **C** | required iff `basis` has `cross-model-corroborated` |
| `diagram.*` | object | **C** | required iff `type == diagram` |
| `code.*` | object | **C** | required iff `type == snippet` |
| `artifact.*` | object | **C** | required iff `type == artifact` |
| `research.raw` | `true` | **C** | required iff `type == research-note` |
| `review.status` | enum(unreviewed, reviewed, verified, deprecated) | **O** | defaults `unreviewed` |
| `confidence.level` | enum(low, medium, high) | **O** | derived from basis; capped by it |
| `summary` | string ≤300 | **O** | warn `W-DISCOVERY` |
| `tags[]`, `topics[]` | array of slug | **O** | warn `W-DISCOVERY` |
| `created_by.session_ref` | string/URI | **O** | the only nod to `prov:Activity` |
| `derived_from[]` | array of doc `id` | **O** | `prov:wasDerivedFrom` |
| `license` | SPDX id | **O** | inherits repo `LICENSE` |
| `superseded_by` | doc `id` | **C** | required iff `status == deprecated` and a successor exists |
| `expires_at` | timestamp | **D** | `anchor + shelf_life[volatility]` |
| `stale` | boolean | **D** | `now > expires_at` |
| `confidence.level` (effective) | enum | **D** | `min(stated, ceiling(basis))` |
| `git_updated_at` | timestamp | **D** | `git log -1 --format=%aI` |
| `revision_count` | integer | **D** | `git rev-list --count HEAD -- <path>` |
| `content_sha256` | hex | **D** | sha256 of body below frontmatter |

Eight unconditional required fields. Everything else is either earned, inherited, or
computed.

---

## 8. JSON Schema sketch (base + one extension) — validated in shape

**This is not a sketch in the hand-wavy sense — I extracted the JSON below from this very
file and ran it.** `jsonschema` 4.10.3, Draft 2020-12, `check_schema` clean, results:

```
schema is well-formed
explainer:                VALID
  no-offset ts         -> REJECTED: '2025-11-02T14:07:00' does not match '^\d{4}-...'
  Z offset             -> REJECTED: '2025-11-02T14:07:00Z' does not match '^\d{4}-...'
  cites w/o sources    -> REJECTED: 'sources' is a required property
  verified w/o reviewer-> REJECTED: 'reviewer' is a required property
  bad evidence enum    -> REJECTED: 'vibes' is not one of ['human-expert-review', ...]
  unknown field        -> REJECTED: Additional properties are not allowed ('nonsense' ...)
snippet:                  VALID
  snippet w/o code     -> REJECTED: 'code' is a required property
research-note verified -> REJECTED: 'verified' is not one of ['unreviewed','reviewed','deprecated']
```

Every message is one an agent can act on without a schema loader. The only edit needed to
run it is replacing the four `$defs/nothing` placeholders with `{"type": "object"}`, as
described below the listing.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://clostaunau.github.io/UseFullknowledge/schema/document.v1.json",
  "title": "UseFullknowledge document frontmatter v1",
  "type": "object",
  "additionalProperties": false,
  "$defs": {
    "timestamp": {
      "type": "string",
      "description": "ISO 8601 with explicit NUMERIC offset. 'Z' is rejected: one spelling only. MUST be quoted in YAML or PyYAML coerces it to a datetime object.",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}(:\\d{2})?[+-]\\d{2}:\\d{2}$"
    },
    "slug": { "type": "string", "pattern": "^[a-z0-9][a-z0-9-]{1,63}$" },
    "evidence": {
      "enum": ["human-expert-review", "executed-verified", "primary-source-cited",
               "cross-model-corroborated", "secondary-source-cited",
               "synthetic-example", "model-recall-only"]
    }
  },

  "required": ["id", "title", "type", "created_at", "updated_at",
               "created_by", "confidence", "volatility"],

  "properties": {
    "id":    { "$ref": "#/$defs/slug" },
    "title": { "type": "string", "minLength": 3, "maxLength": 120 },
    "summary": { "type": "string", "maxLength": 300 },
    "type":  { "enum": ["explainer", "diagram", "snippet", "artifact", "research-note"] },
    "topics": { "type": "array", "items": { "$ref": "#/$defs/slug" } },
    "tags":   { "type": "array", "items": { "$ref": "#/$defs/slug" } },

    "created_at": { "$ref": "#/$defs/timestamp" },
    "updated_at": { "$ref": "#/$defs/timestamp" },

    "created_by": {
      "type": "object",
      "additionalProperties": false,
      "required": ["agent", "model"],
      "properties": {
        "agent":       { "type": "string", "minLength": 1 },
        "model":       { "type": "string", "minLength": 1 },
        "session_ref": { "type": "string" },
        "on_behalf_of":{ "type": "string" }
      }
    },

    "updated_by": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "name"],
      "properties": {
        "kind":  { "enum": ["human", "agent"] },
        "name":  { "type": "string" },
        "model": { "type": "string" },
        "contact": { "type": "string" }
      },
      "allOf": [
        { "if":   { "properties": { "kind": { "const": "agent" } } },
          "then": { "required": ["model"] } }
      ]
    },

    "review": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "status":      { "enum": ["unreviewed", "reviewed", "verified", "deprecated"],
                         "default": "unreviewed" },
        "reviewer":    { "type": "string" },
        "reviewed_at": { "$ref": "#/$defs/timestamp" },
        "note":        { "type": "string" }
      },
      "allOf": [
        { "if":   { "properties": { "status": { "enum": ["reviewed","verified","deprecated"] } },
                    "required": ["status"] },
          "then": { "required": ["reviewer", "reviewed_at"] } }
      ]
    },

    "confidence": {
      "type": "object",
      "additionalProperties": false,
      "required": ["basis"],
      "properties": {
        "level": { "enum": ["low", "medium", "high"] },
        "basis": { "type": "array", "minItems": 1, "uniqueItems": true,
                   "items": { "$ref": "#/$defs/evidence" } }
      }
    },

    "volatility": { "enum": ["ephemeral","fast","moderate","slow","evergreen"] },

    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["title", "url"],
        "properties": {
          "title":    { "type": "string" },
          "url":      { "type": "string", "pattern": "^https?://" },
          "kind":     { "enum": ["primary", "secondary", "dataset", "code"] },
          "accessed": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" }
        }
      }
    },

    "corroborated_by": { "type": "array", "items": { "type": "string" } },
    "derived_from":    { "type": "array", "items": { "$ref": "#/$defs/slug" } },
    "superseded_by":   { "$ref": "#/$defs/slug" },
    "license": { "enum": ["CC-BY-4.0","CC-BY-SA-4.0","CC0-1.0","MIT","Apache-2.0",
                          "BSD-3-Clause","Unlicense","LicenseRef-Proprietary"] },

    "diagram":  { "$ref": "#/$defs/nothing" },
    "code":     { "$ref": "#/$defs/nothing" },
    "artifact": { "$ref": "#/$defs/nothing" },
    "research": { "$ref": "#/$defs/nothing" }
  },

  "allOf": [
    {
      "$comment": "SNIPPET EXTENSION. if/then, never oneOf -- oneOf yields 'is not valid under any of the given schemas', if/then yields \"'code' is a required property\".",
      "if":   { "properties": { "type": { "const": "snippet" } }, "required": ["type"] },
      "then": {
        "required": ["code"],
        "properties": {
          "code": {
            "type": "object",
            "additionalProperties": false,
            "required": ["language", "language_version", "verification"],
            "properties": {
              "language":         { "type": "string" },
              "language_version": { "type": "string",
                                    "$comment": "A RANGE, e.g. '>=3.10,<4' -- 'valid for' is an interval, not a point." },
              "verification":     { "enum": ["executed", "compiled", "linted", "not-run"] },
              "verified_at":      { "$ref": "#/$defs/timestamp" },
              "entrypoint":       { "type": "string" },
              "dependencies":     { "type": "array", "items": { "type": "string" } },
              "runtime_notes":    { "type": "string" }
            }
          }
        }
      }
    },
    {
      "$comment": "DIAGRAM EXTENSION (abbreviated).",
      "if":   { "properties": { "type": { "const": "diagram" } }, "required": ["type"] },
      "then": {
        "required": ["diagram"],
        "properties": {
          "diagram": {
            "type": "object",
            "required": ["notation", "c4_level", "source_path", "rendered_path"],
            "properties": {
              "notation":  { "enum": ["mermaid","structurizr-dsl","plantuml","graphviz"] },
              "c4_level":  { "enum": ["context","container","component","code",
                                      "dynamic","deployment","n-a"] },
              "source_path":   { "type": "string" },
              "rendered_path": { "type": "string" },
              "source_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
              "subject_system":{ "type": "string" },
              "renderer":      { "type": "string" }
            }
          }
        }
      }
    },
    {
      "$comment": "RESEARCH NOTES CANNOT BE VERIFIED. Structural separation of raw AI output from curated docs.",
      "if":   { "properties": { "type": { "const": "research-note" } }, "required": ["type"] },
      "then": {
        "required": ["research"],
        "properties": {
          "research": { "type": "object", "required": ["raw"],
                        "properties": { "raw": { "const": true } } },
          "review":   { "properties": { "status": { "enum": ["unreviewed","reviewed","deprecated"] } } }
        }
      }
    },
    {
      "$comment": "Citation cross-check: claiming a citation requires citing.",
      "if": { "properties": { "confidence": { "properties": { "basis": {
               "contains": { "enum": ["primary-source-cited","secondary-source-cited"] } } } } } },
      "then": { "required": ["sources"],
                "properties": { "sources": { "minItems": 1 } } }
    }
  ]
}
```

`$defs/nothing` is a placeholder that the validator replaces per branch; in the real schema
the four extension keys are declared as `{"type":"object"}` at the top level so
`additionalProperties: false` does not reject them, with the real constraints living in the
`allOf` branches. Rules that JSON Schema cannot express — the confidence ceiling table, the
git/`updated_at` reconciliation, `verification: executed` ⟹ `executed-verified` in basis,
and the E-DEMOTE rule — are implemented as **~60 lines of Python cross-checks** running
after schema validation. I state that split explicitly because pretending JSON Schema can
carry policy is how validators end up half-enforced.

---

## 9. JSON-LD and meta-tag mapping for generated HTML

Two machine-readable layers plus the visible human footer required by the brief. Both are
emitted by the build script from the same frontmatter, so drift is impossible.

### 9.1 Field → schema.org / Dublin Core mapping

| Frontmatter | schema.org | DC meta name | Custom meta |
|---|---|---|---|
| `title` | `name` / `headline` | `DC.title` | — |
| `summary` | `description` | `DC.description` | — |
| `type: explainer` | `@type: TechArticle` | `DC.type` | — |
| `type: snippet` | `@type: SoftwareSourceCode` | `DC.type` | — |
| `type: diagram` | `@type: ImageObject` (+`about`) | `DC.type` | — |
| `type: artifact` / `research-note` | `@type: CreativeWork` | `DC.type` | — |
| `created_at` | `dateCreated` | `DC.date.created` | — |
| `updated_at` | `dateModified` | `DC.date.modified` | `article:modified_time` |
| `created_by.{agent,model}` | `author: SoftwareApplication{name, softwareVersion}` | `DC.creator` | `ukb:agent`, `ukb:model` |
| `created_by.on_behalf_of` | `publisher: Person` | `DC.publisher` | — |
| `updated_by` (human) | `editor: Person` | `DC.contributor` | `ukb:updated-by-kind` |
| `review.status` | `creativeWorkStatus` | — | `ukb:review-status` |
| `review.{reviewer,reviewed_at}` | `review: Review{author, datePublished}` + `reviewedBy` | — | `ukb:reviewed-at` |
| `confidence.level` (effective) | `additionalProperty: PropertyValue` | — | `ukb:confidence` |
| `confidence.basis` | `additionalProperty: PropertyValue` (comma-joined) | — | `ukb:confidence-basis` |
| `volatility` | `additionalProperty: PropertyValue` | — | `ukb:volatility` |
| `expires_at` (D) | `expires` | — | `ukb:expires-at` |
| `stale` (D) | — | — | `ukb:stale` |
| `sources[]` | `citation: [CreativeWork{name,url}]` | `DC.source` | — |
| `license` | `license` (SPDX URL) | `DC.rights` | — |
| `derived_from[]` | `isBasedOn` | `DC.relation` | — |
| `code.language` | `programmingLanguage` | — | — |
| `code.language_version` | `runtimePlatform` | — | — |
| `diagram.c4_level` | `additionalProperty: PropertyValue` | — | `ukb:c4-level` |
| `id` | `identifier` | `DC.identifier` | `ukb:doc-id` |
| — | `encoding: {contentUrl: <raw.githubusercontent URL>}` | — | `ukb:raw-url` |

`prov:` terms ride along inside the same JSON-LD `@context` — three predicates, no separate
graph file.

### 9.2 Emitted head, for the Kafka explainer above

```html
<meta name="DC.title" content="Kafka Partition Rebalancing: Eager vs Cooperative Protocols">
<meta name="DC.creator" content="chatgpt / gpt-5.1">
<meta name="DC.date.created" content="2025-11-02T14:07:00-07:00">
<meta name="DC.date.modified" content="2026-08-11T09:42:00-07:00">
<meta name="DC.rights" content="CC-BY-4.0">
<meta name="ukb:doc-id" content="kafka-partition-rebalancing">
<meta name="ukb:review-status" content="verified">
<meta name="ukb:reviewed-at" content="2026-08-11T09:42:00-07:00">
<meta name="ukb:confidence" content="high">
<meta name="ukb:confidence-basis" content="primary-source-cited,executed-verified,human-expert-review">
<meta name="ukb:volatility" content="moderate">
<meta name="ukb:expires-at" content="2027-08-11T09:42:00-07:00">
<meta name="ukb:stale" content="false">
<meta name="ukb:agent" content="chatgpt">
<meta name="ukb:model" content="gpt-5.1">
<meta name="ukb:raw-url" content="https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/docs/kb/kafka-partition-rebalancing.md">

<script type="application/ld+json">
{
  "@context": ["https://schema.org", {"prov": "http://www.w3.org/ns/prov#"}],
  "@type": "TechArticle",
  "identifier": "kafka-partition-rebalancing",
  "name": "Kafka Partition Rebalancing: Eager vs Cooperative Protocols",
  "description": "How consumer group rebalancing works in Apache Kafka...",
  "dateCreated": "2025-11-02T14:07:00-07:00",
  "dateModified": "2026-08-11T09:42:00-07:00",
  "expires": "2027-08-11T09:42:00-07:00",
  "author": {
    "@type": "SoftwareApplication",
    "name": "chatgpt",
    "softwareVersion": "gpt-5.1",
    "applicationCategory": "AI assistant"
  },
  "prov:wasAttributedTo": {"@type": "prov:SoftwareAgent", "name": "chatgpt / gpt-5.1"},
  "editor": {"@type": "Person", "name": "Chris Lostaunau"},
  "creativeWorkStatus": "verified",
  "reviewedBy": {"@type": "Person", "name": "Chris Lostaunau"},
  "review": {
    "@type": "Review",
    "author": {"@type": "Person", "name": "Chris Lostaunau"},
    "datePublished": "2026-08-11T09:42:00-07:00",
    "reviewBody": "Checked assignor behaviour against KIP-429 and a local 3-broker cluster."
  },
  "citation": [
    {"@type": "CreativeWork", "name": "KIP-429: Kafka Consumer Incremental Rebalance Protocol",
     "url": "https://cwiki.apache.org/confluence/display/KAFKA/KIP-429"},
    {"@type": "CreativeWork", "name": "Apache Kafka 3.7 Documentation - Consumer Configs",
     "url": "https://kafka.apache.org/37/documentation.html#consumerconfigs"}
  ],
  "license": "https://spdx.org/licenses/CC-BY-4.0.html",
  "additionalProperty": [
    {"@type": "PropertyValue", "name": "confidenceLevel", "value": "high"},
    {"@type": "PropertyValue", "name": "confidenceBasis",
     "value": "primary-source-cited,executed-verified,human-expert-review"},
    {"@type": "PropertyValue", "name": "volatility", "value": "moderate"},
    {"@type": "PropertyValue", "name": "stale", "value": "false"}
  ],
  "encoding": {
    "@type": "MediaObject",
    "encodingFormat": "text/markdown",
    "contentUrl": "https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/docs/kb/kafka-partition-rebalancing.md"
  }
}
</script>
```

### 9.3 Visible footer (required by the brief)

Rendered as a bordered block at the end of every page, colour-coded by review status
(grey `unreviewed` / blue `reviewed` / green `verified` / red `deprecated`), with an amber
"Review due" strip when `stale == true`:

> **Provenance** — Created **2025-11-02** by **chatgpt (gpt-5.1)**. Last updated
> **2026-08-11** by **Chris Lostaunau (human)**.
> **Status: VERIFIED** by Chris Lostaunau on 2026-08-11.
> **Confidence: high** — basis: cited primary sources, executed and verified, human expert
> review. **Review due 2027-08-11** (moderate volatility).
> [View source markdown] · [View history]

A search-engine visitor can judge trustworthiness without opening the repo, which is the
stated requirement.

---

## 10. Three schema strategies

### Strategy A — "Minimal 8, fully flat"

Eight required scalar fields, **no nesting whatsoever**. Dotted key names instead of maps:
`created_by_agent`, `created_by_model`, `confidence_basis`, `review_status`. No per-type
extensions — language, C4 level, and so on live in the document body under a `## Metadata`
heading or are inferred from path and file extension.

- **Wins:** minimum possible friction; nested-YAML indentation errors — the single most
  common failure mode across heterogeneous tools — become *impossible*. Trivially
  greppable with plain single-line regexes: `rg '^review_status: verified'`, no `-U`
  needed. A human editing in a plain text editor cannot get it wrong.
- **Loses:** the flat namespace bloats as soon as types diverge (`code_language`,
  `code_language_version`, `diagram_c4_level`, `artifact_target_tools` — ~20 optional
  top-level keys, unclear which apply to what). Type-specific facts move into prose, where
  they are unvalidatable, so "which Python version is this valid for?" becomes
  unanswerable by machine. No structural separation of research notes.

### Strategy B — "Rich PROV-aligned"

Full W3C PROV-O modelling. Frontmatter carries `prov:Entity` identity; a sidecar
`<doc>.prov.jsonld` per document records `prov:Activity` nodes (the generation session, each
edit, each review) with `wasGeneratedBy`, `wasInformedBy`, `wasRevisionOf`,
`qualifiedAttribution`. The build assembles a repo-wide provenance graph queryable for
"every document any output of session X influenced".

- **Wins:** genuinely correct provenance semantics; answers transitive questions (a source
  was retracted — what depends on it?) that no flat schema can. Standards-interoperable.
- **Loses:** **this is the one I would fight hardest against.** It requires six
  non-communicating tools to mint consistent Activity URIs, which they will not do; the
  realistic outcome is 1,000 orphan nodes with no edges — the appearance of a graph with
  none of the value. Two files per document means they desynchronize. Sidecar JSON-LD is
  unreadable in a plain text editor, violating the graceful-degradation principle outright.
  And no ripgrep query answers anything without a graph loader. This is a 10,000-document,
  single-orchestrator design imported into a 1,000-document, six-agent one.

### Strategy C — "Layered core + typed extension" ← **PREFERRED**

Eight required fields in a lightly-nested base (`created_by`, `confidence`, `review` as
small two-to-three-key maps), plus one `type`-keyed extension object validated by
`allOf`/`if-then`. Flattened PROV subset (three predicates). Derived fields — `stale`,
`expires_at`, effective confidence level, git timestamps, content hash — computed into
`catalog.json`, never written back to markdown.

- **Wins:** the base is small enough that a naive agent gets it right from a template; the
  extensions capture the type-specific trust facts (`language_version`,
  `source_sha256`, `c4_level`) that Strategy A loses to prose; derived-not-stored means
  zero build-generated commit churn and no possibility of staleness drift; degrades
  perfectly — every field is readable and meaningful in a plain text editor with no
  tooling, and GitHub renders the frontmatter as a table for free.
- **Loses:** see below. I am not going to soft-pedal these.

### Honest downsides of my own preference

1. **Nesting is the failure mode, and I am choosing to accept it.** `confidence:\n  basis:
   [...]` is precisely where a non-Claude tool emits wrong indentation. Strategy A is
   genuinely more robust on this axis and I am trading that robustness for
   type-specific validation. Mitigations — copy-paste templates, `--fix` auto-repair, a
   pre-commit hook — reduce but do not eliminate it. At six tools this **will** produce CI
   failures, and if the failure rate proves high in the first month, the correct response
   is to flatten `confidence` and `review` to `confidence_basis` / `review_status` rather
   than to add more tooling. I would accept that reversal.
2. **The confidence ceiling table lives in Python, not in the schema.** JSON Schema cannot
   express "level ≤ max(ceiling(basis))". That is a second source of truth beside
   `document.v1.json`, and the two can drift. Mitigation is a unit test asserting the table
   against the schema's evidence enum — but it is real duplication, not an illusion of one.
3. **`volatility` is a required judgment call an agent has every incentive to fudge.**
   `evergreen` means "stop nagging me". The `W-VOLATILITY` heuristic is weak and I said so.
   The real backstop is human spot-checking during review, which is a process control, not
   a technical one. Anyone who claims their staleness system is self-enforcing is wrong.
4. **Eight required fields is still eight.** A tool that supplies none of them files
   nothing, and a knowledge base that rejects content captures less knowledge. The
   counter-argument — the one I actually believe — is that the user's stated problem is not
   "I have too little content", it is "I cannot trust the content I have". Under that
   framing rejection is the feature. But if capture rate collapses in practice, the honest
   fix is a `tools/ingest.py` that takes a bare markdown file plus CLI flags and *generates*
   conforming frontmatter, moving the friction off the contributing agent — not loosening
   the schema.
5. **`Z`-rejection and mandatory quoting are ergonomic taxes** paid by every contributor to
   buy comparability and PyYAML safety. Both are `--fix`-able, both are surprising, and both
   will generate confused first-time failures.

---

## 11. Summary of hard rulings

1. Timestamps: quoted strings, `pattern`-validated (not `format`), numeric offset only, `Z`
   rejected.
2. `updated_at` mirrors `created_at` when never updated. Not null, not blank, not a sentinel.
3. Confidence level is derived from and capped by a required structured `basis` enum.
4. Claiming a citation basis requires non-empty `sources`. Hard failure.
5. Git is the source of truth for modification time; ±24h drift tolerance; catalog publishes
   both claim and fact.
6. An agent editing an above-`unreviewed` document must reset `review.status`.
7. `research-note` can never reach `verified`.
8. Staleness is computed at build time from `volatility` + one config table, never stored in
   markdown.
9. PROV: three flattened predicates, no graph, no sidecars.
10. C2PA: hashes and git, no signing. SPDX: one identifier field.
