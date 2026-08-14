# Position 07 — Build, Validation, and CI

**Role:** DX / Automation Engineer
**Charge:** What runs on every commit so the repo cannot rot?
**Status:** proposal for the design panel
**Author:** DX/automation expert seat

---

## 0. Executive summary

- **Language: Python 3.12, single runtime, four dependencies, zero installs needed today.**
  I verified that `markdown-it-py 3.0.0` is *already installed* on this machine
  (`/usr/lib/python3/dist-packages/markdown_it`). The brief's premise that "Python needs a
  markdown renderer it doesn't have" is factually wrong here. That single fact removes the
  only real argument for Node.
- **Full rebuild at 1,000 documents takes 5.15 seconds.** Measured, not estimated, on a
  synthetic 1,000-document / 6.2 MB corpus. Incremental build is YAGNI by a factor of six.
- **The validator is a registry of small pure functions**, each with a stable error code and
  a declared severity, each backed by exactly one deliberately-broken fixture.
- **Determinism is enforced by `git diff --exit-code` after rebuild, plus a double-build
  byte-comparison, plus a test that bans `datetime.now`/`random`/`hash()` from build code.**
- **Collisions are prevented at the path level**, not detected after the fact, via a
  content-derived ID suffix that the validator can recompute.

Every performance number in this document was measured on this machine. Commands and
outputs are in Appendix A.

---

## 1. Language decision

### The decision

**Python 3.12 for everything — validator, build, catalog, and tests. One runtime. No npm.
No second language. Four third-party packages, all of which are already installed.**

### The paragraph

The decision turned on a fact I checked rather than assumed: `markdown-it-py 3.0.0` is
already present in system `dist-packages`, alongside `PyYAML 6.0.1` (with the libyaml C
loader), `jsonschema 4.10.3`, and `mdurl 0.1.2`. markdown-it-py is a direct, spec-compliant
port of JS markdown-it — same CommonMark engine, same token-stream API — so the one
capability that supposedly forced Node is already sitting on disk, pure-Python, with a single
transitive dependency. That reduces the choice to its real terms: Python needs **four**
pure-Python packages that are all Debian-packaged and years-stable, while an equivalent Node
build (`markdown-it` + `gray-matter` + `ajv` + a CLI framework) pulls 40–80 transitive
packages, a lockfile that must stay in sync, an `npm audit` feed that will start shouting
within a year, and a runtime whose LTS window **ends in April 2027 — inside our three-year
horizon** — against Python 3.12's October 2028. The tiebreaker is that our contributors are
AI agents: with Python, an agent that lands in this repo runs `python3 tools/kb.py check`
and it works with no install step, no network, and no lockfile to corrupt; with Node it must
first run `npm ci`, which is a network round-trip, a failure mode, and an invitation for an
agent to "helpfully" run `npm install` and mutate the lockfile in its PR. A two-runtime split
is worse than either pure option — two setup steps, two version pins, two caches, two ways to
fail, and a cross-process JSON boundary that itself needs tests — and it buys only one thing:
build-time Mermaid SVG rendering, which drags in `mermaid-cli` and therefore **headless
Chromium via Puppeteer**, roughly 150 MB of download and the least reliable component in any
CI pipeline. I would rather ship Mermaid as a vendored, version-pinned `mermaid.min.js` that
renders client-side (satisfying "no external runtime API" because it is committed, not
CDN-fetched) and keep the build single-runtime, single-language, and installable-by-doing-
nothing. Pin the four packages in a hash-locked `requirements.txt` at exactly the versions
installed here, so local and CI are byte-identical rather than merely compatible.

### Dependency ledger

| Package | Version | Pure Python | Role | Rot risk |
|---|---|---|---|---|
| PyYAML | 6.0.1 | C accel, wheels | frontmatter parse | very low |
| jsonschema | 4.10.3 | yes | schema conformance (Draft 2020-12 verified working) | very low |
| markdown-it-py | 3.0.0 | yes | markdown → HTML + token stream | very low |
| mdurl | 0.1.2 | yes | transitive of markdown-it-py | very low |

Everything else is stdlib: `json`, `hashlib`, `html.parser`, `datetime`, `subprocess`,
`pathlib`, `unittest`, `http.server` (for `make serve`), `sqlite3` (available, **not used** —
see §3.6).

Use preset `"default"`, **not** `"gfm-like"`. Verified: `gfm-like` raises
`ModuleNotFoundError: Linkify enabled but not installed` because `linkify-it-py` is absent.
`"default"` gives CommonMark + tables + strikethrough with zero extra dependencies.

### What I am giving up, honestly

1. **No true Mermaid validation.** I can lint diagram source structurally (known diagram-type
   keyword, balanced brackets, no tabs) but I cannot prove a diagram renders without a
   browser. A broken diagram *will* reach production someday. Partial mitigation: GitHub's own
   markdown renderer displays Mermaid errors when browsing source, which is a free second
   pair of eyes.
2. **No Pagefind/lunr.** The JS static-search ecosystem is genuinely better than anything I
   will hand-roll. My counter is that a generated inverted index over 1,000 titles, tags, and
   headings is a ~300 KB JSON file and about 60 lines of code, and that agents will use
   `catalog.json` + ripgrep anyway.
3. **markdown-it-py has a thinner plugin ecosystem** than JS markdown-it (`mdit-py-plugins`
   exists but is not installed). Footnotes, admonitions, and heading anchors have to be
   written as small local rules. Heading anchors I need anyway for anchor-link validation, so
   that one is not a real loss.

---

## 2. The validator

### 2.1 Architecture

Three scopes, because the scope determines testability:

- **`document`** — pure function of one parsed document. Trivially unit-testable. Most checks.
- **`corpus`** — sees all documents (duplicate IDs, link resolution, orphans, near-duplicates).
- **`repo`** — sees git history (the `updated_at` reconciliation check). One injectable seam.

Each check is registered with a decorator:

```python
@check(code="KB024", severity=ERROR, scope="document",
       title="verified requires a human reviewer")
def verified_needs_human(doc, ctx):
    r = doc.meta.get("review", {})
    if r.get("status") == "verified" and r.get("reviewer", {}).get("kind") != "human":
        yield Finding(line=doc.line_of("review"),
                      msg="'verified' requires reviewer.kind: human; got %r"
                          % r.get("reviewer", {}).get("kind"),
                      fix="Set review.status: reviewed, or have a human add "
                          "reviewer.kind: human with reviewer.name and reviewed_at.")
```

The registry buys four things that matter: the error-code table in `AGENTS.md` is
**generated from the code** so it cannot drift; the meta-test "every registered code has
exactly one bad fixture that triggers it and nothing else" becomes three lines; severities
are declarative and tunable in one place; and each check is a five-line pure function, which
is precisely what the TDD requirement asks for.

### 2.2 Three verified YAML traps that shape the design

These are not hypothetical. I reproduced all three (Appendix A).

**Trap 1 — unquoted ISO timestamps are silently coerced to `datetime`.**

```
created_at: 2026-08-14T06:13:00-07:00     ->  datetime(2026,8,14,6,13, tz=UTC-07:00)
updated_at: '2026-08-14T06:13:00-07:00'   ->  str
```

