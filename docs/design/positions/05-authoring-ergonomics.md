# Position 05 — Authoring Ergonomics & Templates

**Expert:** Docs-as-code technical writer
**Charge:** What does an AI agent have to do to file a document correctly, and is that cheap
enough that it will actually happen every time?
**Status:** design position, for synthesis into candidate architectures
**Date:** 2026-08-14

---

## 0. Position in one paragraph

The contributors are foreign AI agents. They are impatient, they pattern-match rather than
read, they invent plausible values for any field you put in front of them, and they treat
anything that looks optional as absent. Therefore the contract must be **one file, under
2,000 tokens, template-first**, and the schema must be **shaped so that the only fields an
agent is asked for are fields it actually knows**. Every field an agent cannot honestly
know must be one of: a constant in the template, derived by the validator, or absent from
the template entirely so no slot exists to fill. I count **27 judgment calls** in a naive
filing flow and cut it to **6 judgments + 3 self-recalls + 1 shell command**. My preferred
flow is **Template + Teaching Validator** (copy-paste contract, no script dependency, with
`tools/new.py` as an optional accelerator that reads the same template files). And the
single highest-leverage anti-fabrication rule in the whole system is this: **for every
required field, ship a legitimate, blessed, non-embarrassing "I don't have this" value.**
Agents fabricate when the honest answer looks like a failure.

---

## 1. Three laws of agent authoring

These drive everything below. They are stated as laws because every concrete decision in
this document is a consequence of one of them.

**Law 1 — The template is the prompt.**
Whatever keys appear in the template will receive values. An agent shown
`reviewer:` will write a reviewer. An agent shown `shelf_life:` will write "6 months."
The template is not documentation; it is the most powerful instruction in the system,
and it instructs by *presence*. Corollary: **removing a field is a stronger control than
documenting it.**

**Law 2 — Never ask for a value the agent will invent.**
If a field requires information the agent cannot possess (who reviewed this, what the
canonical taxonomy tag is, when this will go stale), it must not be agent-writable.
Where the underlying information is genuinely useful, **convert the fabrication-prone
question into a judgment the agent can actually make.** "What is this doc's shelf life?"
is fabrication. "Does this subject change fast, moderately, slowly, or never?" is a real
judgment an agent is good at. Then derive the date.

**Law 3 — Make the honest answer legal, easy, and normal.**
`confidence: medium`, `sources: [model-knowledge]`, and `review_status: unreviewed` must
be presented as the expected, unremarkable default — not as a deficiency. The moment an
agent perceives that "unreviewed" looks bad, it writes "verified." The moment it perceives
that an empty `sources` list looks bad, it invents a URL. Design the defaults so that
telling the truth is the path of least resistance *and* the path of least apparent shame.

---

## 2. Friction budget

### 2.1 Before — every decision required to file one document (naive design)

I enumerated the decision surface of a "normal" docs-as-code repo with the provenance
requirements from the goal doc applied literally. A *decision* is a judgment call with more
than one defensible answer. A *recall* is the agent reading off a fact about itself.

| # | Decision | Class | Fabrication risk |
|---|---|---|---|
| 1 | Which of 5 content types is this? | placement | low |
| 2 | Which directory does it go in? | placement | **high** |
| 3 | What is the filename / slug format? | placement | med |
| 4 | Does the filename need a date prefix? | placement | med |
| 5 | What is the document's stable id? | placement | **high** |
| 6 | What do I do if that filename exists? | placement | med |
| 7 | What is the primary topic tag? | classification | **high** |
| 8 | What secondary tags? | classification | med |
| 9 | Is my tag in the canonical vocabulary? | classification | **high** |
| 10 | Which existing docs should I cross-link? | classification | **high** |
| 11 | Title | identity | low |
| 12 | Summary / description | identity | low |
| 13 | Tool name string (what format?) | provenance | med |
| 14 | Model id string (what format?) | provenance | med |
| 15 | Prompt / session reference | provenance | med |
| 16 | `updated_by` — human or agent? | provenance | low |
| 17 | `created_at` — format, timezone offset | time | med |
| 18 | `updated_at` — what on a new doc? | time | med |
| 19 | `review_status` | trust | **critical** |
| 20 | `reviewer` | trust | **critical** |
| 21 | `review_date` | trust | **critical** |
| 22 | `confidence` value | trust | **high** |
| 23 | `confidence_basis` | trust | med |
| 24 | Shelf life / review-by date | staleness | **critical** |
| 25 | Sources list | sources | **critical** |
| 26 | What headings must the body have? | body | med |
| 27 | Do I need to update an index / TOC / nav? | bookkeeping | **high** |

**27 decisions.** Nine of them are high or critical fabrication risk. This is a system that
will be filled with confident lies within a week, and quietly bypassed within a month.

### 2.2 The cut

| Technique | Decisions removed | How |
|---|---|---|
| **DERIVED from type** | 2 (directory), 26 (body headings) | The template file *is* the type. Copying `templates/explainer.md` fixes the directory, the body skeleton, and the constants. |
| **DERIVED from title** | 3 (slug), 5 (id) | One stated rule: lowercase, non-alphanumerics → `-`, collapse repeats, trim. Id = slug. Validator `--fix` normalizes. |
| **DELETED** | 4 (date prefix), 9 (canonical vocabulary), 20 (reviewer), 21 (review date) | No dates in filenames — they wreck link durability and readability, and the date is in frontmatter. No canonical tag vocabulary — folksonomy plus a generated tag index. `reviewer`/`reviewed_at` are simply **not in the template**; their absence is enforced. |
| **DEFAULTED to a constant in the template** | 16 (`updated_by: agent`), 19 (`review_status: unreviewed`) | Pre-filled and documented as not-agent-writable. Validator rejects any other value. |
| **DERIVED from an enum** | 24 (shelf life) | `volatility: fast\|moderate\|slow\|evergreen` → `review_by` computed by the build from a config table. |
| **MECHANICAL, not judgment** | 17, 18 | `created_at`: run `date -Iseconds`, paste. `updated_at`: paste the *identical string*. Later edits are machine-stamped. |
| **DEFERRED to validator** | 6 (collision) | Just write the natural name. If it collides, CI tells you the exact alternative or tells you to merge. |
| **DEFERRED to build** | 10 (cross-links), 27 (index/TOC) | Backlinks, tag co-occurrence, catalog, nav, `llms.txt` are all generated. An agent that hand-edits an index is doing damage. |
| **RECLASSIFIED as recall** | 13, 14, 15 | Not judgments. The agent reads its own tool name, model id, and session handle. Free-form strings; no format policing beyond non-empty. |

