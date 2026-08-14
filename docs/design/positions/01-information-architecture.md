# Position 01 — Information Architecture / Taxonomy

**Role:** Information architect / taxonomist
**Charge:** How does an unpredictable, unbounded topic space get shelved so it is still
navigable at 1,000 documents across 200 topics, written by six AI tools that never talk
to each other?
**Status:** position paper for the design panel. Opinionated by request.

---

## 0. The one principle everything else follows from

> **The mandatory directory axis must be the *least ambiguous* axis, not the most
> interesting one. Every axis that requires judgement becomes a facet in frontmatter.**

The reason is not aesthetic. It is that we have six uncoordinated writers with no shared
memory. Any classification decision that two reasonable agents would answer differently
*will* be answered differently, roughly 50/50, forever. Put such an axis in the directory
tree and you get a corpus that is split down the middle by coin flips and can only be
repaired by moving files — which breaks links, which is the expensive failure.

So the test for "may this be a folder?" is: **can an agent that has read only a one-page
contract get it right ~100% of the time, without knowing what else is in the repo?**

- "Is this a diagram or an explainer?" → yes, ~100%. Folder-worthy.
- "Is this raw AI output or a curated doc?" → yes, ~100% (the agent knows whether a human
  reviewed it). Folder-worthy.
- "Is this an explanation or a reference?" (Diátaxis) → no. Facet at best.
- "Is this `distributed-systems` or `streaming` or `kafka`?" → no. Facet.
- "Is this a Project or an Area?" (PARA) → no, and it depends on the reader. Facet at best.

A corollary that matters just as much:

> **Depth expresses composition, not classification.**