The parsed value cannot tell you whether the author wrote ISO 8601 or YAML's looser
`2026-08-14 06:13:00 -07:00`, and a `safe_dump` round-trip drops the `T`. **Consequence: the
timestamp format check must run against the RAW frontmatter string via regex, before YAML
parsing decides what it means.** This is why the frontmatter splitter (test 1) must return
raw text and line numbers, not just a mapping.

**Trap 2 — duplicate keys are silently accepted; last one wins.**

```yaml
review: {status: unreviewed}
review: {status: verified}     # first one vanishes, no warning
```

An agent that appends a corrected block instead of editing in place silently overrides
provenance. Fix: a `SafeLoader` subclass with a mapping constructor that raises on repeats.
Verified working.

**Trap 3 — the Norway problem, live in our schema.**

```yaml
tags: [no, on, off, yes]   ->  [False, True, False, True]
id: 0755                   ->  493   (octal)
ver: 1.20                  ->  1.2   (trailing zero lost)
```

A tag literally named `no` or `on` becomes a boolean. Fix: a loader with the `timestamp` and
`bool` implicit resolvers removed, so scalars stay strings, plus an explicit `strict-string`
check on `tags`, `id`, and all timestamp fields. Verified working.

### 2.3 The full check table

Severity policy: **ERROR** fails CI and blocks deploy. **WARNING** is reported, annotated on
the PR, counted in the job summary, and surfaced in the weekly sweep issue, but never blocks.

The rule I applied: *a defect introduced by this commit is an ERROR; a condition that arises
from the passage of time or from legitimate ambiguity is a WARNING.* This is why staleness is
a warning — otherwise the repo spontaneously turns red on a day nobody committed, which is
exactly how a validator earns a `--no-verify` habit and dies.

#### A. Parse and structure

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB001 | Frontmatter fence `---` present at byte 0 and terminated | ERROR | Nothing downstream works without it |
| KB002 | YAML parses; **no duplicate keys** (custom loader) | ERROR | Trap 2: silent provenance override |
| KB003 | File is valid UTF-8 | ERROR | Breaks render and raw fetch |
| KB004 | LF line endings, single trailing newline | WARNING | Auto-fixable; cosmetic but keeps diffs clean |
| KB005 | Body ≥ 200 chars after frontmatter | WARNING | Stub detection; some legit stubs exist |
| KB006 | File size ≤ 512 KB (md) / 2 MB (asset) | WARNING | Agent dumping raw output |
| KB007 | File size ≤ 2 MB (md) / 10 MB (asset) | ERROR | Hard stop on repo bloat |
| KB008 | Only allowed extensions under `kb/` | ERROR | Blocks `.DS_Store`, `.bak`, `untitled-1.md`, agent scratch |

#### B. Schema conformance

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB010 | Validates against the JSON Schema for its `type` | ERROR | The core requirement |
| KB011 | `type` in the five-type enum | ERROR | Selects the schema; must be right |
| KB012 | No unknown frontmatter keys, except `x_`-prefixed | ERROR | Six agents will invent fields; the `x_` escape hatch prevents them fighting the validator while keeping sprawl greppable |
| KB013 | `x_` keys present | WARNING | Visibility on the escape hatch; promote to schema or delete |

#### C. Timestamps

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB014 | `created_at`/`updated_at` match strict ISO 8601 **with explicit numeric offset or `Z`**, minute precision, checked against the RAW string | ERROR | Trap 1: parsed value cannot prove format |
| KB015 | Naive (offset-less) timestamp | ERROR | "Exact with timezone" is a stated hard requirement |
| KB016 | `updated_at >= created_at` | ERROR | Internally incoherent provenance |
| KB017 | No timestamp more than 24 h in the future | ERROR | Models hallucinate dates constantly |
| KB018 | Never-updated docs set `updated_at == created_at` exactly (never null/absent) | ERROR | Brief: "must be unambiguous rather than blank-and-guessable" |
| KB019 | **`updated_at` vs git history** — file content changed in a commit whose author date is > 24 h *after* `updated_at` | ERROR | **The single most important anti-rot check.** Without it, `updated_at` decays into fiction |
| KB020 | `updated_at` more than 24 h *newer* than the last commit touching the file | WARNING | Can be legitimate (authored, committed later) |
| KB021 | On a PR: any file in the diff whose `updated_at` predates the base commit date | ERROR | Sharpest, cheapest form of KB019; catches "edited the body, forgot the stamp" at the moment it happens |

> **Implementation note, load-bearing.** KB019 must use **one** `git log --name-only
> --format=...` pass over history, never per-file `git log`. Measured on a 300-file repo:
> per-file = 3.54 s, single-pass = 0.013 s. That is ~270x at 300 files and gets worse with
> history depth; at 1,000 files the naive version alone costs more than the entire build.
> **This also forces `actions/checkout` with `fetch-depth: 0`** — the default shallow clone
> makes KB019 silently unable to see history, which would be a check that passes while
> measuring nothing.

#### D. Identity and naming

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB030 | `id` matches `<type>.<slug>.<suffix>` pattern | ERROR | Addressing depends on it |
| KB031 | `id` globally unique | ERROR | Catalog integrity |
| KB032 | **`id` suffix equals the recomputed content hash** | ERROR | Makes the ID unforgeable and un-copy-pasteable (§5) |
| KB033 | `id` agrees with the filename | ERROR | Path and catalog must not disagree |
| KB034 | Slug is lowercase ASCII kebab, ≤ 60 chars, no leading/trailing/double hyphen | ERROR | Pages path gotchas; `--` is the reserved suffix separator |
| KB035 | Two paths differing only by case | ERROR | Breaks on macOS/Windows checkouts and on Pages |
| KB036 | Same slug, different suffix (near-duplicate doc) | WARNING | Two agents' takes are often both worth keeping; auto-blocking destroys content (§5) |
| KB037 | Same slug + same tags + body length within 20 % | WARNING | Probable true duplicate; goes to the dedup queue |
| KB038 | Path segment with space, uppercase, or non-ASCII | ERROR | URL and casing hygiene |

#### E. Provenance

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB040 | `provenance.tool` present and in `vocab/tools.yml` | ERROR | Prevents "claude" / "Claude Code" / "claude-code" / "ClaudeCode" becoming four tools. Fix cost is one line in a vocab file, and the error message prints that line |
| KB041 | `provenance.model` present and non-empty | ERROR | Trust is model-specific |
| KB042 | `provenance.model` not in `vocab/models.yml` | WARNING | Models ship faster than vocab PRs |
| KB043 | `provenance.session_ref` present, or explicitly `null` with `session_ref_reason` | WARNING | Not every tool can emit one |
| KB044 | `updated_by` entries: agents carry tool+model, humans carry a name | ERROR | "human vs agent" is a stated requirement and must be decidable |
| KB045 | `updated_by` ordering is chronologically consistent | WARNING | Cheap coherence check |