### 2.3 After — the minimum viable decision set

**6 judgments:**

1. **Type** — one of 5. Determines the template, and the template determines everything else.
2. **Title** — the agent already has this. Derives slug, filename, id, H1.
3. **Summary** — ≤ 60 words, one paragraph. This is the retrieval unit: it goes into
   `catalog.json`, `llms.txt`, the HTML `<meta description>`, and every card in the site.
4. **Tags** — 3–8, free-form, `lower-kebab-case`. No vocabulary to look up, no "is this the
   right tag" anxiety. Validator normalizes casing and *warns* (never fails) on near-duplicates.
5. **Volatility** — 4-value enum. A real judgment: does this subject move fast?
6. **Confidence + one-line basis + sources** — treated as a *single coupled decision*,
   because the validator couples them (rule R4 below). The agent decides "did I actually
   consult a source in this session, or am I working from model knowledge?" Everything else
   follows.

**3 recalls:** `tool`, `model`, `session_ref`.

**1 shell command:** `date -Iseconds` → pasted into `created_at` and `updated_at`.

**27 → 6.** More importantly: **zero critical-fabrication-risk fields remain agent-writable.**

---

## 3. Field writability matrix

This is the enforcement backbone. Three classes, and the validator knows which is which.

### AGENT-WRITABLE (self-knowledge and honest judgment)

| Field | Why the agent genuinely knows it |
|---|---|
| `type` | It knows what it wrote. |
| `title` | It wrote it. |
| `summary` | Summarising is its core competence. |
| `tags` | Free-form; there is no wrong answer to get wrong. |
| `tool`, `model`, `session_ref` | Facts about itself. |
| `created_at`, `updated_at` | From the system clock, not from judgment. |
| `volatility` | A genuine domain judgment it can make. |
| `confidence`, `confidence_basis` | Its own epistemic state, *if* the scale is behaviourally anchored (§4.2). |
| `sources` | It knows what it actually read this session — *if* "nothing" is a legal answer. |
| body prose, diagram source, code | The content itself. |
| `related` (optional) | Only if it links to a path that exists; validator checks. |

### HUMAN-ONLY (agent writing these is a CI failure)

| Field | Why |
|---|---|
| `review_status` values `reviewed` / `verified` | An agent asserting its own work is verified is the single worst failure mode in the system. Agents may write exactly one value: `unreviewed` (or `raw` for raw notes). |
| `reviewer`, `reviewed_at` | Must be **absent** from unreviewed docs. Absence is easier to validate than emptiness, and there is no slot for an agent to fill. |
| `reviews/ledger.yml` | The corroborating record. CODEOWNERS-protected. |
| `config/volatility.yml` | The volatility → interval mapping. |
| `config/redirects.yml` | Slug aliases when a doc is renamed. |
| Promotion of a raw note into a curated doc | Never happens in place (§9). |

### MACHINE-GENERATED-ONLY (agent writing these is a CI failure)

| Field / artifact | Generated from |
|---|---|
| `id` | Path/slug. |
| `review_by` | `created_at`/`reviewed_at` + `volatility` lookup. |
| `updated_at` **on edits after creation** | `git log -1 --format=%cI -- <path>` at build time; the stamp step rewrites frontmatter. |
| `updated_by` **on edits after creation** | Git author identity vs. the human allowlist. |
| `catalog.json`, `llms.txt`, tag index, backlinks, nav, search index | The corpus. |
| Rendered diagram output | The mermaid fence in the source doc. |
| HTML provenance footer + JSON-LD | Frontmatter + ledger + git. |

**Design note:** the only reason `updated_at` sits in frontmatter at all is that the goal doc
requires it there. Git already holds the truth. Making it agent-authored *at creation only*
(paste the same string twice) and machine-owned thereafter is the cheapest way to satisfy the
requirement without asking an agent to maintain a field it will forget to bump.

---

## 4. The fabrication problem — concrete defenses

Numbered rules, because the validator's error messages cite the rule number and an agent can
`rg R4 AGENTS.md` to find the explanation.

### 4.1 R1–R3: review status cannot be self-declared

- **R1** — `review_status` must be `unreviewed` for anything under `docs/`, and `raw` for
  anything under `raw/`. Any other value fails **unless** R2 is satisfied.
- **R2** — `review_status: reviewed|verified` is valid only when `reviews/ledger.yml`
  contains an entry whose `id` matches the document, whose `status` matches, and whose
  `reviewer` is in `config/humans.yml`. The build copies `reviewer` and `reviewed_at` into
  the published HTML from the **ledger**, never from the doc. `reviews/ledger.yml` is
  CODEOWNERS-protected so only the repo owner can merge changes to it.
- **R3** — `reviewer` and `reviewed_at` keys must be **absent** when `review_status` is
  `unreviewed` or `raw`. Not null, not `""` — absent.

This is socially rather than cryptographically enforced, and that is the correct amount of
engineering for a single-owner public repo. A foreign agent that writes `verified` gets a CI
failure with the exact replacement line; a foreign agent that *also* forges a ledger entry is
caught by branch protection on `ledger.yml`.

**Why a ledger rather than just trusting frontmatter:** the frontmatter of a doc is edited by
whoever last touched the doc — including agents doing an unrelated typo fix. The ledger is a
separate, small, human-owned file with a separate review gate. Reviews should not be
collateral damage of an edit.

### 4.2 R4: confidence is coupled to sources

Do not ask for a 0.0–1.0 float. Invented precision invites invented values. Use a 3-value
enum with **behavioural** anchors — anchors that describe what the agent *did*, not how it
*feels*:

| Value | Anchor (what you did, not how sure you feel) |
|---|---|
| `high` | I opened, read, and cited at least one external source during this session. |
| `medium` | I worked from model knowledge. It is consistent with what I know. I did not re-read a source. |
| `low` | I inferred, extrapolated, or reconstructed this. Parts may be wrong. |

- **R4** — `confidence: high` requires at least one `sources` entry beginning with `http`.
  Otherwise fail.
- **R5** — `sources` must be a non-empty list. The reserved literal `model-knowledge` is a
  **valid, normal, non-deficient** entry meaning "no external source was consulted."

R5 is Law 3 made mechanical. Without a blessed "none" value, every agent invents a URL.
The template ships with `confidence: medium` and `sources: [model-knowledge]` pre-filled, and
AGENTS.md says in as many words: *this is the expected value for most documents; leaving it
is not a failure.*

**Self-critique:** R4 creates a small perverse incentive — an agent that wants `high` can
unlock it by citing a URL it barely read. Two mitigations: (a) AGENTS.md explicitly states
that `medium` is the normal, expected value and that `high` is uncommon; (b) an optional
weekly non-blocking CI job HEAD-requests every `http` source and opens an issue listing 404s.
Hallucinated URLs 404 at a very high rate, so this is a cheap, high-yield detector. It is
YAGNI-deferrable to the point where the corpus has ~100 docs with URL sources.

### 4.3 R6: staleness is derived, never authored

- **R6** — `volatility` must be one of `fast | moderate | slow | evergreen`. `review_by` must
  be **absent** from frontmatter; it is computed by the build.

```yaml
# config/volatility.yml — human-owned
fast:      90    # days. fast-moving libraries, model APIs, pricing, cloud services
moderate:  365   # stable-ish tech: protocols, mature frameworks, org practices
slow:      1095  # foundational CS, established standards
evergreen: null  # mathematics, thermodynamics, historical facts — never goes stale
raw_default: fast   # raw notes always age visibly
```

The agent answers a question it can answer ("does this subject change fast?") instead of one
it cannot ("when should a human re-check this?").

**Honest limitation:** agents will over-select `moderate` because it is the safe middle. The
per-type defaults in the templates (snippets default `fast`, explainers default `moderate`)
partially offset this. There is a real accuracy ceiling here and I do not claim otherwise.

### 4.4 R7–R9: mechanical hygiene

- **R7** — `created_at` and `updated_at` must be ISO-8601 with an explicit UTC offset, to the
  minute (`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$`). A bare date fails.
  On creation, `updated_at` must equal `created_at`.
- **R8** — The literal token `TODO:` must not appear anywhere in frontmatter or in the body.
  All template placeholders use this one token so a single grep catches every unfilled slot,
  and the error message can report every offending line at once.
- **R9** — Body H1 must exist, must be the only H1, and must match `title` exactly. Slug must
  be globally unique across the entire corpus.

R8 is worth more than it looks. Agents partially fill templates and leave the rest. One
distinctive token, one grep, one comprehensive error message listing every line number.

### 4.5 R10–R12: containment

- **R10** — Files under `raw/` must have `type: raw-note` and `review_status: raw`. Files
  outside `raw/` must not have `type: raw-note`. (See §9.)
- **R11** — Unknown frontmatter keys fail. This catches an agent inventing
  `accuracy: 0.92` or `author: AI Assistant` and makes the schema self-teaching.
- **R12** — **The contract file has a size budget.** CI fails if `AGENTS.md` exceeds
  **200 lines or ~2,500 tokens**. See §5.1.

---

## 5. The contribution contract

### 5.1 Length, structure, and why

**Target: one file, ≤ 200 lines, ≤ ~2,000 tokens, template above the fold.**

Defence of the target:

- **Lower bound (unambiguous).** It must contain a complete, valid, copy-pasteable worked
  example, all closed vocabularies as literal lists, the path/naming rule, and the rules that
  fail CI. That is roughly 130–170 lines. You cannot get correct first-try filing below that.
- **Upper bound (read).** At ~2,000 tokens the file is cheap enough that every tool can inject
  it into every session automatically — Cursor rules, Copilot instructions, Claude Code project
  memory, a system prompt paste. Above ~4,000 tokens, tools start truncating and agents start
  skimming for what looks relevant, which means they skim past the rules and straight to the
  template. Above ~8,000 tokens it is functionally a website nobody visits.
- **Enforce it.** R12 makes the budget a CI check, exactly like a bundle-size budget. Every
  future clarification must displace something rather than accrete. This is the single
  mechanism that keeps the contract from rotting into a wiki over two years.

**One file or an index?** **One file.** An index adds a hop, and an impatient agent skips
hops. But the file does not have to carry everything: the per-type instructions live in
`templates/*.md`, which are **copy targets, not reading material**. The agent is told "copy
this file," which is an action, not a research task. Self-documenting comments *inside* the
template do the teaching at the exact moment of use. This is the difference between an index
(costly indirection) and a template library (free indirection, because the agent has to open
the file anyway to copy it).

**What happens when it exceeds what an agent will read?** Two answers, and both must be
designed in from the start because you cannot prevent overrun by hoping:

1. **Ordering is a safety property.** Inverted pyramid, most-violated rule first. Everything
   below the fold must be non-essential. If the file is truncated at 40% by a tool's context
   policy, the agent must still file correctly. Concretely: quickstart + full template in the
   first ~60 lines; vocabularies next; rationale last, or not at all.
2. **The validator is the second chance.** Assume a meaningful fraction of contributors never
   read AGENTS.md at all. Their entire education is the CI failure message (§7). Budget real
   effort there — those messages are load-bearing documentation, not diagnostics.

**Mirror files, not copies.** The six tools look for six different filenames. Each mirror is a
one-line pointer, never a duplicate (duplicates drift):

| Tool | File | Content |
|---|---|---|
| Claude Code | `CLAUDE.md` | `See @AGENTS.md — it is the complete contract.` |
| Cursor | `.cursor/rules/contributing.mdc` | pointer, `alwaysApply: true` |
| GitHub Copilot | `.github/copilot-instructions.md` | pointer |
| Codex / Gemini CLI / generic | `AGENTS.md` | the real file |
| Web-UI tools (ChatGPT, etc.) | `README.md` → link | pointer near the top |
| Agents entering via retrieval | `llms.txt` | first line links `AGENTS.md` |