A new directory level is legal only when it holds *multiple files belonging to one
artifact* (a diagram's source + render + legend). It is never legal to add a level because
there are *more artifacts of one kind*. That single rule is what stops the tree reaching
six levels, and it is mechanically checkable in CI.

---

## 1. Honest assessment of the named schemes

### 1.1 Diátaxis — reject as a shelf, allow as an optional hint

Diátaxis (Procida) partitions documentation on two axes: theory vs. practice, and study
vs. work, producing tutorial / how-to / reference / explanation. It is genuinely good, and
it is good *at the thing it was designed for*: documenting **one product** whose users
arrive with one of four needs.

Two things break it here.

**The degenerate case is real and is our normal case.** The brief says the corpus is
mostly explanatory. At 1,000 docs a Diátaxis tree plausibly looks like
`explanation/ ≈ 800`, `reference/ ≈ 90`, `how-to/ ≈ 60`, `tutorial/ ≈ 50`. A top-level
split that puts 80% of the corpus in one bucket has done no navigational work at all; it
has just added a level of indirection in front of a pile. Worse, the three small buckets
are the ones with the highest classification variance, so the split you *do* get is the
noisy one.

**Diátaxis is a compass for authors, not a filing system for arbitrary corpora.** Its own
guidance is that it tells you what kind of document you should be *writing*; it does not
claim to be a shelving scheme for a heterogeneous library. Applied as a filing system by
six agents, the predictable outcome is a permanent, unresolvable argument about whether a
runnable Kafka consumer example is a tutorial (it teaches), a how-to (it solves a task),
or reference (it's a config sample). Each of the six tools will answer differently, and
because the answer lives in the path, every answer is a different URL.

Note that our five content types already capture the *useful* part of Diátaxis, but along
a **format/artifact** axis rather than a **reader-intent** axis — and the format axis is
the machine-decidable one. "Is this a code snippet?" is a fact about the file. "Is this a
how-to?" is a claim about a reader.

**Verdict:** no Diátaxis directories. If anyone wants it, it is an optional
`doc_kind: explanation|reference|how-to|tutorial` frontmatter field with a default of
`explanation`, used only to sort within a generated index. I would ship without it (YAGNI)
and add it only if someone actually complains they can't find the how-tos.

### 1.2 PARA — reject as a shelf; its one real signal is handled elsewhere

PARA (Forte) sorts by **actionability to a specific person**: Projects (deadline-bound),
Areas (ongoing responsibility), Resources (topical interest), Archive (dead).

Three failures, in increasing severity:

1. **There are no projects.** This is a reference library. Everything lands in Resources.
   Same degenerate 90%-in-one-bucket problem as Diátaxis, with less justification.
2. **PARA is subjective and personal.** The same document is an Area for one reader and a
   Resource for another. An agent filing a doc has *no basis whatsoever* to decide. This
   is the least machine-decidable scheme of the six.
3. **PARA requires continuous re-filing.** Its value comes from moving items
   Project → Archive as life changes. That is a weekly human ritual. Six AI tools will
   never perform it. Within six months of neglect PARA is strictly worse than no scheme,
   because the folder names now assert a lifecycle state that is false.

PARA does contain one true observation for us: **client/engagement material genuinely is
different in kind** from "Kafka partition rebalancing." It is bounded, dated, cohesive,
and it goes stale as a set. But that difference is better expressed as (a) provenance and
staleness frontmatter, which we already require, and (b) a `client-work` tag — not as a
lifecycle folder that must be maintained.

There is one *non-IA* reason to consider a separate physical shelf for client material,
and the panel should decide it explicitly: **this is a public repo.** A client C4 container
diagram with real system, service, and vendor names is a disclosure risk, and a
path-visible boundary (`kb/clients/…`, or better, an entirely separate private repo) is a
far more reliable guard than a frontmatter field a build script must remember to honour.
My recommendation: **sanitize client material before it enters this repo** (generic names,
no hostnames, no vendor contracts), and treat "must stay private" as a signal that the
document belongs in a different repo entirely. The worked example below uses a sanitized
client.

### 1.3 Johnny Decimal — reject the addressing scheme, steal the underlying idea

Johnny Decimal is 10 areas × 10 categories × up to 100 ids, giving addresses like `34.11`.
Its real contribution is *short, stable, memorable identifiers* and a hard cap that forces
you to keep the system small.

Why it fails at our scale and shape:

- **The cap is the point, and we exceed it on day one.** 200 unrelated topics do not fit
  into 100 conceptually coherent categories. JD's own answer to "I need more" is "then you
  need a second JD system" — which means a second, disconnected namespace, which is worse
  than no numbering.
- **Exhaustion is unrecoverable.** Fill area `30` and the next thing that belongs there has
  nowhere to go. The only repair is renumbering, which changes every path, which breaks
  every link — the exact failure mode we are trying to design out.
- **It needs a central allocator.** Someone must know the whole map to assign the next
  number. Six tools that never talk cannot do this. They will either collide (two agents
  both take `34.11` on the same day) or, far more likely, ignore the numbers entirely and
  invent their own — leaving a numbering system that is 60% honoured, which is the worst
  possible state for a system whose entire value is being exhaustive.
- **Opaque numbers are hostile to both our audiences.** `34.11-kafka.md` means nothing to a
  human skimming a directory and nothing to ripgrep. JD is optimized for a *single person's
  memory* of a *personal* filing cabinet. We are optimizing for strangers and machines.

**Steal this:** the idea of an identifier that is *decoupled from location*, so re-shelving
does not break references. We get that in §5 with an immutable `id` — but ours is a
readable slug rather than a number, because grep-ability and human legibility are worth
more to us than brevity.

### 1.4 Zettelkasten / atomic linked notes — reject decisively

Zettelkasten's value is **link density**. Emergent structure appears because one mind, over
years, remembers the corpus and connects each new note to the existing ones.

That mechanism cannot exist here. Six tools with no shared memory produce notes with **zero
inbound links**. What emerges is not a network; it is 1,000 orphans and a set of hub notes
nobody wrote. Every honest Zettelkasten practitioner will tell you a Zettelkasten with
sparse links is just a worse folder system, and sparse links are the *guaranteed* outcome
of uncoordinated contribution.

Two further mismatches:

- **Atomicity fights our retrieval model.** Both audiences want one self-contained artifact
  that answers the question in one fetch. An agent doing RAG or a raw-markdown pull wants
  "the Kafka rebalancing doc," not twelve 200-word notes requiring a graph traversal to
  reassemble. Atomicity also multiplies the corpus: 1,000 docs becomes ~8,000 notes, making
  every other problem worse.
- **Hand-maintained links rot silently.** A link that should exist but doesn't produces no
  error, no warning, no visible gap.

**Steal this:** hub / structure notes — but **generate them from frontmatter instead of
writing them by hand.** This is the single most important transfer in this document:
*anything Zettelkasten achieves through hand-maintained links, we achieve through generated
indexes, because generation survives neglect and hand-linking does not.* Likewise
backlinks: a doc declares `related: [id, …]` one-directionally, and the build renders the
reverse edge on the target page. Nobody has to remember to link back.

### 1.5 Pure faceted classification (flat namespace + orthogonal tags) — nearly right, insufficient alone

The Ranganathan-style ideal: one flat pool, no hierarchy, all navigation from orthogonal
facets. Its strengths are exactly the ones we need — **a document is never in the wrong
place, because there are no places**; re-classification costs one line of YAML instead of a
file move; and there is nothing to argue about at filing time.

What breaks:

1. **It fails the graceful-degradation requirement hardest.** Strip the build script from a
   flat pool and you have a pile. Strip it from a shallow tree and you still have a
   browsable library. The brief explicitly requires the markdown to be navigable in a plain
   text editor and on github.com. A flat pool only satisfies that via generated artifacts.
2. **github.com browsing degrades badly.** A directory with 1,000 entries paginates and
   truncates in the web UI, and `ls` / editor file trees become useless. Human browsing of
   the *source* — which is how you'd triage during a rescue — is gone.
3. **Filename collisions become frequent.** Six writers, one namespace: `kafka-consumers.md`
   gets claimed twice. (In git this at least surfaces as a loud add/add conflict, which is
   the good failure — see §5.)
4. **Vocabulary carries 100% of the navigation load, with no backstop.** `k8s` vs
   `kubernetes`, `postgres` vs `postgresql`, `llm` vs `llms` silently fragment the corpus.
   In a hybrid you notice because the shelf shows you the neighbourhood; in a flat pool
   there is no neighbourhood to notice from.

### 1.6 Hybrid — shallow shelf + facets. This is the answer.

Shallow hierarchy on the one unambiguous axis gives us: something that works with no
tooling, a bounded namespace per shelf, and a place for humans to look. Facets in
frontmatter give us: unbounded topics, zero-cost reclassification, multi-membership without
duplication, and machine-filterable queries. Generated indexes give us the Zettelkasten
navigation without the Zettelkasten discipline.

Everything below is a hybrid. The three options differ in **what the shelf axis is.**

---

## 2. The five mandatory answers

### Q1. What happens when a document belongs in three places?

**Mechanism: one canonical file on disk + facets in frontmatter + generated cross-reference
indexes + recorded aliases for former paths.** Slogan: **one file, many index entries.**

Explicitly rejected alternatives, with reasons:

- **Duplicate files** — no. Two copies drift, and each copy carries its own provenance
  block, so the trust story (the whole point of the repo) forks. Also doubles the surface
  for the validator and the reviewer.
- **Symlinks** — no. They survive git but not Windows checkouts without special config,
  and critically **`raw.githubusercontent.com` serves the symlink's *target path string*,
  not the target's content**. An agent fetching the raw URL would receive the literal text
  `../../explainers/kafka-partition-rebalancing.md` instead of a document. That silently
  breaks the primary agent-retrieval path. Disqualifying.
- **Tag-only, no canonical home** — no; that's §1.5 and it fails degradation.

So: the document lives at exactly one path. Its multi-membership is expressed as
`topics: [kafka, distributed-systems]` and `tags: [consumer-groups, rebalancing,
performance]`, and the build emits `topics/kafka.md`, `topics/distributed-systems.md`,
`tags/performance.md` — each listing the doc with its title, status, confidence, and
staleness. Those generated index files are **committed to the repo**, not build-only, so
the degraded state (build script gone) still navigates: you open `topics/kafka.md` in vim
or on github.com and follow relative links.

Committing generated files has a cost — six tools regenerating concurrently will conflict.
Mitigation is a deterministic sort order (so the diff is minimal and stable) plus a rule
that these files are **never merged by hand: on conflict, take either side and re-run the
generator**, with CI regenerating and failing if the working tree comes back dirty. That
makes drift impossible without making merges painful.

### Q2. Where do the five content types live — directory, frontmatter field, or both?

**Both, with the directory derived from the field, and the validator enforcing that they
agree.**

Redundancy is normally a smell, but it is correct here because the two representations
serve different consumers and a validator makes divergence impossible:

- The **frontmatter field** is required because agents filter on it, the catalog keys on
  it, the HTML template branches on it, and it must survive a document being moved.
- The **directory** is required because it is the *only* type signal that survives the
  build script vanishing, a file being copy-pasted out, a raw URL being shared into a
  chat, or a ripgrep hit being read out of context.

That last point is why `notes/` (research notes / raw AI output) **must** be a directory
and not merely a field. The brief's requirement is that raw AI output is never mistaken for
a curated explainer. A path containing `/notes/` communicates that in every context a
document can appear in — a URL in a Slack message, a `rg -l` result, a browser tab, an
agent's citation. A frontmatter field communicates it only to something that parsed the
file. **Path-visible separation is a safety property, not a convenience.** The same logic
applies to any private/client shelf if the panel decides to have one.

Validator rule: `frontmatter.type` MUST equal the shelf directory name (singularized).
Mismatch fails CI. This also gives the contribution contract a one-line rule an agent
cannot misread: *put the file in the folder named after its type.*

### Q3. Directory depth, and the rule that stops it growing

**Maximum three levels below the repo root for content**, i.e.
`kb/<type>/<slug>.md` (2 levels) or `kb/<type>/<bundle-slug>/<file>` (3 levels).

The stopping rule, restated: **depth expresses composition, not classification.**

- Legal: `kb/diagrams/acme-payments-container/` — because a diagram is genuinely several
  files (`.mmd` source, `.svg` render, `index.md` narrative) that constitute *one artifact*.
- Illegal: `kb/explainers/streaming/kafka/consumers/rebalancing.md` — "more docs about
  Kafka" is a facet problem. Adding depth for it converts a free reclassification into an
  expensive file move.

Two mechanical CI checks make this enforceable rather than aspirational:

1. No content path may exceed the depth limit.
2. No directory below `kb/<type>/` may contain another directory. (A bundle is a leaf.)

There is exactly one sanctioned escape hatch, defined in Q4 and §4, and it adds **one**
level, once, under a triggering condition — never a general licence to nest.

### Q4. Topic sprawl: 200 topics, 6 uncoordinated tools. Controlled vocabulary?

**Yes, you need one. No, nobody will maintain it. Therefore make it generated and advisory
rather than curated and mandatory.** Anything that requires a human to approve a term
before an agent can file a doc will be bypassed within a month.

The design, in four parts:

**(a) Constrain shape, not membership.** `topics` is lowercase kebab-case ASCII, **maximum
3 per document, first one is primary**. The cap is the actual sprawl control: it forces the
writer to name the subject rather than sprinkle `architecture`, `best-practices`, and
`overview` on everything. Free-form `tags` are unlimited-ish but capped at ~8 and carry no
navigational guarantees. Membership is open — any agent may invent a topic.

**(b) The vocabulary file is a census, not a law.** `taxonomy/topics.yml` is **generated**
by the build from what is actually in use, with document counts, sorted alphabetically.
The contribution contract tells an agent: *before inventing a topic, grep
`taxonomy/topics.yml`; if something within an obvious synonym of your term already exists,
use that instead.* That costs one file read and one grep — cheap enough that it will
actually happen. It is a reuse *nudge*, and nudges are all you get from uncoordinated
writers.

**(c) Synonym repair is opt-in and lazy.** `taxonomy/aliases.yml` maps
`k8s: kubernetes`, `postgres: postgresql`. It is hand-written, starts empty, and grows only
when someone notices a duplicate. **If nobody ever touches it, nothing breaks** — you
simply get two census entries, which sit adjacent-ish in the generated topic index, which
is precisely how a human notices and fixes it in one line. Compare this to the
topic-as-directory design, where the same mistake costs a file move plus tombstones plus
link rewrites. *The system is designed so that being wrong is cheap.*

**(d) CI reports vocabulary problems; it never fails on them.** The build emits a summary:
singleton topics (used once), near-duplicates by normalized edit distance and simple plural
folding, and topics that appeared this month. Strong opinion: **never fail CI on taxonomy.**
Fail CI on provenance and schema — those are facts about the file and an agent can always
comply. Failing on taxonomy trains agents to game the taxonomy (pick whatever term passes)
and trains humans to disable the check. Provenance is enforced; vocabulary is observed.

**What happens after six months of total neglect?** Topics fragment into maybe 260 terms
where 200 would do; the generated indexes still build; every document still has a canonical
home, a working path, and valid provenance; ripgrep still finds things by body text
regardless of tags. That is a graceful, recoverable degradation — an afternoon with
`aliases.yml` repairs it without touching a single file path. Contrast with a topic-folder
scheme after six months of neglect: 260 directories, many with one file, and repair means
moving files and breaking URLs.

### Q5. Naming and addressing so links don't break

**Filename:** `<slug>.md`, lowercase kebab-case, ASCII only, no dates (except `notes/`), no
tool or model names, shaped `<subject>-<aspect>` — `kafka-partition-rebalancing`, not
`kafka` and not `kafka-deep-dive-v2-final`. ASCII-and-lowercase is not fussiness: GitHub
Pages is case-sensitive while macOS checkouts are not, and that mismatch produces links
that work locally and 404 in production.

**Identity:** `id` in frontmatter equals the slug at creation time and is **immutable
forever**. Titles may change freely; the slug may not. Citations, `related:` edges, and the
catalog key all use `id`. The path may change; the id may not. This is the Johnny Decimal
lesson (identity decoupled from location) implemented with a readable token instead of a
number.

**Links between documents:** the primary form is a **normal relative markdown link**, not
an id macro. This is forced by the graceful-degradation requirement: relative links resolve
on github.com, in a text editor's follow-link, and in any markdown renderer, with no build
step. An id-based link syntax would be more durable but would render as inert text
everywhere the build script isn't. The validator checks every relative link resolves.

**Moves and renames** are therefore a *tooling* problem, and the tool is
`scripts/kb mv <old> <new>`, which atomically:
1. moves the file (`git mv`),
2. appends the old path to `aliases:` in frontmatter,
3. rewrites every inbound relative link in the corpus (deterministic, greppable),
4. writes a **tombstone stub** at the old path: frontmatter with `redirect_to: <id>`, plus
   one human sentence and a relative link.

Tombstones matter because they are the only thing that keeps *external* references alive —
a `raw.githubusercontent.com` URL pasted into another tool's memory six months ago, or a
Pages URL in a bookmark. A 200 with a pointer beats a 404. They cost six lines each. Cost
honestly stated: tombstone litter accumulates, and there is no way to measure whether one
is still needed (no analytics on a static site), so in practice you keep them all. At 1,000
docs with, say, 50 lifetime moves, that is 50 stubs — acceptable. If it ever isn't, they
are trivially bulk-deletable, and the validator can list them.

**URL ↔ path mapping must be trivially guessable in both directions.** This is an IA
requirement, not just a build detail: an agent that finds an HTML page in a search engine
must be able to derive the raw markdown URL, and vice versa, without an index lookup. Rule:
the site path is the repo path minus the extension. `kb/explainers/kafka-partition-
rebalancing.md` → `/kb/explainers/kafka-partition-rebalancing/`. No path stripping, no
flattening, no build-time renaming, no clever prettification.

**Collisions between uncoordinated writers.** If `<slug>.md` already exists, an agent must
NOT silently create `<slug>-2.md`. The contract says: either update the existing document
(recording itself in the provenance chain) or choose a genuinely distinct slug that names
the different aspect. A same-day, same-path collision from two tools surfaces as a git
add/add merge conflict — loud, unmissable, and correct. In `notes/` alone, where collisions
are likely and duplication is *fine* (raw session output is inherently per-session),
filenames are `YYYY-MM-DD-<slug>.md`, which makes accidental collisions nearly impossible
and gives the shelf a natural chronological order.

---

## 3. Worked examples

Top-level layout used by all examples (Option A, my preference):

```
/
  README.md                 # human entry point
  AGENTS.md                 # contribution contract
  llms.txt                  # agent entry point
  kb/
    explainers/             # the bulk
    diagrams/               # bundles: source + render + narrative
    snippets/               # runnable examples, config samples
    prompts/                # prompts, skills, agent artifacts
    notes/                  # raw AI output, date-prefixed, never curated
  topics/                   # GENERATED, committed
  tags/                     # GENERATED, committed
  index/                    # GENERATED, committed (by-type, by-status, recent, stale)
  taxonomy/
    topics.yml              # GENERATED census with counts
    aliases.yml             # hand-written, may remain empty forever
  templates/                # one per content type
  scripts/                  # build, validate, kb mv
  docs/design/              # this panel's own documents (not knowledge content)
```

Note for the Pages engineer: the knowledge base is deliberately **not** under `/docs`,
because GitHub Pages' classic "publish from /docs" mode would then dictate our IA. Please
use an Actions-built deployment so the repo layout is chosen for readers, not for Pages.

### (a) C4 container diagram for a client system

Client material is sanitized before entry (see §1.2). Suppose the sanitized subject is
"Acme Payments Platform."

```
kb/diagrams/acme-payments-container/
  index.md          # frontmatter + narrative + embedded render
  container.mmd     # Mermaid C4 source (hand/agent authored)
  container.svg     # rendered output (generated, committed)
```

- Site URL: `https://clostaunau.github.io/UseFullknowledge/kb/diagrams/acme-payments-container/`
- Raw markdown: `https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/kb/diagrams/acme-payments-container/index.md`
- Raw source: same path, `container.mmd`

Frontmatter (IA-relevant fields only; provenance fields are the metadata specialist's):

```yaml
id: acme-payments-container
type: diagram
title: "Acme Payments Platform — C4 Container Diagram"
diagram_kind: c4-container
diagram_format: mermaid
source_file: container.mmd
rendered_file: container.svg
topics: [payments-architecture, event-driven-architecture]
tags: [c4, client-work, sanitized, microservices]
related: [kafka-partition-rebalancing]
aliases: []
```

**Why a bundle directory is legal here:** three files constitute one artifact. This is
composition, not classification.

**The `index.md` trade-off, stated honestly:** naming the narrative file `index.md` gives a
clean URL and a trivial build rule, but **github.com does not auto-render `index.md` when
you browse the folder** — it auto-renders `README.md`. So in the degraded, build-less state,
a bundle is slightly worse to browse than a bare file. I accept this because bundles are
roughly 10% of the corpus (mostly diagrams), and the alternative (`README.md` as the doc
body) is semantically confusing and collides with Jekyll/Pages special-casing. If the panel
weights github.com folder browsing highly, `README.md` is the defensible flip.

### (b) Kafka partition rebalancing explainer

```
kb/explainers/kafka-partition-rebalancing.md
```

- Site URL: `.../kb/explainers/kafka-partition-rebalancing/`
- Raw: `.../main/kb/explainers/kafka-partition-rebalancing.md`

```yaml
id: kafka-partition-rebalancing
type: explainer
title: "Kafka Partition Rebalancing"
topics: [kafka, distributed-systems]
tags: [consumer-groups, rebalancing, performance, cooperative-sticky]
related: [acme-payments-container, kafka-consumer-config-baseline]
aliases: []
```

This document "belongs in three places" — Kafka, distributed systems, performance. It sits
in exactly one, and appears in three generated indexes: `topics/kafka.md`,
`topics/distributed-systems.md`, `tags/performance.md`. It also gains an automatic backlink
on the Acme diagram page, because it declared `related`.

An agent with no prior knowledge does one of:
- `rg -l 'partition rebalanc' kb/` — works with no index at all;
- `ls kb/explainers/ | rg kafka` — works with no index at all;
- read `llms.txt` → `catalog.json` → filter `type == explainer AND 'kafka' in topics AND
  review_status == verified AND not stale`.

All three paths work; the first two survive the build script's disappearance.

### (c) Third example: the same subject, different type

To show the type-first split concretely, a runnable consumer config for the same subject:

```
kb/snippets/kafka-consumer-config-baseline.md
```

with `topics: [kafka]`. Note that the Kafka explainer, the Kafka snippet, and the Acme
diagram now live in three different shelves. They are reunited **only** in
`topics/kafka.md` (generated) and in `catalog.json`. This is the central cost of my
preference, and I address it head-on in §5.

---

## 4. Three structural options I will defend

### Option A — **Type Shelf + Facets** (my recommendation)

`kb/<type>/<slug>.md`, or `kb/<type>/<slug>/index.md` for bundles. Type is the only
mandatory directory axis. Topics and tags are frontmatter facets. All subject-oriented
navigation is generated and committed. Depth ≤ 3, hard-capped by "composition not
classification."

**Sprawl escape hatch, with a numeric trigger:** when any single shelf directory exceeds
**150 files**, and only then, introduce **one** grouping level *under that shelf only*,
using a **closed list of ≤12 coarse domains decreed at that moment** (e.g. `computing`,
`life-sciences`, `physical-sciences`, `mathematics`, `business`, `craft`, `meta`) — chosen
from the *actual topic census*, which by then contains real data instead of guesses.
`kb/explainers/computing/kafka-partition-rebalancing.md`. The list is closed by decree; a
document that doesn't fit goes in `general` and stays there.

Deferring this is defensible **only because re-shelving is cheap in this design**:
`kb mv` handles the move, the alias, the tombstone, and the inbound link rewrite, and `id`
never changes. That is a real bet, and I name it as a bet in §5.

**Wins when:** contributors are uncoordinated (type is the only thing they'll all get
right); the corpus is heterogeneous; you want zero taxonomy arguments at filing time; you
want reclassification to be free.
**Loses when:** the primary human access pattern is "show me everything about X" and the
build is broken; when someone genuinely wants to browse source directories by subject.

### Option B — **Domain Shelf** (subject-first, closed top level)

`kb/<domain>/<topic-slug>/<type>-<slug>.md`, e.g.
`kb/computing/kafka/explainer-partition-rebalancing.md` and
`kb/computing/kafka/diagram-consumer-group-rebalance/`. `<domain>` is a **closed** list of
~10 decreed at day zero; `<topic>` is open. Type moves into the filename prefix (still
greppable, still visible in results) plus frontmatter.

**Wins when:** humans browse by subject and want all artifacts about a subject colocated;
when the build is unreliable and you need subject navigation with zero tooling; when a
single curator with taste is doing the filing.
**Loses when:** six uncoordinated agents must pick a domain and a topic folder for
"Kafka on Kubernetes for a fintech client" — that decision has no right answer and it is
encoded in the URL. Also loses the path-visible `notes/` safety boundary unless `notes` is
kept as a sibling of the domains (I would insist on that). Topic-folder proliferation
(200 folders, many with one file) and the expensive-to-fix vocabulary drift are the real
killers at our contributor model.

### Option C — **Flat Pool + Generated Everything**

`kb/<type>__<slug>.md` in a single directory (optionally sharded `kb/<YYYY>/` purely to keep
directory sizes sane). Zero classification decisions; the double-underscore keeps type
greppable and sortable. All navigation — type, topic, tag, status — is generated.

**Wins when:** contribution friction must be as close to zero as physically possible; when
retrieval is 95% ripgrep and catalog queries; when you're confident the build and the
catalog will always be there.
**Loses when:** the build script is gone (it degrades to a pile), when browsing source on
github.com (pagination/truncation at scale), and it maximizes filename-collision pressure
across six writers. It also fails the brief's "navigable in a plain text editor" test more
than the others.

### Preference and why

**Option A.** The decisive argument is the contributor model. We have six tools that never
talk; the *only* classification question all six will answer identically is "what kind of
artifact is this?" Every other axis I could put in the tree is a coin flip encoded into a
URL. Option A puts the coin flips in YAML, where being wrong costs one line and no link
breaks — and puts the certainty in the filesystem, where it earns the graceful degradation
the brief demands.

Second reason: Option A is the only one of the three where the **safety-critical boundary**
(curated docs vs. raw AI output) is a first-class, path-visible, always-true fact.

Third: it is the cheapest to start and the cheapest to change. It needs no vocabulary on
day zero, no decreed domain list I'd be guessing at with zero documents in hand, and no
central allocator.

If the panel wants insurance, I will happily defend **A + B's one good level**: Option A
with the domain grouping introduced at the 150-file trigger. That is my actual expected end
state at 1,000 docs; I just refuse to guess the domain list before the census exists.

---

## 5. Honest downsides of my own preference

1. **Type-first splits subject-mates.** The Kafka explainer, the Kafka snippet, and the
   Kafka diagram live in three different trees. Reuniting them depends on
   `topics/kafka.md` being generated. Basic navigability survives a dead build script;
   the *nicest* navigation does not. Partial mitigation, and I want it in the contract:
   the topic slug should appear in the filename wherever it's natural, so
   `rg -l kafka kb/` and `ls kb/*/ | rg kafka` both work with no tooling whatsoever. That
   is a convention, not an enforcement, and conventions decay.

2. **Facets-not-folders means vocabulary drift is guaranteed, and I've deliberately chosen
   not to block it.** At 1,000 docs, expect 240–280 topic terms where 200 would do. I
   consider this strictly better than the alternative failure (documents in the wrong
   folder, repaired only by breaking URLs), but it is a real cost and the census/report is
   only as useful as someone's willingness to read it.

3. **"Flat until 150" defers a migration that may never happen.** If phase 2 ships without
   a working `kb mv`, the 150-file trigger will fire, moving 400 files will look expensive,
   and the shelf will just stay flat and unpleasant. **My preference is contingent on the
   move tooling actually being built** — I'd rather the panel treat `kb mv` (move + alias +
   tombstone + inbound link rewrite) as a phase-2 deliverable than treat it as optional
   polish. If the DX engineer says it isn't happening, I switch my recommendation to
   Option A *with* the domain level from day zero and accept the guessing.

4. **Committed generated indexes create merge conflicts.** Six tools, concurrent PRs, same
   `topics/kafka.md`. The regenerate-don't-merge rule handles it, but it is friction that a
   build-only index wouldn't have. I accept it because build-only indexes fail the
   degradation requirement.

5. **`index.md` bundles lose github.com's folder auto-render**, as detailed in §3(a).

---

## 6. What I need from the other experts

- **Metadata specialist:** `id`, `type`, `topics`, `tags`, `related`, `aliases`, and
  `redirect_to` are load-bearing for this IA. Please treat them as required schema (with
  `aliases: []` and `related: []` explicitly empty rather than omitted, so "never moved" is
  unambiguous the same way "never updated" must be).
- **Pages engineer:** Actions-built deployment, not "publish from /docs", so the IA isn't
  dictated by Pages. Also please confirm the repo-path → site-path mapping stays 1:1 and
  guessable, and that tombstones render as pages rather than 404s.
- **Retrieval engineer:** `catalog.json` keyed by `id` (not path) is the contract that lets
  paths move without breaking agent references. Also, please confirm that ripgrep over
  `kb/` remains a first-class supported retrieval path at 1,000 docs — the whole
  "facets over folders" argument depends on lexical search being good enough that a wrong
  tag is not a lost document.
- **DX engineer:** `scripts/kb mv` as a phase-2 deliverable (see downside 3), plus the two
  depth checks and the `type`-matches-directory check in the validator.
- **Technical writer:** the entire contribution contract for filing reduces to five lines —
  pick the shelf named after your type, pick a kebab slug that doesn't already exist, ≤3
  topics grepped from `taxonomy/topics.yml` first, never touch `topics/` or `index/` by
  hand, date-prefix anything in `notes/`. If it can't be said in five lines, I've designed
  it wrong.
- **Skeptic:** my three known-weak points are listed in §5. The one I most want attacked is
  #3 — whether "flat until 150" is genuine YAGNI or wishful thinking about a migration
  nobody will perform.