#### F. Review lifecycle and trust

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB050 | `review.status` in `unreviewed`/`reviewed`/`verified`/`superseded` | ERROR | Lifecycle is the trust contract |
| KB051 | `reviewed`/`verified` requires `reviewer` + `reviewed_at` | ERROR | An unattributed review is not a review |
| KB052 | **`verified` requires `reviewer.kind: human`** | ERROR | **The load-bearing trust check.** A model self-certifying as verified defeats the entire premise of the repo |
| KB053 | `reviewed` with an agent reviewer | WARNING | Agent review is weaker but real; `verified` is the line |
| KB054 | `reviewer` not equal to `provenance.tool` for `verified` | ERROR | No self-certification, even by a differently-named agent identity |
| KB055 | `reviewed_at` ≥ `created_at`, not in the future | ERROR | Incoherent |
| KB056 | **`review.content_sha256` matches the current body hash** while status is `reviewed`/`verified` | ERROR | **Without this, `verified` becomes a lie the instant anyone edits the body.** Cheap (`hashlib` over the body) and closes the biggest hole in review-status systems |
| KB057 | Reviewer in `vocab/reviewers.yml` | WARNING | Attribution hygiene |

#### G. Confidence and staleness

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB060 | `confidence.level` in enum | ERROR | Machine-decidable trust |
| KB061 | `confidence.basis` present, ≥ 20 chars | ERROR | The empty basis is the standard cheat; without it "confidence: high" is noise |
| KB062 | `confidence: high` with `review.status: unreviewed` | WARNING | An unreviewed model asserting high confidence deserves a flag, not a block |
| KB063 | `shelf_life_days` positive int, **or** `shelf_life: none` with `shelf_life_reason` | ERROR | Thermodynamics does not expire; a fast-moving library does. The reason field forces the author to say which |
| KB064 | Document past shelf life | WARNING | **Deliberately not an error** — see severity policy. Surfaced as a site badge, a catalog `effective_status: expired`, and a weekly issue |
| KB065 | Document past shelf life **and touched by this PR** | ERROR | You had it open; refresh it |
| KB066 | `verified` + past shelf life | WARNING | Catalog downgrades effective trust so agents need no date arithmetic |

#### H. Links, anchors, and references

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB070 | Relative link target exists on disk | ERROR | Broken links are the classic silent rot |
| KB071 | **Link anchor exists among the target's generated heading slugs** | ERROR | Broken anchors rot invisibly; requires two-pass build (collect slugs, then resolve) |
| KB072 | Internal links point at `.md`, not `.html` | ERROR | Keeps source navigable in a plain editor and on GitHub — the "degrade gracefully" principle. The build rewrites extensions |
| KB073 | No repo-absolute links (`/docs/...`) | ERROR | Pages base-path breakage |
| KB074 | External URL is syntactically valid | ERROR | Free to check |
| KB075 | External URL liveness | WARNING, **scheduled job only** | Network checks are flaky and rate-limited; they must never gate a merge |
| KB076 | `sources` non-empty for `explainer` and `research` | ERROR | Brief: citations required where factual claims are made |
| KB077 | `sources` non-empty for `snippet`/`prompt`/`diagram` | WARNING | Often genuinely original |
| KB078 | `related`/`supersedes` IDs resolve to existing documents | ERROR | Dangling cross-references |
| KB079 | No `supersedes` cycle | ERROR | Infinite loop in any consumer |
| KB080 | `redirects.yml` targets exist, no redirect loops | ERROR | Renames must not break addressing |

#### I. Tags and vocabulary

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB090 | Every tag in `vocab/tags.yml` | ERROR | **The single biggest anti-sprawl lever** at 200 topics × 6 agents. Error message prints the exact line to add plus the five nearest existing tags by edit distance, so an agent self-serves in one step |
| KB091 | Tag is a known alias of a canonical tag (`k8s` → `kubernetes`) | ERROR (auto-fixable) | Aliases must resolve at write time, not read time |
| KB092 | Tag count between 2 and 8 | WARNING | One tag under-classifies; twenty is noise |
| KB093 | Tag string is lowercase kebab (and not a YAML boolean) | ERROR | Trap 3 |

#### J. Diagrams

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB100 | `diagram.format` declared (`mermaid`/`structurizr`) | ERROR | Determines rendering path |
| KB101 | `diagram.c4_level` declared for C4 diagrams | ERROR | C4 is explicitly first-class |
| KB102 | Diagram source block present and non-empty | ERROR | A diagram doc with no diagram |
| KB103 | **Source/render drift**: if a rendered `.svg`/`.png` is committed, `diagram.source_sha256` must match the current source | ERROR | Direct application of "markdown and HTML cannot drift" to diagrams. Conditional — skipped entirely when rendering is client-side |
| KB104 | First non-blank source line is a known Mermaid diagram type | ERROR | Cheapest possible catch of a mangled block |
| KB105 | Structural lint (balanced brackets, no tabs, no unclosed subgraph) | WARNING | Heuristic; genuine validation needs a browser (stated gap, §1) |

#### K. Code snippets

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB110 | `snippet` declares `language` **and** `valid_for` (runtime + version) | ERROR | Brief: "must record what language/version they were valid for" |
| KB111 | Fenced code blocks declare a language | WARNING | Needed for highlighting; some blocks are genuinely plain text |
| KB112 | Fence language agrees with frontmatter `language` | WARNING | Common copy-paste error |

#### L. Catalog and site invariants

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB120 | **Regenerating the catalog produces no git diff** | ERROR | The determinism gate (§3) |
| KB121 | Every document appears in the regenerated catalog | ERROR | Build invariant |
| KB122 | Document has no vocabulary tag and therefore appears on no tag page (true orphan) | WARNING | With a generated catalog, unreachability is the only meaningful orphan |
| KB123 | `.nojekyll` present in output | ERROR | Underscore-prefixed paths vanish without it |
| KB124 | Built HTML carries provenance meta tags, JSON-LD, and a visible footer | ERROR | Stated hard requirement; asserted by build tests, not per-document |

#### M. Checks not in the brief that I am adding

| Code | Check | Severity | Rationale |
|---|---|---|---|
| KB130 | **Secret scan** — API keys, tokens, private-key headers, `.env` fragments, high-entropy strings in code blocks | ERROR | **This is a public repo receiving raw AI output from six tools.** Someone will paste a key. Cheap regex + entropy; the highest expected-value check in the whole table |
| KB131 | Client/PII heuristic — internal hostnames, RFC1918 addresses, email addresses, names from `vocab/private-terms.yml` | WARNING | C4 diagrams "for a client system" are explicitly in scope, and this repo is public |
| KB132 | **Prompt-injection hygiene** — imperative second-person instructions to a reading agent ("ignore previous instructions", "run the following command", "you are now") | WARNING | A corpus whose stated purpose is to be fed to agents as context is a prompt-injection amplifier. This is our threat model, not a generic one |
| KB133 | `research` type must set `content_is_untrusted: true` | ERROR | Raw AI output must be structurally distinguishable from curated explainers, per the brief's fifth content type |
| KB134 | Build source contains no `datetime.now`/`time.time`/`random`/`uuid`/bare `hash(` | ERROR | Determinism guard (§3) |
| KB135 | Frontmatter `title` is not a template placeholder (`TODO`, `<title>`, `Untitled`) | ERROR | Templates get committed half-filled constantly |