A CI check asserts every mirror is ≤ 3 lines and contains the string `AGENTS.md`.

### 5.2 DRAFT `AGENTS.md`

This is the real artifact. 138 lines, ~1,450 words.

~~~~markdown
# Contributing to this knowledge base

You are an AI agent. Follow this file exactly. It is the whole contract.
Do not hand-write HTML. Do not edit any index, catalog, nav, or `llms.txt` — those are generated.

## Quickstart (do this)

1. Pick a type: `explainer` | `diagram` | `snippet` | `prompt` | `raw-note`
   Unsure, or it's raw/unpolished output? Use `raw-note`. That is a correct answer, not a fallback.
2. Copy `templates/<type>.md` to the path for that type (table below).
3. Filename = title, lowercased, every run of non-alphanumerics replaced by `-`, trimmed.
   "Kafka Partition Rebalancing" -> `kafka-partition-rebalancing.md`. No dates in filenames.
4. Fill only the lines marked `TODO:`. Leave everything else exactly as it is.
5. Run `date -Iseconds` and paste the result into BOTH `created_at` and `updated_at`.
6. Validate: `python3 tools/validate.py <your-file>` (optional but it will tell you the exact fix).

| type | path |
|---|---|
| explainer | `docs/explainers/<slug>.md` |
| diagram | `docs/diagrams/<slug>.md` |
| snippet | `docs/snippets/<slug>.md` |
| prompt | `docs/prompts/<slug>.md` |
| raw-note | `raw/<YYYY>/<slug>.md` |

Directories are flat. Do not invent subdirectories.

## The template (explainer — the common case)

```markdown
---
type: explainer
title: TODO: Human-readable title, sentence case
summary: TODO: One paragraph, max 60 words, no markdown. This is what humans and agents see first.
tags: [TODO, three-to-eight, lower-kebab-case]
tool: TODO: your product name, e.g. cursor / github-copilot / claude-code / codex / gemini-cli
model: TODO: your exact model id, e.g. claude-opus-4-6 / gpt-5.2 / gemini-3-pro
session_ref: TODO: anything that identifies the session or prompt; "not available" is acceptable
created_at: TODO: output of `date -Iseconds`
updated_at: TODO: the identical string you used for created_at
updated_by: agent
review_status: unreviewed
confidence: medium
confidence_basis: TODO: one line. e.g. "Model knowledge only; no sources consulted this session."
volatility: moderate
sources:
  - model-knowledge
---

# TODO: same text as `title` above, exactly

## TL;DR

- TODO: 3-6 bullets. A reader who stops here should still have gained something.

## TODO: first real section

TODO: body. Each `##` section must make sense quoted on its own — an agent will retrieve
it without the rest of the page. No "as mentioned above".

## What this is not

- TODO: 1-3 bullets naming the adjacent thing this is NOT about, and where to go instead.
```

## Fields you MUST NOT change

- `review_status` — you may only ever write `unreviewed` (or `raw` in `raw/`). Writing
  `reviewed` or `verified` fails CI (rule R1/R2). Only a human promotes a document.
- Do NOT add `reviewer`, `reviewed_at`, `review_by`, or `id`. They must be absent. They are
  human- or machine-owned (R3, R6, R11).
- `updated_by: agent` — leave as-is.
- Do not add frontmatter keys that aren't in the template. Unknown keys fail CI (R11).

## Fields where the honest answer is the right answer

**`confidence`** — pick by what you DID, not how sure you feel:
- `high` — you opened and cited an external source in this session. Requires an `http` source (R4).
- `medium` — model knowledge, consistent with what you know, no source re-read. **This is the
  normal value for most documents. Leaving it is not a failure.**
- `low` — inference or reconstruction; parts may be wrong. Saying `low` is useful, not embarrassing.

**`sources`** — a list of strings. Must not be empty (R5).
- A URL you actually read: `- https://kafka.apache.org/documentation/#basic_ops_consumer_group`
- Anything else, cited freely: `- "Kleppmann, Designing Data-Intensive Applications, ch. 11"`
- No external source consulted: `- model-knowledge`  <- normal and fine
- **Never invent a URL.** A fabricated citation is worse than no citation and CI link-checks them.

**`volatility`** — how fast does this SUBJECT change? The review-by date is computed from this.
- `fast` — libraries, APIs, pricing, cloud services, model behaviour (~90 days)
- `moderate` — protocols, mature frameworks, practices (~1 year)  <- default
- `slow` — foundational CS, established standards (~3 years)
- `evergreen` — mathematics, physics, history (never expires)

**`tags`** — 3-8, `lower-kebab-case`. There is no approved list; use the obvious words.
Prefer the terms someone would search for. Broad + narrow is good:
`[kafka, consumer-groups, distributed-systems]`.

## Body rules

- Exactly one `#` H1, and it must match `title` character-for-character (R9).
- First section is `## TL;DR`, 3-6 bullets.
- Explainers must end with `## What this is not` (1-3 bullets). This is how a reader and a
  retrieval system tell "Kafka the broker" from "Kafka the novelist".
- Heading depth max `###`. Sentence case. Never skip a level.
- Every `##` section must stand alone when quoted out of context.
- Fenced code blocks must declare a language: ```python, not ```.
- Link to other docs with relative paths. Broken links fail CI.

## Other content types

Copy the matching template; the same rules apply. Type-specific notes:

- **diagram** — ONE markdown file. Put the Mermaid inside a ```mermaid fence in the body.
  Do not create `.svg`, `.png`, or `.mmd` files; the build renders them. Set `diagram_kind`
  (`c4-context`|`c4-container`|`c4-component`|`c4-code`|`sequence`|`er`|`state`|`flow`).
- **snippet** — set `language` and `verified_against` (e.g. `python 3.12`, `kafka 3.7`).
  Default `volatility: fast`.
- **prompt** — the reusable prompt/skill goes in a fenced block. Set `intended_tool`
  (or `any`). Say what it is for and when it fails.
- **raw-note** — unedited or lightly-edited AI output. `review_status: raw`. It is rendered
  with a warning banner, excluded from search, and never cited as authoritative. Raw notes are
  never promoted in place: a human writes a NEW explainer that references the note.

## If CI fails

Read the message. It names the file, the line, the rule number, and the exact replacement
text. Apply it literally. `python3 tools/validate.py --fix <file>` fixes everything mechanical
(slugs, casing, derived fields) and refuses to touch anything requiring judgment.

## Optional accelerator

If you can run commands:

    python3 tools/new.py explainer "Kafka partition rebalancing" \
        --tool cursor --model gpt-5.2 --session "thread: rebalance storm"

Stdlib only. It reads the same `templates/*.md` files, fills what it can, prints the path.
Copy-pasting the template by hand is equally valid — the script is a convenience, not the contract.
~~~~

**Note on the draft:** it is 138 lines, comfortably under the 200-line budget, with the
complete template in the first 60 lines. A tool that truncates this file at 40% still gives
an agent the type list, the path table, the filename rule, and the full template. That is the
design goal of the ordering.

---

## 6. Templates

Living at `templates/*.md`. Two shown in full, three shown complete but tighter. Note what is
*absent*: no `reviewer`, no `reviewed_at`, no `review_by`, no `id`, no `related` — each of
those would be filled with a fabricated value purely because the key existed (Law 1).

### 6.1 `templates/explainer.md`

Shown in full inside AGENTS.md above; the file on disk is byte-identical to that block. **This
matters:** the template must exist in exactly one place. AGENTS.md embeds it and a CI check
asserts the embedded copy matches `templates/explainer.md`. Otherwise they drift within a month.

Worked result after an agent fills it:

```markdown
---
type: explainer
title: Kafka partition rebalancing
summary: >-
  How Kafka reassigns partitions among consumers in a group, why rebalances stop
  consumption, and what eager, cooperative-sticky, and static membership change about
  that. Covers the trigger conditions and the settings that control rebalance duration.
tags: [kafka, consumer-groups, rebalancing, distributed-systems]
tool: cursor
model: gpt-5.2
session_ref: "cursor chat 2026-08-14, thread 'rebalance storm in prod'"
created_at: 2026-08-14T09:32:00-07:00
updated_at: 2026-08-14T09:32:00-07:00
updated_by: agent
review_status: unreviewed
confidence: medium
confidence_basis: "Model knowledge; consistent with Kafka 3.x behaviour as I recall it, not re-read."
volatility: moderate
sources:
  - model-knowledge
---

# Kafka partition rebalancing

## TL;DR

- A rebalance reassigns partitions across a consumer group; with the eager protocol every
  consumer stops consuming for its duration.
- Triggers: member join, member leave, session timeout, subscription change, partition count change.
- `cooperative-sticky` assignment removes the global stop-the-world pause.
- Static group membership (`group.instance.id`) prevents rebalances on rolling restarts.
- Most "rebalance storms" are a `max.poll.interval.ms` problem, not a Kafka problem.

## Why rebalancing exists

...

## What this is not

- Not about *partition reassignment* between brokers (`kafka-reassign-partitions.sh`) —
  that is data movement, not consumer coordination. See `docs/explainers/kafka-partition-reassignment.md`.
- Not about Kafka Streams task assignment, which layers its own logic on top.
```

### 6.2 `templates/diagram.md`

The important ergonomic claim: **one file, not three.** The naive design has an agent produce
`foo.mmd` + `foo.svg` + `foo.md` and keep them consistent. That is three placement decisions,
a rendering step the agent cannot perform, and a guaranteed drift source. Instead the mermaid
source lives in a fence in the document; the build extracts and renders it. "Source plus
rendered, both provenance-tracked" is satisfied, and the agent's job drops to "write a fenced
block" — something every one of these tools does correctly a thousand times a day.

~~~~markdown
---
type: diagram
title: TODO: what the diagram shows, sentence case
summary: TODO: one paragraph, max 60 words. Name the system and what a reader learns from it.
tags: [TODO, lower-kebab-case]
diagram_kind: TODO: c4-context | c4-container | c4-component | c4-code | sequence | er | state | flow
subject: TODO: the system/domain being diagrammed, e.g. "acme-billing-platform"
tool: TODO
model: TODO
session_ref: TODO
created_at: TODO: output of `date -Iseconds`
updated_at: TODO: identical to created_at
updated_by: agent
review_status: unreviewed
confidence: medium
confidence_basis: TODO: e.g. "Drawn from the repo's source; container boundaries inferred from deploy manifests."
volatility: fast
sources:
  - model-knowledge
---

# TODO: same as `title`

## TL;DR

- TODO: 3-6 bullets. What are the boxes, and what is the one insight the picture carries?

## Diagram

```mermaid
TODO: your mermaid source here. Do NOT create .mmd or .svg files — the build renders this.
```

## Legend and assumptions

- TODO: what each element means, and anything you inferred rather than confirmed.
  Be explicit about inference. This is the field a reader most needs and most rarely gets.

## What this is not

- TODO: which C4 level this is NOT, and where the neighbouring level lives.
~~~~

Note `volatility: fast` is the diagram default — architecture diagrams go stale faster than
almost anything else, and a stale C4 container diagram is actively harmful.

### 6.3 `templates/snippet.md` (frontmatter + skeleton)

~~~~markdown
---
type: snippet
title: TODO
summary: TODO: one paragraph, max 60 words. What problem does this solve?
tags: [TODO]
language: TODO: python | typescript | bash | sql | yaml | ...
verified_against: TODO: exact versions this was valid for, e.g. "python 3.12, psycopg 3.2".
                  If you did not run it, write "not executed".
runnable: TODO: true | false
tool: TODO
model: TODO
session_ref: TODO
created_at: TODO
updated_at: TODO
updated_by: agent
review_status: unreviewed
confidence: medium
confidence_basis: TODO
volatility: fast
sources:
  - model-knowledge
---

# TODO: same as `title`

## TL;DR
- TODO: what it does, in one bullet. When to reach for it, in another.

## Code
```TODO-language
TODO
```

## How to run it
TODO: exact commands, and what correct output looks like.

## Caveats
- TODO: what it does NOT handle. Error paths, scale limits, security notes.
~~~~

`verified_against` with the blessed literal `not executed` is Law 3 again. Without that
escape, agents write `python 3.12` for code they never ran.

### 6.4 `templates/prompt.md` (frontmatter + skeleton)

~~~~markdown
---
type: prompt
title: TODO
summary: TODO: one paragraph, max 60 words. What does this prompt make a model do?
tags: [TODO]
intended_tool: TODO: claude-code | cursor | copilot | codex | gemini-cli | any
artifact_kind: TODO: prompt | skill | agent-config | system-prompt
tool: TODO
model: TODO
session_ref: TODO
created_at: TODO
updated_at: TODO
updated_by: agent
review_status: unreviewed
confidence: medium
confidence_basis: TODO: e.g. "Used successfully ~5 times in this session." or "Untested draft."
volatility: fast
sources:
  - model-knowledge
---

# TODO: same as `title`

## TL;DR
- TODO: what it is for, and the one situation it is worth reaching for.

## The prompt
```text
TODO: the verbatim reusable text. No commentary inside the fence.
```

## How to use it
TODO: where it goes (system prompt / rules file / slash command), and what to substitute.

## When it fails
- TODO: observed failure modes. If you have not tested it, say so here explicitly.
~~~~

### 6.5 `templates/raw-note.md` (frontmatter + skeleton)

~~~~markdown
---
type: raw-note
title: TODO: what the session was about
summary: TODO: one paragraph, max 60 words. What question were you answering?
tags: [TODO]
review_status: raw
tool: TODO
model: TODO
session_ref: TODO
created_at: TODO
updated_at: TODO
updated_by: agent
confidence: low
confidence_basis: TODO: raw output; state anything you know to be shaky.
volatility: fast
sources:
  - model-knowledge
---

> **RAW AI OUTPUT — NOT REVIEWED.** Unedited or lightly edited output kept for reference.
> Do not cite as authoritative. Do not feed to another agent as verified context.

# TODO: same as `title`

## TL;DR
- TODO: 2-4 bullets. What is actually in here?

## Raw output

TODO: paste it.

## What a curator should check
- TODO: the specific claims you are least sure about. This is the most valuable
  section in the file — it is the to-do list for whoever curates this later.
```
~~~~

Note the defaults are inverted: `confidence: low`, `volatility: fast`, `review_status: raw`,
and a blockquote warning inside the markdown itself so the warning survives a raw
`raw.githubusercontent.com` fetch with no HTML rendering. Also note the raw-note template has
**fewer** TODOs than any other — filing raw output must be the cheapest action in the system,
or it will be filed as an explainer instead.

---

## 7. Validator error messages as documentation

Design rules for every message: **file:line**, the offending value, one clause of *why it
matters to a reader* (not "schema violation"), the **exact replacement text**, a rule id to
grep, and — where a choice exists — the options framed so the honest one is not the losing one.
Never say "see AGENTS.md" as the fix; that assumes a re-read that will not happen.

### 7.1 Self-declared review status

```
FAIL  docs/explainers/kafka-partition-rebalancing.md:11  [R1]
  field:  review_status
  found:  verified
  Only a human can set review_status. There is no entry for this document in
  reviews/ledger.yml, so "verified" is unsupported — and it would tell every
  downstream reader and agent that a person checked this, when nobody has.

  Fix — replace line 11 with exactly:

    review_status: unreviewed

  Also delete these lines if present (they must be ABSENT, not empty) [R3]:
    line 12:  reviewer: AI Assistant
    line 13:  reviewed_at: 2026-08-14

  Values you may write:        unreviewed
  Values only a human may set: reviewed, verified

  "unreviewed" is the normal state for a new document. It is not a defect and it
  does not reduce the document's visibility. A human promotes it later.
```

### 7.2 High confidence with no citable source

```
FAIL  docs/explainers/crispr-base-editing.md:16  [R4]
  fields: confidence = high
          sources    = [model-knowledge]
  "high" is reserved for documents where you opened and cited a source during
  this session. You cited none, so a reader cannot check anything you wrote.

  Fix — choose ONE. Both are correct outcomes; neither is a failure:

  (a) You did read sources. List the ones you actually opened:

        sources:
          - https://www.nature.com/articles/the-exact-page-you-read
          - "Anzalone et al. 2019, Nature 576, prime editing"

  (b) You worked from model knowledge. Then write:

        confidence: medium
        confidence_basis: "Model knowledge only; no sources consulted this session."
        sources:
          - model-knowledge

  (b) is the expected outcome for most documents in this repo.
  Do NOT invent a URL to unlock (a). Fabricated citations are link-checked and
  are worse than no citation at all.
```

### 7.3 Timestamp without a timezone, plus unfilled placeholders

```
FAIL  docs/snippets/pg-connection-pooling.md  [R7, R8]

  line 9   created_at: 2026-08-14
           A bare date is ambiguous by up to 26 hours across timezones, which
           breaks staleness sorting and "what changed since" queries.

           Fix — replace line 9 with exactly:
             created_at: 2026-08-14T09:32:00-07:00

           Get the value by running:  date -Iseconds
           If you truly cannot know the local time, use  2026-08-14T00:00:00Z

  line 10  updated_at: TODO: identical to created_at
           On a NEW document, updated_at is the same string as created_at.
           Later edits are stamped automatically; you never maintain this field.

           Fix — replace line 10 with exactly:
             updated_at: 2026-08-14T09:32:00-07:00

  3 more unfilled placeholders remain. Every one contains the token "TODO:":
    line 6   verified_against: TODO: exact versions ...
    line 31  ## How to run it  ->  TODO: exact commands ...
    line 36  - TODO: what it does NOT handle ...

  Find them all yourself with:  rg 'TODO:' docs/snippets/pg-connection-pooling.md
  Mechanical issues (slugs, casing, derived fields) can be auto-fixed with:
    python3 tools/validate.py --fix docs/snippets/pg-connection-pooling.md
  It will not touch anything that needs judgment.
```

### 7.4 Bonus — wrong place / invented key

```
FAIL  raw/2026/kafka-rebalance-notes.md:3  [R10, R11]
  found:  type: explainer
          accuracy: 0.92
  Files under raw/ are unreviewed AI output and must declare themselves as such,
  or they get read as curated documentation by both humans and agents.

  Fix — either:
  (a) It IS raw output. Replace line 3 with:  type: raw-note
      and ensure line N reads:                review_status: raw
  (b) It is a finished explainer. Then MOVE it:
        git mv raw/2026/kafka-rebalance-notes.md docs/explainers/kafka-rebalance-notes.md
      and keep type: explainer.

  Also delete line 4 entirely:  accuracy: 0.92
  "accuracy" is not a field in this schema and invented numeric scores are not
  accepted [R11]. Express uncertainty with confidence: high|medium|low plus a
  one-line confidence_basis. Valid keys for type raw-note:
    type, title, summary, tags, review_status, tool, model, session_ref,
    created_at, updated_at, updated_by, confidence, confidence_basis,
    volatility, sources
```

---

## 8. Body conventions

Frontmatter serves machines; the body has to serve a human skimming *and* an agent retrieving
a chunk. These are the conventions I would require, each with the reason it earns its cost.

| Convention | Required? | Why it earns its place |
|---|---|---|
| Single H1, exact match to `title` | Yes (R9) | Trivially machine-checkable; prevents the frontmatter/body drift that makes catalog entries lie. |
| `summary` in frontmatter, ≤ 60 words, prose | Yes | The *retrieval unit*. It is what goes into `catalog.json`, `llms.txt`, `<meta description>`, and every card on the site. An agent triaging 40 candidates reads only this. |
| `## TL;DR`, 3–6 bullets, first section | Yes | Different granularity and different audience from `summary`. Prose for machines and cards; bullets for a human skimming on a phone. This is the one place I add a requirement rather than remove one, and I defend it: the bullets are the highest-value 20 seconds on the page. |
| `## What this is not`, 1–3 bullets | Yes, explainers only | The cheapest disambiguation in a 200-topic corpus. "Kafka the broker" vs. "Kafka the novelist", C4 container vs. component, rebalancing vs. reassignment. It bounds hallucination at retrieval time and it costs the author 30 seconds. |
| Every `##` section stands alone when quoted | Yes (convention, warn-only) | H2s are the natural chunk boundary for any retrieval scheme. "As mentioned above" is a chunk-poisoning phrase. Warn-only because it is not reliably machine-checkable; a lint that greps for `as (mentioned|described|noted) above` catches most of it. |
| Max depth `###`, sentence case, no skipped levels | Yes | Predictable anchors, predictable chunking, readable ToC. Skipped levels break generated navigation. |
| Fenced code blocks declare a language | Yes | Syntax highlighting, and it lets the build extract snippets for testing later. |
| Internal links relative, checked in CI | Yes | Link rot is the fastest way a knowledge base dies. |
| No `## Sources` section in the body | Yes — forbidden | It duplicates frontmatter and the two will diverge. The build renders sources into the page footer from frontmatter. One source of truth. |
| Slug globally unique across the corpus | Yes (R9) | Enables `/d/<slug>` short URLs and a `redirects.yml` alias map, so links survive a doc moving between directories. |

**Deliberately NOT required:** word-count minimums, a mandatory "Further reading" section, a
"Prerequisites" section, structured "Audience:" lines, or Diátaxis quadrant labelling. Each is
plausible; each adds a decision; none of them changes whether the right document gets found.
YAGNI.

---

## 9. Keeping raw notes from drifting into curated

This is the type most likely to quietly corrupt the corpus, because raw output *looks like* a
document. Defence in depth, six layers, each independently sufficient to raise suspicion:

1. **Path.** `raw/<YYYY>/` — a top-level sibling of `docs/`, not a subdirectory of it. The
   path appears in every URL, every ripgrep hit, every citation, and every `catalog.json`
   entry. Path is the strongest signal available because it cannot be lost in transmission.
2. **A separate review vocabulary.** `review_status: raw` is not on the
   `unreviewed → reviewed → verified` ladder — it is off the ladder entirely (R10). There is
   no in-place path from `raw` to `verified`. That is the structural core of this defence.
3. **No promotion in place.** Curating a raw note means a human writes a **new** document in
   `docs/` that references the note (`derived_from: raw/2026/<slug>.md`). The raw note stays
   raw forever. This means a link to a raw note can never silently become a link to something
   that claims to be verified — the URL you cited is the artifact you saw.
4. **In-band warning.** A blockquote banner inside the markdown, above the H1. This survives a
   raw `raw.githubusercontent.com` fetch with no HTML, no frontmatter parsing, and no catalog
   — the exact case where an agent is most likely to misread the content.
5. **Build treatment.** `[RAW]` prefix in `<title>` (visible in browser tabs and search
   results), a persistent high-contrast banner that does not scroll away,
   `<meta name="robots" content="noindex">`, excluded from the site search index, and listed
   in `llms.txt` under a separate clearly-labelled section rather than the main corpus.
6. **Catalog default.** `catalog.json` marks raw notes, and the documented default query in
   AGENTS.md and `llms.txt` **excludes** them. An agent must opt in explicitly to retrieve
   raw material.

**Counterintuitive design choice:** filing a raw note must be the *cheapest* action available —
fewer TODOs than any other template, and AGENTS.md says in the first five lines that
"unsure → raw-note" is a correct answer rather than a fallback. If raw-note filing is more
expensive than explainer filing, agents will file raw output as explainers, and the entire
containment scheme is defeated at step zero. **The quarantine only works if the door is wide
open.**

---

## 10. Contribution-flow strategies

Three genuinely distinct flows, for the synthesis into candidate architectures.

### Strategy A — "Inbox / Drop Zone"

The foreign agent writes to `inbox/` with 5 fields (`type`, `title`, `summary`, `tool`,
`model`) and stops. A local script or the repo owner runs `tools/file.py`, which normalises,
derives, slugs, and moves documents into the taxonomy.

- **Wins:** absolute minimum friction for the foreign agent. Nothing it can get wrong except
  the type. Highest raw capture rate — and capture is the stated point of the project.
- **Loses:** the inbox becomes a landfill within a month; requires an active human curator
  loop forever; documents are invisible and unpublished until filed; two states of truth;
  and the moment the owner is busy for three weeks, the system is just a folder of files —
  which is precisely the problem this repo exists to solve.
- **Variant:** intake via `gh issue create` with an issue-form template, converted by an
  Action. Enforces fields at entry and needs no clone. Costs an Action, bot commits, and a
  detour that agents *with* repo write access will find strange and skip.

### Strategy B — "Template + Teaching Validator" (my preference)

The foreign agent copies `templates/<type>.md`, fills the `TODO:` lines, saves it at the
dictated path, and commits. CI validates. Failures teach with exact, copy-pasteable fixes
(§7). `tools/new.py` exists as an optional accelerator, and `tools/validate.py --fix` cleans
up everything mechanical.

- **Wins:** no runtime dependency — works for a sandboxed agent, a web-UI tool doing a file
  export, or a human with a text editor. Degrades gracefully: if every script in the repo were
  deleted, the templates are still valid, readable markdown and the conventions still hold.
  Documents land in their final home immediately. The template does the teaching at the moment
  of use, which is the only moment an agent is paying attention.
- **Loses:** agents mangle YAML (indentation, smart quotes, "improving" the comments,
  helpfully dropping fields they judge optional). First-try pass rate realistically 70–80%.
  CI is *asynchronous* teaching — an agent that pushes and exits never reads the error, so
  correction depends on the human noticing or a PR bot comment landing where someone looks.

### Strategy C — "Scaffold Script First"

`tools/new.py` is the only sanctioned path. AGENTS.md shrinks to ~25 lines that mostly say
"run this command, then write prose into the file it created."

- **Wins:** highest correctness when it runs — every derived field is correct by construction,
  timestamps are real, slugs are canonical, fabrication-prone fields never appear. The contract
  file gets small enough that no agent can fail to read it.
- **Loses:** a hard dependency that a meaningful fraction of contributors cannot satisfy —
  web-UI tools, restricted-sandbox agents, tools that only edit files. When the script cannot
  run there is *no documented fallback*, so those contributors either invent their own format
  or give up. Violates "degrade gracefully": if `new.py` breaks under a future Python, filing
  stops entirely rather than degrading.

### Recommendation

**Strategy B, with C's script as a non-authoritative accelerator, and one part borrowed from A.**

The borrowed part is the important bit, and it is a synthesis rather than a compromise:
**make the inbox a content type instead of a staging area.** `raw-note` is the low-friction
drop zone, and it lives *inside* the taxonomy — validated, published, provenance-tracked,
visibly quarantined. "I can't be bothered to file this properly" therefore has a correct,
legitimate, permanently-valid answer that does not produce a garbage explainer and does not
create a backlog that depends on a human to drain. Strategy A's capture rate, without
Strategy A's landfill.

Two implementation constraints on B that are not optional:

1. **`new.py` must read `templates/*.md`** rather than embedding its own copy of the
   frontmatter. One source of truth, or the script and the template diverge within a month
   and start teaching contradictory things.
2. **AGENTS.md must embed the explainer template verbatim**, with a CI check asserting the
   embedded copy matches `templates/explainer.md` byte-for-byte. Same reason.

### Honest downsides of my preference

- **~20–30% first-try failure rate.** Copy-paste plus YAML equals mangling. I am trading
  first-try correctness for universal accessibility, and I think that is right — but it is a
  real trade, not a free lunch, and it means CI will be red often at first.
- **CI teaches asynchronously.** The foreign agent has usually left. My error messages are
  written for an agent that will read them, and a fraction never will. The realistic recovery
  path is the human running `--fix` or pasting the error back into the tool. Partial mitigation
  only.
- **Two paths to maintain** (template and script). Mitigated by the single-source constraints
  above, but it is still two things.
- **`volatility` will skew to `moderate`.** Agents choose the safe middle. Per-type defaults
  offset this partially. Real accuracy ceiling.
- **`## What this is not` will produce filler** in maybe a third of documents. I still want it:
  a weak "what this is not" section costs a reader five seconds, and a good one saves a
  retrieval system from a wrong answer.
- **R4 creates a mild incentive to cite weakly.** Documented and mitigated (§4.2), not solved.
- **The 200-line budget on AGENTS.md will hurt** the first time something genuinely needs
  explaining and there is no room. That pain is the mechanism working. Every addition must
  displace something.

---

## 11. Dependencies on other experts' decisions

Flagged so the synthesis does not silently break my ergonomics:

- **Information architect:** I assume **flat directories per type**. Any topic-based
  subdirectory scheme reintroduces decision #2 ("which folder?"), which is both the most
  expensive and the most fabricated decision in the naive list. If a topic exceeds ~20
  documents, my proposed escape valve is that a *human* creates one level of nesting and the
  validator accepts it; slugs stay globally unique so links resolve regardless. I will argue
  hard against agent-chosen directories.
- **Metadata specialist:** I have made `sources` a **list of plain strings** with the reserved
  literal `model-knowledge`, and `tool`/`model`/`session_ref` **flat rather than nested under
  `created_by`**. Both choices are deliberately mangle-tolerant — nesting is what agents break
  most often. If richer structure is needed, please take it via `validate.py --fix` normalising
  strings into objects at build time rather than by asking agents to author nested YAML.
- **Diagram specialist:** I have assumed **one file per diagram** with the Mermaid inline in a
  fence, and the build extracting and rendering it. Sidecar `.mmd`/`.svg` files would add three
  decisions and a guaranteed drift source; I would need convincing.
- **DX/automation:** the validator is the primary teaching surface, not a diagnostic tool.
  Its error-message quality is a feature with a budget, and `--fix` is required, not optional.
  Also please implement R12 — the size budget on `AGENTS.md` — as a real CI check.
- **Retrieval engineer:** frontmatter `summary` is the retrieval unit and `##` sections are the
  chunk boundary. If your chunking wants different boundaries, tell me now and I will change
  the body conventions rather than have two competing structures.