**Total: ~70 checks, 48 ERROR / 22 WARNING.**

### 2.4 The severity ratchet (mitigating my own over-engineering)

Seventy checks on a greenfield repo is a real risk: the validator becomes more work than the
content. Mitigation, and I would write it into `AGENTS.md`:

**Ship in three waves.** Wave 1 (structure, schema, timestamps, identity, trust — codes
KB001–KB056) lands as ERROR immediately, because they define the system. Wave 2 (links, tags,
diagrams, snippets) lands as **WARNING** and is promoted to ERROR once it has been quiet for
100 documents. Wave 3 (KB130–KB135 heuristics) stays WARNING until it demonstrates a low
false-positive rate. Severity lives in one decorator argument, so promotion is a one-line
diff and the meta-test proves nothing else changed.

### 2.5 What a failing agent sees

This is a design requirement, not polish. Four output modes from one run:

1. **Human/terminal**, one finding per line, greppable:
   ```
   kb/explainer/kafka-partition-rebalancing--k7m2qd.md:12: ERROR KB052
     'verified' requires reviewer.kind: human; got 'agent'
     fix: set review.status: reviewed, OR have a human add reviewer.kind: human
     docs: AGENTS.md#KB052
   ```
2. **GitHub annotations** (`::error file=...,line=...,title=KB052::...`) so findings appear
   **inline on the PR diff** — the form an agent reading PR checks is most likely to parse.
3. **`$GITHUB_STEP_SUMMARY`** markdown table — what `gh run view` surfaces, which is how a
   contributing agent will actually look.
4. **`--format=json`** → `{file, line, code, severity, message, fix_hint}` for programmatic
   consumption.

Plus **`kb fix`**, which mechanically repairs the auto-fixable subset: timestamp
normalisation, tag alias canonicalisation, `updated_at` bumping, trailing newlines, catalog
regeneration, `content_sha256` recomputation with a review-status reset. For agent
contributors the fastest green path must be **one command**, and this is it.

---

## 3. Determinism

The requirement is that the catalog "can never silently drift." Six mechanisms, layered.

**3.1 The build is a pure function of tracked source.** Inputs: files under `kb/`, `vocab/`,
`templates/`, `schema/`. Nothing else. No clock, no network, no environment, no filesystem
ordering.

**3.2 Nondeterminism is banned by test (KB134).** A unit test greps the build package for
`datetime.now`, `time.time`, `random`, `uuid`, `os.urandom`, and bare `hash(` and fails on a
hit outside an allowlist. Crude, and it works — it catches reintroduction, which is the
actual failure mode over three years.

> Note on `hash()`: verified that Python's builtin string hash is **salted per process** and
> changes between runs. An agent that reaches for `hash()` to build a content suffix produces
> a different ID on every invocation. `hashlib.sha256` only, and the test enforces it.

**3.3 Sorted everything.** `sorted(glob(...))`, never bare `os.listdir`. Catalog sorted by
`id` — unique, so the ordering is total and tie-free. Tag lists, source lists, and every
`related` array sorted. **Any set is `sorted()` before it reaches output**, because set
iteration order depends on the salted string hash. `PYTHONHASHSEED=0` is set in the Makefile
as a second line of defence, but correctness does not depend on it.

**3.4 Canonical serialisation.** `json.dumps(obj, sort_keys=True, indent=2,
ensure_ascii=False)` plus exactly one trailing newline. UTF-8, LF. No locale-dependent
collation (plain `sorted()` on `str` is codepoint order, which is locale-independent —
`locale.strxfrm` is banned).

**3.5 No build timestamp inside any committed artifact.** The catalog carries
`schema_version`, never `generated_at`. Build/source SHA goes only into deployed HTML, never
into a committed file.

**3.6 Only three artifacts are committed** — `catalog.json`, `llms.txt`, `search-index.json`.
**HTML is never committed.** It is built in CI and uploaded as a Pages artifact. This is a
deliberate scope reduction: the drift surface shrinks from ~1,000 generated HTML files to
three JSON/text files. The hard requirement is that *raw markdown* stay fetchable, which it
is; HTML has no reason to live in git.

> **Not SQLite.** `sqlite3` is available as a stdlib module but there is no `sqlite3` CLI
> binary, and a committed `.db` file is an opaque binary blob that diffs as garbage, merges
> as a conflict nobody can resolve, and is unreadable in a plain clone — the exact opposite
> of "degrades gracefully." `catalog.json` is greppable, diffable, and `jq`-able. If query
> performance ever demands it, the SQLite file is *generated at build time and published to
> Pages*, never committed.

**3.7 The gate.**

```bash
python3 -m kb build
git diff --exit-code -- catalog.json llms.txt search-index.json
```

If a contributor changed a document without regenerating, CI fails and prints the exact diff.
This is the mechanism that makes silent drift impossible.

**3.8 The idempotence proof.** Build twice into two directories and compare bytes:

```bash
python3 -m kb build --out /tmp/a && python3 -m kb build --out /tmp/b && diff -r /tmp/a /tmp/b
```

**Verified working** on the 1,000-document synthetic corpus: byte-identical across runs. A
single build cannot detect nondeterminism; two can.

**3.9 The offline proof.** In tests, monkeypatch `socket.socket` to raise. Any build that
tries to touch the network fails the suite permanently.

---

## 4. CI workflow

### 4.1 Shape

Two workflows. **All logic lives in the Makefile; workflow steps are one-liners that call
`make`.** If the YAML contains logic, the local loop and CI drift apart — which is the same
rot the validator exists to prevent, applied to the validator itself.

```yaml
# .github/workflows/ci.yml
name: ci
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true      # superseded PR pushes: cancel freely

jobs:
  check:
    runs-on: ubuntu-24.04       # pinned: silent major bumps change behaviour
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # REQUIRED: KB019 needs real history.
                                # Shallow clone makes it silently measure nothing.
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
      - run: pip install --require-hashes -r requirements.txt
      - run: make test          # the tooling's own unit tests
      - run: make validate      # ~70 checks, GitHub annotations on
      - run: make build         # markdown -> HTML + catalog
      - run: make diff-check    # git diff --exit-code on committed artifacts
      - run: make determinism   # double build, byte-compare
      - if: always()
        run: make summary >> "$GITHUB_STEP_SUMMARY"
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: validation-report, path: build/report.json }
      - if: github.ref == 'refs/heads/main'
        uses: actions/upload-pages-artifact@v3
        with: { path: build/site }
```

```yaml
# .github/workflows/deploy.yml
name: deploy
on:
  workflow_run:
    workflows: [ci]
    types: [completed]
    branches: [main]

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false     # never cancel an in-flight deploy

jobs:
  deploy:
    if: github.event.workflow_run.conclusion == 'success'   # <-- the gate
    runs-on: ubuntu-24.04
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deploy
```

**Validation blocks deploy** two ways: the deploy workflow only triggers on a *successful*
`ci` run, and the Pages artifact is only uploaded when `ci` reaches that step. A red validator
means no artifact and no trigger. Branch protection additionally requires `check` to pass
before merge, so `main` cannot receive an invalid document in the first place.

Note the deliberate asymmetry in `cancel-in-progress`: **true for CI** (a superseded PR push
should abandon the old run) and **false for Pages** (cancelling mid-deploy can leave Pages in
an inconsistent state, and it is GitHub's documented recommendation).

### 4.2 Scheduled maintenance (never blocking)

```yaml
# .github/workflows/sweep.yml — weekly
#   make validate --warnings-only  ->  create/update ONE tracking issue listing
#   stale docs, unreviewed docs, near-duplicates (KB036/KB037), dead external links
```

**Critical constraint:** GitHub disables scheduled workflows on repositories with no activity
for 60 days. The sweep **will** stop after two quiet months. Therefore **nothing correctness-
critical may depend on the schedule.** Staleness is computed at *read* time — by the browser
from `updated_at` + `shelf_life`, and by agents from `catalog.json` — never stamped by cron.
The sweep is a convenience that notifies; it is not a mechanism that decides.

### 4.3 Runtime at 1,000 documents

Extrapolated from measured local numbers (Appendix A), with a 2x runner-slowness factor:

| Step | Local | CI estimate |
|---|---|---|
| checkout `fetch-depth: 0` (~8 MB, ~1,000 commits) | — | 5–8 s |
| setup-python + `pip install` (4 wheels, cached) | — | 8–12 s |
| `make test` (~120 unit tests) | ~2 s | 3–5 s |
| `make validate` + `make build` | **5.15 s** | 10–12 s |
| `make determinism` (second build) | 5.15 s | 10 s |
| upload Pages artifact (~6 MB HTML) | — | 5 s |
| **Total `check` job** | — | **~45–60 s** |
| deploy job | — | 20–30 s |

**Under two minutes end to end at the full scale target.** That number is what makes several
other decisions (full rebuild, no caching complexity, double-build determinism check)
obviously correct rather than merely defensible.

Caching honesty: `cache: pip` on four pure-Python wheels saves perhaps 2–4 s. It is one line,
so keep it, but it is not load-bearing and should not be defended if it ever misbehaves.

---

## 5. The two-agent collision problem

### 5.1 What happens with the naive scheme

Claude Code and Cursor both write "Kafka partition rebalancing" on 2026-08-14, both slug it
`kafka-partition-rebalancing`, both branch from `main`, both open a PR.

| Level | Outcome |
|---|---|
| Filename | Identical path, both new → git **add/add conflict** on the second merge |
| ID | Slug+date-derived IDs are **identical** → duplicate-ID error, but only *after* the merge already destroyed one document |
| Catalog | Both PRs regenerate `catalog.json` → a **second** conflict |
| Git | Two conflicts per collision, blocking the second PR behind the single operation AI contributors fail at most often — and the likely "resolution" is picking one file and silently losing the other's content |

Detecting this after the fact is too late. The scheme must make it **structurally
impossible**.

### 5.2 The scheme

```
Path:  kb/<type>/<slug>--<suffix>.md
ID:    <type>.<slug>.<suffix>

Example:  kb/explainer/kafka-partition-rebalancing--k7m2qd.md
          id: explainer.kafka-partition-rebalancing.k7m2qd
```

```python
suffix = base32_lower(
    sha256(b"\x00".join([tool, model, session_ref, created_at_minute, slug]))
)[:6]
```

Properties, each doing real work:

1. **Deterministic and therefore verifiable.** The validator (KB032) *recomputes* the suffix
   from frontmatter and rejects a mismatch. This is the key difference from a random UUID: an
   agent cannot invent, copy-paste, or fudge an ID. It is a checksum over its own provenance.
2. **Collision-free in practice.** Two agents differ in at least `tool` (and usually `model`
   and `session_ref`) → different suffixes → **different filenames → git never conflicts on
   content.** Both documents land. Nothing is lost.
3. **Sized deliberately.** 6 base32 chars = 30 bits ≈ 1.07e9. Birthday probability at n=1,000
   is n²/2N ≈ **0.047 %** (~1 corpus in 2,100). At n=10,000 it rises to ~4.7 %.
   **Numeric trigger: widen to 8 characters (40 bits, ~0.005 % at 10,000) when the corpus
   passes 5,000 documents.** And even then KB031 makes a real collision a loud ERROR, never
   silent — the fix is to bump `created_at` by one minute and re-run `kb fix`.
4. **Still greppable.** `rg kafka-partition-rebalancing` matches; the suffix does not
   interfere with human or agent search.
5. **Mechanically separable.** `--` cannot appear inside a slug (KB034 enforces it), so
   splitting on the last `--` is unambiguous.

### 5.3 What the validator does about *semantic* duplicates

Unique filenames solve git. They do not solve "we now have two Kafka explainers."

- **KB036 (same slug, different suffix) is a WARNING, not an ERROR.** This is a deliberate
  and arguable call. Two agents' takes on the same subject are frequently *both* worth
  keeping — one is often better, and which one is a human judgement. For a repository whose
  entire purpose is to stop valuable output evaporating, **auto-rejecting the second document
  is the worse failure.**
- **KB037** escalates when slug + tags match and body lengths are within 20 %: probable true
  duplicate, added to the weekly sweep issue.
- Resolution is `supersedes:` frontmatter — the loser gets `review.status: superseded` plus a
  `redirects.yml` entry, so old links keep working (KB080).
- **Honest residual cost:** near-duplicates accumulate until a human triages. At 200 topics ×
  6 tools that backlog is real. I accept it because a lost document is worse than a duplicate
  one, and the weekly issue keeps the debt visible rather than invisible.

### 5.4 The residual conflict: `catalog.json`

Unique filenames do not prevent two PRs both appending a catalog entry. Options:

- **(a) Commit the catalog, accept conflicts.** Resolution is mechanical and documented:
  `git checkout --ours catalog.json && make build`. The determinism gate proves the result is
  correct regardless of which side you took. Mark it `linguist-generated=true` in
  `.gitattributes` so it collapses in PR diffs.
- **(b) Publish the catalog to Pages only, never commit it.** Zero conflicts. Costs
  raw-fetchability of the index and makes a plain `git clone` index-less.
- **(c) Per-document metadata shards merged at build time.** Zero conflicts, doubles the file
  count.

**I prefer (a).** "Works in a plain clone / degrades gracefully" is a stated working
principle, and at six contributors the conflict rate is low with a one-command fix. **Numeric
trigger for moving to (c): more than ~1 catalog conflict per week.**

---

## 6. Incremental vs full rebuild

**Full rebuild. Never write the incremental path.** This is not a judgement call; it is a
measured one.

**Measured full build, 1,000 documents (~968 words each, 6.2 MB corpus), single-threaded:**

```
FULL BUILD 1000 docs: 5.15s total
  read 0.08 | fm-parse 0.45 | schema 0.15 | md parse+render+link-extract 4.21
  write 0.22 | catalog 0.02
```

Markdown parsing is 82 % of the cost; everything else is rounding error. Note the fm-parse
number depends on using **`yaml.CSafeLoader`** — the libyaml C loader is available here and
is **7x faster** than pure-Python `safe_load` (0.40 s vs 2.84 s per 1,000 documents). Use it,
with a pure-Python fallback.

**When incremental becomes necessary.** The real threshold is behavioural: a build slower
than ~30 s is one a human or agent stops running before pushing. Extrapolating linearly from
5.15 s/1,000:

- **~6,000 documents** → 30 s local build → *now* consider it.
- ~15,000 documents → 3 min CI → hard requirement.

So incremental pays off at **6x the stated scale target**. YAGNI, decisively.

**Two cheaper levers to reach for first, in order:**

1. **Parallelise rendering.** The 4.21 s render stage is embarrassingly parallel;
   `ProcessPoolExecutor` plus re-sorting results gets it to roughly 1 s on four cores for
   about five lines of code, and stays deterministic because output is re-sorted.
2. **Content-addressed render cache** — `sha256(source + template_version + tool_version)` →
   rendered HTML, in a gitignored `.cache/` restored via `actions/cache`.

**The trap to record now, before anyone tries it:** link integrity, anchor resolution, orphan
detection, and duplicate-ID checks are **inherently global** — a document you did not touch
can be broken by one you deleted. **Validation must always be full, even if rendering becomes
incremental.** Fortunately validation is only ~0.6 s of the 5.15 s, so this costs nothing.
Incremental may only ever apply to the render-and-write stage.

---

## 7. TDD structure

### 7.1 Framework: stdlib `unittest`, with pytest optional

`pytest` is **not installed**, and this system is PEP 668 externally-managed
(`/usr/lib/python3.12/EXTERNALLY-MANAGED`), so `pip install pytest` requires either a venv or
`--break-system-packages`. Meanwhile `python3 -m unittest discover -s tests` works **right
now, on this machine, with zero setup** — which is exactly the property that matters when
your contributors are AI agents that must run the suite without a working install step.

**Baseline is `unittest`.** `make test-dev` optionally creates `.venv` and installs pytest for
humans who want better assertion introspection; pytest runs unittest-style tests unchanged,
so nothing is lost by writing them in the stdlib style.

**Honest downside:** pytest's assertion rewriting and `@parametrize` are a genuine
productivity gain during TDD, and I am giving them up as the default. `subTest` covers
parametrisation adequately, and the fixture-corpus tests want a "walk the tree, `subTest` each
file" shape that needs no parametrisation at all — but I would be overselling if I claimed the
ergonomics are equal.

### 7.2 Fixture strategy — three tiers

1. **`tests/fixtures/good/`** — 8–12 documents covering all five content types, all valid.
   Positive assertions plus the golden build input.
2. **`tests/fixtures/bad/`** — **one file per error code, named for the code it triggers**:
   `KB014-naive-timestamp.md`, `KB052-self-verified.md`, `KB071-broken-anchor.md`,
   `KB130-leaked-api-key.md`.
3. **`tests/golden/`** — expected `catalog.json` (byte-level) and 2–3 expected HTML pages.
   Regenerated with `make golden-update`, reviewed as a diff in the PR.

**The meta-test that keeps the suite honest** — my favourite structural idea here:

```python
def test_every_code_has_exactly_one_fixture(self):
    # every registered check has a bad fixture, and that fixture
    # triggers exactly its own code and no others
    for code in REGISTRY.codes():
        with self.subTest(code=code):
            fixtures = glob(f"tests/fixtures/bad/{code}-*.md")
            self.assertEqual(len(fixtures), 1)
            found = {f.code for f in validate_file(fixtures[0])}
            self.assertEqual(found, {code})   # no under-firing, no over-firing
```

This makes it **impossible to add a check without a test** and **impossible for a check to
over-fire** without the suite noticing. It is three lines and it does more for long-term
health than any other single test.

### 7.3 How to test a build

- **Do not snapshot HTML broadly.** Golden 2–3 pages only, to catch gross regressions. For
  everything else, make **structural assertions on parsed output**: parse built HTML with
  stdlib `html.parser` and assert "there is a `<meta name='kb:model'>` whose content equals
  the frontmatter model", "the JSON-LD block parses as JSON and its `dateModified` equals
  `updated_at`", "the visible footer contains the review status". These survive restyling;
  broad goldens turn the whole suite red on a CSS tweak and get regenerated without being read
  — which is worse than no test.
- **Catalog: parsed-dict assertions**, *plus* exactly one byte-level golden that specifically
  asserts formatting (sort_keys, 2-space indent, trailing newline), because formatting is
  load-bearing for the `git diff --exit-code` gate.
- **Determinism as a property**, not an example: build twice, assert byte-identical.
- **Git checks against a temp repo** built in the fixture (`git init` in a tmpdir, commits
  made with pinned `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`), which is the only way to make
  KB019 both testable and reproducible.

### 7.4 Layout

```
tools/kb/
  __init__.py
  frontmatter.py     # split, safe-load (dup-key + no-timestamp-coercion), line numbers
  ids.py             # slug rules, suffix hash, id parse/format
  schema.py          # jsonschema loading and dispatch by type
  registry.py        # @check decorator, codes, severities, scopes
  checks/            # one module per family; ~70 small pure functions
  render.py          # markdown-it-py -> HTML, heading slugs, link extraction
  catalog.py         # catalog.json, llms.txt, search-index.json
  gitmeta.py         # ONE git log pass -> {path: last_change_iso}
  cli.py             # validate | build | fix | new | doctor | summary
schema/*.json
vocab/{tags,tools,models,reviewers,private-terms}.yml
tests/
  fixtures/{good,bad}/
  golden/
  test_frontmatter.py  test_ids.py  test_checks_*.py
  test_build_determinism.py  test_code_coverage.py
Makefile
requirements.txt         # hash-pinned, 4 packages
```

### 7.5 The first five tests, in order

Each forces a design decision that is painful to retrofit, and each builds on the last.

---

**Test 1 — `test_frontmatter.py::test_splits_and_rejects_malformed`**

Given a `---`-fenced YAML block at byte 0, `split(text)` returns
`(raw_fm_text, parsed_mapping, body, body_start_line)`. Rejects: no fence, unterminated
fence, fence not at byte 0, duplicate keys (KB002). Asserts `created_at` comes back as a
**string, not a `datetime`** (Trap 1), and that `tags: [no, on]` comes back as
`["no", "on"]`, **not `[False, True]`** (Trap 3).

*Why first:* everything downstream depends on this one function, and it needs no schema, no
rendering, and no git. More importantly it forces two decisions that are agony to retrofit —
**keep raw strings alongside parsed values** (because the timestamp format check cannot run on
the parsed value) and **carry line numbers** (because every error message needs one).

---

**Test 2 — `test_ids.py::test_id_is_deterministic_and_collision_resistant`**

`compute_id(type, slug, tool, model, session_ref, created_at)` is stable across calls and
across processes (run it in a subprocess with `PYTHONHASHSEED=random` to prove it is not
using builtin `hash()`); changing *any* input changes the suffix; **two different tools with
the same slug on the same day produce different IDs**; the ID round-trips to and from the
filename; invalid slugs (uppercase, spaces, `--`, > 60 chars) raise.

*Why second:* identity underpins the catalog, the collision scheme, and the entire path
layout. Getting it wrong later means renaming every file in the repo. It is a pure function,
so it is the cheapest possible place to lock the most expensive decision.

---

**Test 3 — `test_checks_trust.py::test_verified_requires_human_reviewer`**

`review.status: verified` with `reviewer.kind: agent` → ERROR KB052. With no reviewer →
ERROR KB051. With `reviewer.kind: human` + `reviewed_at` → clean. Reviewer equal to
`provenance.tool` → ERROR KB054. And body edited after review (`content_sha256` mismatch)
while still `verified` → ERROR KB056.

*Why third:* this is the single check the entire premise of the repository rests on — "can I
trust this as context?" Writing it before any content exists forces the `review` sub-object
into existence and makes the trust model concrete rather than aspirational. KB056 in
particular is the check that stops `verified` decaying into a lie.

---

**Test 4 — `test_checks_timestamps.py::test_updated_at_reconciles_with_git`**

In a temp git repo with pinned `GIT_AUTHOR_DATE`s: a file whose content changed in a commit
dated after its `updated_at` → ERROR KB019. A file with `updated_at == created_at` and a
single commit → clean. Naive timestamp → ERROR KB015. Future timestamp → ERROR KB017. **And
the implementation must invoke `git` exactly once** — asserted with a call counter on the
subprocess seam, encoding the measured 270x perf lesson as a test rather than a comment.

*Why fourth:* the highest-value anti-rot check and the hardest to test, so TDD earns the most
here. It also forces `gitmeta.py` to exist as an **injectable seam**, which is what lets the
other ~115 tests run with no git at all.

---

**Test 5 — `test_build_determinism.py::test_build_is_byte_identical_and_offline`**

Build the `good/` fixture corpus twice into two temp directories; assert the trees are
byte-identical. Assert `catalog.json` matches the committed golden byte for byte. Assert no
build output contains today's date. Assert the build makes **no network calls** by
monkeypatching `socket.socket` to raise.

*Why fifth:* it is the executable form of "regenerated deterministically so it can never
silently drift," and it must be locked in before there is enough code to make it hard. The
socket assertion is a permanent, one-line guarantee that the build stays offline forever.

---

## 8. Local dev loop

**One command: `make check`. It runs exactly what CI runs, because CI calls the same targets.**

| Target | Does |
|---|---|
| `make check` | `test` + `validate` + `build` + `diff-check` + `determinism` — the full CI gate, ~12 s at 1,000 docs |
| `make test` | `python3 -m unittest discover -s tests` |
| `make validate` | ~70 checks; `--format=github` under CI |
| `make build` | markdown → HTML + catalog + llms.txt + search index |
| `make fix` | auto-fix the mechanical subset |
| `make new TYPE=explainer TITLE="..."` | scaffold from template, frontmatter prefilled, **ID computed** — the target that actually makes agents comply |
| `make serve` | `python3 -m http.server` over `build/site` (stdlib, no deps, works on a phone over LAN) |
| `make doctor` | verify local toolchain, print exactly what to install |
| `make golden-update` | regenerate goldens |
| `make stale` | list documents past shelf life |

**Git hooks: yes, but fast and opt-in.** `make hooks` sets `core.hooksPath .githooks`.

- **pre-commit** runs validation on **staged files only** plus catalog regen. Target < 2 s.
  A pre-commit hook slower than that gets `--no-verify`'d into irrelevance within a week.
- **pre-push** runs the full `make check` (~12 s), since pushes are rarer.

Hooks are **not enforcement** — they are bypassable and are not cloned by default. CI is the
enforcement. Hooks exist purely to shorten the feedback loop.

**For agents, `AGENTS.md` says exactly this and nothing more elaborate:**

> Before you finish: run `make check`.
> If it fails, run `make fix`, then run `make check` again.
> If it still fails, read the error codes — each one names its own fix.

Three lines. Anything longer will not be followed.

---

## 9. Six months of neglect

Ranked by likelihood, with the mitigation baked into the design.

**1. GitHub Actions deprecations — the actual killer.** Node runtime deprecations for actions,
`set-output` removal, `upload-artifact@v3` brownouts (this really happened). Mitigation: use
the **minimum number of actions, all first-party** — `checkout`, `setup-python`,
`upload-pages-artifact`, `deploy-pages`, `upload-artifact`. Five, no third parties.

**Pinning: major tags (`@v4`), not SHAs — a deliberate, arguable choice.** SHA-pinning
maximises supply-chain safety but *guarantees* rot with no human present to bump it, and
Dependabot PRs pile up unmerged until the workflow breaks anyway. For a public repo with no
secrets and no deploy credentials beyond the Pages OIDC token, absorbing patch fixes
automatically is worth more than pinning against a compromise of a first-party action. I would
rather state that trade-off than pretend SHA-pinning is free.

**2. Runner image drift.** Pin `runs-on: ubuntu-24.04`, not `ubuntu-latest`. When it is
retired the failure is loud and one line to fix, versus `ubuntu-latest` silently changing
behaviour underneath a passing build. A weekly no-op scheduled run surfaces breakage *before*
someone tries to contribute — subject to the 60-day caveat below.

**3. Runtime EOL.** `setup-python` pinned to `3.12` (exact minor). Python 3.12 is supported to
**October 2028**, comfortably past the horizon. **Node 22 reaches EOL in April 2027, inside
it** — a concrete, dated argument for the language decision in §1.

**4. Dependency rot: near zero.** Four hash-pinned packages, three pure-Python, one (PyYAML)
with manylinux wheels. **No npm means no `npm audit` noise, no lockfile drift, no transitive
deprecations, no supply-chain surface beyond four well-known packages.** This is the single
largest rot reduction the language decision buys, and it is why I weighted it so heavily.

**5. Vendored `mermaid.min.js`.** A pinned copy keeps working indefinitely — it is static JS.
It simply will not gain new diagram types. Record version, source URL, and sha256 in
`vendor/README.md` so a future maintainer can verify and upgrade deliberately.

**6. Scheduled workflows get disabled after 60 days of inactivity.** The weekly sweep **will**
stop. Design consequence, already applied: **nothing correctness-critical depends on the
schedule.** Staleness is computed at read time by the browser and by agents from
`catalog.json`. The sweep only notifies.

**7. Content rot — the intended kind.** This is where the design actually wins. After six
months of neglect, the shelf-life mechanism means the site displays "stale" badges and the
catalog marks documents `effective_status: expired`, so **the system tells the truth about
its own neglect** rather than quietly serving six-month-old content as `verified`. That is the
most important graceful-degradation property in the whole proposal: an abandoned knowledge
base that visibly says "nobody has checked this since February" is far more useful than one
that looks maintained.

**Total rot surface: one runtime, four dependencies, five first-party actions, one pinned
runner image, zero cron dependencies for correctness.**

---

## 10. Three tooling strategies

Genuinely different approaches, not variations, for the panel to combine into candidate
architectures.

### Strategy A — "Minimal Monolith"

A single `tools/kb.py` (~600–900 lines), stdlib + the four preinstalled packages, subcommands
`validate | build | fix | new | doctor`. Committed artifacts: catalog + llms.txt + search
index. `unittest` + a fixture tree.

- **Wins:** lowest possible ceremony. **An agent can read the entire tool in one context
  window** — a genuinely underrated property when your contributors are LLMs. Trivially
  auditable. Nothing to install, nothing to wire.
- **Loses:** one file past ~1,000 lines becomes unwieldy; **harder to unit-test in small
  units, which directly conflicts with the stated TDD requirement**; no seam for adding a
  sixth content type; error codes and severities scattered through the file, so the
  documented table drifts from behaviour.
- **Best when:** the check count stays under ~20 and the corpus stays under ~200 documents.

### Strategy B — "Registry Package" ⭐ **my preference**

`tools/kb/` as a package. Every check is a small pure function registered with
`@check(code, severity, scope)`. Build runs three phases — **collect → validate → emit** —
where phase 1 parses each document exactly once into a `Document` dataclass (raw frontmatter,
parsed mapping, body, token stream, heading slugs, content hash) that phases 2 and 3 both
consume. That single-parse design is what the 5.15 s benchmark actually measures.

- **Wins:** best testability by a wide margin — every check is a five-line pure function,
  which is exactly what "testable in small units" asks for. The error-code table in
  `AGENTS.md` is **generated from the registry** and therefore cannot drift. The
  "every code has exactly one fixture" meta-test becomes three lines. Severities are
  declarative, so the ratchet in §2.4 is a one-line diff. Scales to ~70 checks without
  becoming spaghetti.
- **Loses:** roughly 2x the initial code of A; more files and one layer of indirection; a
  registry is an abstraction an unmotivated future maintainer may simply bypass by adding
  checks inline — at which point the generated table silently becomes a lie. The meta-test
  mitigates but does not eliminate this.

### Strategy C — "Two-Runtime Split: Python validates, Node renders"

Python owns frontmatter, schema, catalog, and git; Node owns markdown → HTML plus
`mermaid-cli` SVG pre-rendering, communicating via a JSON manifest on disk.

- **Wins:** a genuinely superior diagram story — **real pre-rendered SVG**, so diagrams work
  with JavaScript disabled, appear in link previews and search-engine results, and survive in
  the raw path. Access to Pagefind/lunr for a better static search index. Richer markdown-it
  plugin ecosystem (footnotes, containers, anchors) than the Python port.
- **Loses:** two runtimes, two lockfiles, two setup steps, two caches, ~60+ npm transitive
  packages, `npm audit` noise, Node 22 EOL **inside** the three-year window, and — decisively
  — **`mermaid-cli` drags in Puppeteer and headless Chromium**, roughly 150 MB and the least
  reliable component in any CI pipeline. Worst of all, an agent contributor now has *two*
  ways to fail to run the tooling.
- **Adopt only if** pre-rendered SVG becomes a hard requirement. **Numeric trigger:** diagrams
  failing to render on the target phone, or a stated need for no-JS / SEO-visible diagrams.

### Recommendation

**Strategy B**, with **A** as the fallback if the check count is deliberately capped below
~20, and **C** explicitly deferred behind the trigger above.

### Downsides of my own preference, stated plainly

1. **The registry has no external forcing function.** If checks get added inline later, the
   generated error-code table becomes a lie. The meta-test catches missing *fixtures*, not
   unregistered *checks*.
2. **Python-only means no true Mermaid validation.** I can lint structurally; I cannot prove a
   diagram renders without a browser. **A broken diagram will reach production.** I accept
   this rather than pull Chromium into the build, and I note that GitHub's own renderer shows
   Mermaid errors when browsing source, which is a free partial safety net.
3. **The tag-vocabulary ERROR (KB090) is the check most likely to be resented and worked
   around.** An agent facing a rejected tag will often pick a wrong-but-existing tag rather
   than propose a new one, silently degrading classification quality — a failure mode that is
   *invisible* to the validator. That is a real weakness of my own recommendation. Partial
   mitigation is the error message printing the exact vocab line to add plus the five nearest
   existing tags, making "add the right tag" cheaper than "settle for a wrong one."
4. **~70 checks is a lot of surface for a greenfield repo**, and there is a genuine risk the
   validator becomes more work than the content it guards. The severity ratchet (§2.4) is the
   mitigation, but it is a discipline, not a mechanism.
5. **`unittest` over pytest** costs real ergonomics during TDD, which is precisely the phase
   the user is about to enter.

---

## Appendix A — Measurements

All run on this machine (Python 3.12.3, Linux, this repo's host) on 2026-08-14.

**Environment verification**

```
Python 3.12.3 | Node v22.23.2 | npm 10.9.8
PyYAML 6.0.1 | jsonschema 4.10.3 | markdown-it-py 3.0.0 | mdurl 0.1.2   <- all preinstalled
markdown / mistune / commonmark / docutils : MISSING
pytest: MISSING;  /usr/lib/python3.12/EXTERNALLY-MANAGED present (PEP 668)
libyaml CSafeLoader: AVAILABLE
markdown-it-py preset 'gfm-like' -> ModuleNotFoundError: Linkify enabled but not installed
markdown-it-py preset 'default'  -> tables OK, strikethrough OK
```

**Full build, 1,000 synthetic documents (~968 words each, 6.19 MB)**

```
FULL BUILD 1000 docs: 5.15s total
  read 0.08 | fm-parse 0.45 | schema 0.15 | md parse+render+link-extract 4.21
  write 0.22 | catalog 0.02
  links found: 8000  broken: 0  dup ids: 0
  catalog.json size: 312 KB
```

**YAML loader**

```
pyyaml safe_load  x1000: 2.84s
pyyaml CSafeLoader x1000: 0.40s        <- 7x, use it
```

**git mtime lookup, 300 files / 31 commits**

```
per-file `git log -1 -- <path>` x300 : 3.542s
single-pass `git log --name-only`    : 0.013s     <- ~270x
```

**Determinism**

```
diff -r bench/out bench/out2  ->  DETERMINISM: byte-identical across runs
```

**YAML traps (all reproduced, all with working fixes)**

```
Trap 1: created_at: 2026-08-14T06:13:00-07:00  -> datetime (not str); safe_dump drops the 'T'
Trap 2: duplicate 'review:' key -> {'review': {'status': 'verified'}}  (first silently lost)
Trap 3: tags: [no, on, off, yes] -> [False, True, False, True]
        id: 0755 -> 493 (octal);  ver: 1.20 -> 1.2
Fixes:  dup-key-detecting SafeLoader subclass      -> "duplicate key 'review' at line 3"
        loader with timestamp+bool resolvers removed -> values stay strings
```

**Birthday collision probability for a 30-bit (6 base32 char) suffix**

```
n=1,000   -> n^2/2N = 1e6 / 2.148e9  = 0.047%
n=10,000  -> 1e8 / 2.148e9           = 4.7%     -> widen to 8 chars past ~5,000 docs
```
