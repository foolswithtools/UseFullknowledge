# Position: Agent-Facing Retrieval

**Role:** AI Retrieval / RAG Engineer
**Scope:** how a heterogeneous AI agent finds the right document in this repo, and how it
filters that document set by trust.
**Date:** 2026-08-14

---

## 0. Method note — these numbers are measured, not estimated

Every size and timing in this document came from a real experiment, not a guess. I
generated a synthetic corpus matching the stated scale target — **1,000 documents across
200 topics, 6 contributing tools, 5 content types**, with realistic explainer lengths
(700–2,600 words) and a Zipfian vocabulary of ~33,000 unique terms — then built and
measured every index option against it.

Corpus properties (these drive everything downstream):

| Property | Measured |
|---|---|
| Total corpus size | 12.9 MB markdown / 1.32 M words |
| Median document | 12,877 B ≈ **3,219 tokens** |
| p90 document | 23,666 B ≈ 5,900 tokens |
| Largest document | 34,297 B ≈ 8,574 tokens |
| Docs per topic | 5.0 mean |

Caveat I owe you: synthetic prose has a slightly fatter identifier tail than real prose,
so full-text index sizes below may be ~10–20% high. The *ratios* between options, which is
what the decision turns on, are unaffected. Timings are on this machine, warm cache.

---

## 1. The entry point: `llms.txt`

### What it actually is

`llms.txt` is a convention proposed by Jeremy Howard of Answer.AI on 2024-09-03. It is a
**markdown file at the site root** with a rigid top-level shape:

- An H1 with the project name (required, and the only required element)
- A blockquote with a short summary
- Optional free prose giving context
- H2 sections, each containing a markdown **list of links, each with a description after a
  colon**
- A section literally named `## Optional`, which carries special meaning: an agent short on
  context is invited to skip it

`llms-full.txt` is the sibling convention: **the entire documentation corpus concatenated
into one markdown file**, so a model can slurp everything in a single HTTP request.

### Its actual adoption status — be honest about this

The convention is widely *published* and almost never *consumed*.

- Adoption sits around **8.7% of the Tranco top 1,000 (June 2026)** and ~10.1% across a
  300,000-domain sample. Developer-facing SaaS adopted it heavily through 2025; mainstream
  adoption followed in 2026 Q1.
- But crawler telemetry is damning: across **500M+ AI bot visits in a 90-day window, only
  408 requests targeted `/llms.txt` at all**. GPTBot, ClaudeBot, PerplexityBot,
  OAI-SearchBot and Google-Extended overwhelmingly ignore it and crawl HTML directly.
- Google's June 2026 documentation update states plainly that `llms.txt` has **no effect**
  on Search rankings or AI Overviews. Search ignores the file.

**So why have one here at all?** Because this repo's access pattern is fundamentally
different from the SEO pattern. Nobody is waiting for ClaudeBot to spontaneously discover
this KB. The real flow is: *the user tells their agent "our knowledge base is at
github.com/clostaunau/UseFullknowledge"*, and the agent then needs a predictable, cheap,
zero-prior-knowledge place to start. `llms.txt` is excellent at that job. It fails as a
passive crawler protocol; it succeeds as a **directed entry point**, which is exactly the
job we need done.

Corollary: do not spend one minute optimizing `llms.txt` for AI search visibility. Optimize
it purely as a routing document for an agent that has already been pointed at the repo.

### Is it enough on its own? No.

Two hard limits:

1. **It is a flat link list with no query capability.** With 200 topics it becomes a
   200-line list. That is survivable, but it cannot express "verified only" or "not stale"
   — the entire point of this system.
2. **`llms-full.txt` is arithmetically impossible here.** Concatenating all 1,000 documents
   yields **12.9 MB ≈ 3.23 million tokens**. That does not fit in any context window at any
   price. Measured, not theorized.

`llms.txt` must therefore be a **router into a machine-queryable catalog**, not a
destination. Its job is to get an agent from zero knowledge to the right catalog shard in
one hop.

### What it must contain so a Kafka explainer is 1–2 fetches away

Not a list of 1,000 documents. A list of *access methods*, plus the URL templates that let
an agent construct its next fetch without another round trip. The template line is the
critical trick: it converts "browse until you find it" into "compute the URL and fetch it."

### Concrete `llms.txt` draft for this repo

```markdown
# UseFullknowledge

> A provenance-tracked knowledge base of explainers, diagrams, code snippets, prompts and
> research notes produced by many different AI tools. Every document records what created
> it, when, whether a human reviewed it, and when it goes stale. 1,000+ documents across
> 200+ unrelated topics. Markdown is the source of truth; HTML is generated.

READ THIS FIRST — how to query this repo in 2 fetches:

1. Fetch the topic router (~17 KB, lists every topic with document counts):
   https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/catalog/index.json
2. Pick the topic slug you want, then fetch its shard (~6 KB):
   https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/catalog/topics/{topic}.json
3. Each shard entry has `path`, `review_status`, `expires_on` and `confidence`.
   Fetch the document at:
   https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/{path}

TRUST RULES — apply these before using any document as context:
- `review_status` is one of: unreviewed | reviewed | verified. Prefer `verified`.
- A document is STALE if `expires_on` is a date earlier than today. `expires_on: never`
  means it does not expire. Compare against today's date yourself; do not trust a
  cached boolean.
- `confidence` (high|medium|low) is the AUTHOR's self-assessment, not a review. An
  `unreviewed` + `high confidence` document is still unreviewed.
- Documents under `kb/note/` are RAW AI OUTPUT, deliberately not curated. Do not treat
  them as reviewed explainers.

## Catalog

- [Topic router](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/catalog/index.json): every topic slug, document count, verified count, last-updated date. Start here.
- [Topic aliases](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/catalog/aliases.json): maps common synonyms to canonical topic slugs (e.g. `kafka` → `kafka-partition-rebalancing`). Check this if your topic guess misses.
- [Verified + fresh fast path](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/catalog/verified.json): pre-filtered to human-verified, non-expired documents only (~100 KB). Use when you need trustworthy context and do not care about topic breadth.
- [Schema](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/catalog/schema.json): JSON Schema for a catalog entry and for document frontmatter.

## Conventions

- [AGENTS.md](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/AGENTS.md): how to FILE a new document correctly. Read before writing.
- [Taxonomy](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/docs/taxonomy.md): path layout, naming rules, content types.
- Paths follow `kb/{type}/{topic-slug}/{topic-slug}-{type}-{nnnn}.md` where type is one of
  explainer, diagram, snippet, prompt, note.
- Frontmatter keys are FLAT and line-anchored, so `rg '^review_status: verified'` works.

## If you have a shell and a clone

    git clone --depth 1 https://github.com/clostaunau/UseFullknowledge
    rg -l '^review_status: verified' -g '*kafka*' kb/

Full recipes: [docs/agent-queries.md](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/docs/agent-queries.md)

## Optional

- [Human-browsable site](https://clostaunau.github.io/UseFullknowledge/) — rendered HTML with Pagefind search. Not needed by agents; raw markdown is always preferable.
- [Changelog](https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/CHANGELOG.md)
```

Note the deliberate spec violation: I put imperative instructions *above* the first H2. The
spec allows free prose there, and every real agent reads top-down. The trust rules are the
single most important thing in the file and they do not belong in a link list.

---

## 2. Catalog design — the flat manifest fails, and here is the arithmetic

I built the obvious `catalog.json` — one array, one full record per document — and measured
it.

| Variant | Bytes | gzip | ≈ tokens |
|---|---:|---:|---:|
| **Flat `catalog.json`, full records** | **1,081,457** | 242,083 | **~270,000** |
| Same, pretty-printed | 1,250,658 | 249,571 | ~313,000 |
| Same as NDJSON | 1,081,390 | 242,055 | ~270,000 |
| Slim (abbreviated keys, 9 fields) | 279,199 | 53,511 | ~70,000 |
| Tiny (4-element arrays, no titles) | 123,303 | 15,711 | ~31,000 |

**Verdict: the flat catalog blows the context window.** 270k tokens is larger than most
agents' entire budget, and even the "tiny" 31k-token variant is an absurd toll to pay
before you have retrieved a single document. Worse, gzip does not save you — HTTP
decompresses before the agent sees it, so the agent pays the **uncompressed** token cost.
The gzip column only matters for transfer time, never for context.

Note also that agents which can only fetch HTTPS often cannot stream or range-request; they
get the whole file or nothing. A 1 MB catalog is a wall.

### Therefore: a three-tier manifest

```
llms.txt                          ~3 KB      Tier 0  — how to query, trust rules
catalog/index.json                17,458 B   Tier 1  — 200 topics, routing only
catalog/topics/{topic}.json       ~5,936 B   Tier 2  — full records for ONE topic
kb/{type}/{topic}/{doc}.md        ~12,877 B  Tier 3  — the document
```

Measured Tier 1 (the topic router), two encodings:

| Encoding | Bytes | ≈ tokens |
|---|---:|---:|
| Readable object form | 17,458 | ~4,364 |
| Minified array form | 5,834 | ~1,458 |

**I recommend the readable 17 KB form.** The 3k-token saving from the array form is not
worth making the file unreadable to the agent — an LLM reasons far better over
`{"n":5,"v":2}` with named keys than over `["kafka",5,2]`, and 4.4k tokens is an entirely
acceptable routing cost.

Measured Tier 2 (per-topic shards, 200 files): **median 5,936 B (~1,484 tokens), max
10,924 B (~2,731 tokens), 1.2 MB total on disk.**

### The end-to-end cost, measured

An HTTPS-only agent answering *"give me verified, non-stale Kafka documents"* from zero
knowledge:

| Step | Bytes | ≈ tokens |
|---|---:|---:|
| 1. `llms.txt` | ~3,000 | ~750 |
| 2. `catalog/index.json` | 17,458 | ~4,364 |
| 3. `catalog/topics/kafka-partition-rebalancing.json` | 6,242 | ~1,560 |
| 4. The document itself | ~12,877 | ~3,219 |
| **Total** | **~39,577** | **~9,900** |

**~10k tokens from zero knowledge to a trust-filtered document in hand, three fetches
before the document.** Against 270k tokens for the flat catalog alone, this is a 27×
reduction on the index and it never degrades as the corpus grows — Tier 1 grows with
*topic* count, not document count, and Tier 2 stays ~6 KB no matter how large the corpus
gets. That scaling property is the whole reason to tier.

### Concrete catalog entry schema (Tier 2)

```json
{
  "topic": "kafka-partition-rebalancing",
  "generated_at": "2026-08-14T09:00:00-05:00",
  "docs": [
    {
      "id": "kafka-partition-rebalancing-explainer-0400",
      "path": "kb/explainer/kafka-partition-rebalancing/kafka-partition-rebalancing-explainer-0400.md",
      "title": "Kafka Partition Rebalancing: cooperative sticky assignor",
      "type": "explainer",
      "summary": "Why eager rebalancing stops the world, how the cooperative sticky assignor avoids it, and the session/heartbeat timeouts that actually trigger a rebalance.",
      "review_status": "verified",
      "reviewed_at": "2026-05-02",
      "reviewer": "chris",
      "expires_on": "never",
      "confidence": "high",
      "updated_at": "2026-05-02",
      "tool": "claude-code",
      "words": 1840
    }
  ]
}
```

**Per-entry cost breakdown** (measured mean 1,066 B for the *full* record; the trimmed
Tier 2 record above averages ~590 B):

| Field group | ≈ bytes | Keep in Tier 2? |
|---|---:|---|
| `id` + `path` | 160 | Yes — path is the whole point |
| `title` + `summary` | 230 | Yes — this is what the agent matches on |
| trust block (`review_status`, `reviewed_at`, `reviewer`, `expires_on`, `confidence`) | 110 | **Yes — non-negotiable** |
| `type`, `updated_at`, `tool`, `words` | 90 | Yes, cheap |
| `model`, `session`, `confidence_basis`, `sources`, `tags`, `domain` | ~476 | **No** — read from the document's own frontmatter when needed |

That last row is where the flat catalog died: `confidence_basis`, `sources` and `session`
are ~45% of every record and are needed only *after* you have chosen a document. Provenance
must be *complete in the document* and *sufficient in the catalog*. Those are different bars
and conflating them is what produces a 1 MB manifest.

**Also generate `catalog/verified.json`** — the pre-filtered verified + non-expired set.
Measured: **99,534 B for 92 documents (~24,900 tokens)**. That is too big to read whole, but
it is the right shape for `jq` in shell mode and it is a genuinely useful fast path for "I
don't care about the topic, I care that it's true."

---

## 3. Ripgrep-first retrieval — and when it genuinely beats a vector store

**This is the honest headline: at 1,000 documents, ripgrep over well-named files beats a
vector store on every axis that matters here except synonym recall.**

Measured on the 1,000-document corpus (13 MB), warm cache:

| Query | Time |
|---|---:|
| `rg --files -g '*kafka*'` (filename glob) | **14 ms** |
| `rg -l '^review_status: verified'` | **19 ms** |
| `rg -l '^review_status: verified' -g '*kafka*'` | **16 ms** |
| Full trust pipeline (verified + non-stale + topic) | **22 ms** |
| Two-pass intersection via `comm` | 38 ms |

Twenty-two milliseconds, zero build step, zero index to keep in sync, zero dependency,
works on a plane. A vector store would need a model, an embedding pass, and an index file,
and would answer the *same* query worse (see §5). At this scale it is not close.

### The conventions that make `rg` work

Three rules. All three are load-bearing; drop any one and grep degrades to guessing.

**1. Topic slug appears in the directory name AND the filename.**
`kb/explainer/kafka-partition-rebalancing/kafka-partition-rebalancing-explainer-0400.md`
The redundancy looks silly and is deliberate: it makes `-g '*kafka*'` a *prefilter* that
works before reading a single byte of content, and it makes the path self-describing in
`rg` output with no extra flag.

**2. Frontmatter keys MUST BE FLAT. This is not a style preference — I measured it
breaking.**

With nested YAML (`review: { status: verified }`), the emitted file contains
`  status: unreviewed` with leading indentation. Measured on the same corpus:

```
rg -l '^status: verified'      →   0 files   # anchor fails, silently
rg -l '^  status: verified'    → 172 files   # works, but depends on YAML emitter indent
rg -l 'status: verified'       → 172 files   # works, but also matches BODY prose
```

**A nested trust field returns zero results from the obvious query and gives no error.**
That is the worst possible failure mode — a retrieval system that confidently reports "no
verified documents exist." Flattening to `review_status: verified` makes `^review_status:`
a reliable anchor that cannot match body text and cannot break when a different tool's YAML
emitter chooses two-space vs four-space indentation. With six tools that never talk to each
other, that last point is not hypothetical.

Flat keys: `review_status`, `reviewed_at`, `reviewer`, `expires_on`, `confidence`,
`confidence_basis`, `created_at`, `updated_at`, `updated_by`, `tool`, `model`, `session`.
Only `topics`, `tags` and `sources` are lists (they must be), and list items get the
`^- ` anchor.

**3. Headings are predictable.** Every explainer opens with `# {Title}` and uses a fixed
set of H2s where possible (`## Summary`, `## How it works`, `## Gotchas`, `## Sources`), so
`rg -A5 '^## Summary'` extracts an abstract from any document without parsing.

### Real commands an agent would run

```bash
# Q1 — find by topic, cheapest possible: filename only, no content read
rg --files kb/ -g '*kafka*'

# Q2 — find by concept in body, case-insensitive, list files only
rg -il 'partition rebalanc' kb/ -g '*.md'

# Q3 — PROVENANCE FILTER: every verified document, anchored so body text can't match
rg -l '^review_status: verified' kb/

# Q4 — verified AND about Kafka (glob prefilter makes this cheaper than the unfiltered Q3)
rg -l '^review_status: verified' -g '*kafka*' kb/

# Q5 — THE TRUST QUERY: verified + not stale + topic, one pipeline, 22 ms
rg -l '^review_status: verified' -g '*kafka*' kb/ -0 \
  | xargs -0 rg -H -o -m1 '^expires_on: .*' \
  | awk -F'expires_on: ' -v today="$(date +%F)" \
      '{f=$0; sub(/:expires_on.*/,"",f); if ($2=="never" || $2 > today) print f}'
# → kb/explainer/kafka-partition-rebalancing/kafka-partition-rebalancing-explainer-0400.md

# Q6 — exclude raw AI output; curated content only
rg -l '^review_status: verified' kb/ -g '!kb/note/**'

# Q7 — what did a specific tool produce that nobody has reviewed?
rg -l '^tool: cursor' kb/ | xargs rg -l '^review_status: unreviewed'

# Q8 — pull just the summary of every verified Kafka doc, no full reads
rg -l '^review_status: verified' -g '*kafka*' kb/ | xargs rg -A4 '^## Summary'
```

`expires_on` being an **ISO-8601 date makes `>` a correct lexicographic comparison in
`awk`**, which is why the trust query is one pipeline and not a Python script. That is a
direct payoff from a schema decision.

### Failure modes — stated honestly

| Failure | Severity | Mitigation |
|---|---|---|
| **Synonyms.** Agent greps `message queue`, document says `Kafka topic partition`. Zero hits. | **High — this is grep's real weakness** | `catalog/aliases.json` (measured: **163 bytes** for a starter map). Plus: the agent should route through Tier 1's topic list, which an LLM matches semantically *for free* using its own weights. This is the key insight — see §5. |
| **Frontmatter vs body confusion.** `rg 'verified'` matches prose "we verified that…". | Medium | Solved by flat keys + `^` anchor. Enforce in the validator; forbid the string `review_status:` in body text. |
| **No semantic match.** "How do I stop consumer group thrash?" matches nothing lexically. | High | Same mitigation: route via the topic router, not via full-text grep. |
| **Multi-field AND across frontmatter** needs multiline or two passes. | Low | The `-U '(?s)...'` form works but is brittle; prefer the `xargs` pipeline in Q5. |
| **Case and hyphenation drift** (`Kafka` / `kafka` / `apache-kafka`) across 6 tools. | Medium | Validator enforces lowercase-kebab slugs against a controlled topic list; new topics require an explicit addition. |
| **`rg` mode is unavailable to 2 of 3 access modes.** | **Structural** | This is why §2's catalog exists. Grep is not sufficient alone. |

---

## 4. Lexical static search index — measured, all four options

Built every candidate against the same 1,000 documents.

| Option | Index size | gzip | Client downloads before 1st query |
|---|---:|---:|---|
| **lunr.js** (full body) | 12,824,509 B | 3,659,660 B | **12.8 MB — all of it** |
| lunr + required docstore | 12,992,848 B | 3,689,531 B | 13.0 MB |
| **MiniSearch** (full body) | 5,973,815 B | 1,423,908 B | **6.0 MB — all of it** |
| MiniSearch (lead 1,200 chars) | 1,459,442 B | 334,873 B | 1.5 MB |
| MiniSearch (title only) | 269,970 B | 57,223 B | 270 KB |
| **Pagefind 1.5.2** | 11 MB on disk | — | **~125 KB + ~31 KB/chunk** |

### Pagefind's chunked model is the real advantage, and the numbers prove it

Pagefind's on-disk total (11 MB) is misleading and it is why people dismiss it. What
matters is what crosses the wire. Measured structure:

```
pagefind.js               45,555 B   ─┐
wasm.en.pagefind          72,000 B    ├─ ~125 KB baseline, once, cached
pagefind-entry.json          174 B    │
*.pf_meta                  7,878 B   ─┘
index/    108 files      3,350,248 B   mean 31,021 B/chunk — fetched ON DEMAND
fragment/ 1000 files     4,704,162 B   mean  4,704 B/doc   — one per RESULT SHOWN
filter/     2 files          3,824 B   mean  1,912 B/filter
```

A typical search fetches the 125 KB baseline (cached after first use), **1–3 index chunks
at ~31 KB**, and **one 4.7 KB fragment per result actually displayed**. Call it **~200–300
KB for a full search session** versus **6 MB before MiniSearch can answer its first
query**. On a phone on mobile data — an explicit requirement — that is a 20–30× difference
and it is the difference between "search works" and "search is a 6 MB stall."

Pagefind also scales sublinearly in *fetched* bytes: at 10,000 documents the chunk count
grows but the per-query fetch stays roughly constant. lunr and MiniSearch grow linearly in
*download*, so they have a hard ceiling. lunr at 12.8 MB is already past it at 1,000 docs;
**lunr is disqualified.**

And the filter index is nearly free: **1,912 bytes per filter**. Adding
`data-pagefind-filter="review_status"` to the generated HTML gives humans faceted
trust-filtered search for under 4 KB total. That is the cheapest win in this entire
document.

### But: Pagefind is for humans, and I verified that agents cannot use it

I attempted a headless query from Node against the generated index:

```
Error: Failed to load Pagefind metadata
    at PagefindInstance.loadEntry (.../pagefind.js)
```

Pagefind's *indexing* API works fine in Node (`pagefind.createIndex()` produced 1,123 files
successfully). Its *search* runtime assumes a browser: relative `fetch` against a document
base URL, plus WASM. It is workable with a shim, but:

- An **HTTPS-only agent cannot use Pagefind at all.** It would have to execute WASM and
  reimplement the chunk-hash routing. Absolutely not.
- An **IDE-file-tools agent cannot use it either** — it can read files, not run a WASM
  search engine.
- Only a **shell agent with Node** could, via a shim, and that agent already has `rg`,
  which is faster and needs no shim.

**Conclusion: Pagefind for the human site. Never sell it as agent infrastructure.** The
agent path is `llms.txt` → tiered catalog → raw markdown, and it is entirely independent of
Pagefind. This separation is a feature: the human search index can be rebuilt, swapped or
deleted without breaking a single agent query.

MiniSearch stays on the bench as a fallback if Pagefind's Node/CI story ever becomes a
problem — a **title-only MiniSearch index at 270 KB** would be a defensible agent-readable
artifact. But the tiered catalog already dominates it, so today: no.

---

## 5. Embeddings — a clear NO, with the trigger stated

**Verdict: NO at 1,000 documents. Not "not yet, soon" — no, and the trigger is far away.**

### What the no-external-runtime-API constraint actually forbids

Read precisely, the constraint rules out **calling a hosted embedding API at query time**
(OpenAI `/embeddings`, Voyage, Cohere). It does **not** forbid:

- Running a model **locally at build time** and committing the resulting vectors.
- Shipping a model file **in the repo** and running it locally at query time.
- Using a hosted API **once, offline, by a human**, to produce a committed artifact.

So embeddings are not *prohibited*. They are simply not *worth it*, for a reason that has
nothing to do with the constraint.

### The decisive argument: the query side, not the document side

Everyone sizes the document vectors and forgets that **semantic search requires embedding
the query with the same model at query time.**

- An **HTTPS-only agent cannot embed its query.** It has no model, no runtime, no compute.
  Committed document vectors are inert to it.
- An **IDE-file-tools agent cannot either.** It reads files; it does not run ONNX.
- Only the **shell-clone agent** could, and only after installing a runtime.

Locally, I confirmed **numpy is not installed**, and neither is torch or any ONNX runtime.
Making embeddings work would mean either `pip install sentence-transformers` (pulls ~2 GB of
torch) or `transformers.js`, which downloads a ~23 MB ONNX model from the HuggingFace CDN at
first run — an external runtime dependency in all but name. Vendoring the model in-repo to
stay clean adds ~23 MB of binary to a git repo whose entire text corpus is 12.9 MB.

**So a vector index would serve 1 of 3 access modes, at the cost of a new runtime
dependency, to solve a problem the tiered catalog already solves.**

### Because here is the thing: the consuming agent IS the embedding model

The synonym problem — grep's one real weakness — is solved for free. Give an LLM the 17 KB
topic router listing 200 slugs, and ask it "which of these covers *how do I stop consumer
group thrash?*" It answers `kafka-partition-rebalancing` correctly, using its own weights,
at a cost of ~4,400 tokens and zero infrastructure. **We are doing semantic retrieval; we
are just using the agent's own embeddings instead of shipping our own.** At 200 topics this
is not a hack, it is strictly better: no model to version, no index to drift, no
dimensionality to choose, and it improves for free every time the agent's model is upgraded.

### The size math, for the record

| Model | Granularity | float32 | int8 | JSON |
|---|---|---:|---:|---:|
| MiniLM-L6 (384d) | whole-doc (1,000) | 1.54 MB | 384 KB | 3.60 MB |
| MiniLM-L6 (384d) | chunked ~3.4/doc | 5.22 MB | 1.31 MB | 12.28 MB |
| **768d** | **whole-doc (1,000)** | **3.07 MB** | **768 KB** | **7.21 MB** |
| 768d | chunked ~3.4/doc | 10.44 MB | 2.61 MB | 24.51 MB |
| 1024d | chunked ~3.4/doc | 13.93 MB | 3.48 MB | 32.71 MB |

Note float32 vectors are **incompressible** — gzip recovers ~8%. Committing 768d whole-doc
JSON (7.21 MB) would make the vector index *half the size of the entire knowledge corpus*,
and git would store a fresh copy on every rebuild. int8 quantization at 768 KB is the only
tolerable form, and it needs custom decode code in every consumer.

Search itself is not the problem: measured **77.9 ms/query for pure-Python brute-force
cosine over 1,000×768** — no numpy, no FAISS, no HNSW needed. Brute force is fine to ~50k
vectors. The cost was never the search; it was the model.

### The numeric trigger

Add embeddings when **all three** hold:

1. **Topic count exceeds ~600**, at which point the Tier 1 router passes ~50 KB / 13k
   tokens and stops being a cheap single fetch; *and*
2. The dominant query pattern shifts from *"find the document about X"* to **"find passages
   across many documents that relate to X"** — i.e. genuine cross-document synthesis, not
   lookup; *and*
3. Retrieval failures are **measured, not imagined** — keep a `docs/retrieval-misses.md` log
   and require ≥20 real logged misses that a topic alias could not fix.

At 1,000 docs / 200 topics, condition 1 fails by 3×. Revisit at **~3,000 documents / 600
topics**. Until then this is the single most expensive way to make retrieval worse.

---

## 6. MCP server over the corpus

### Does it violate the no-server constraint?

**No.** An MCP server here would run locally over stdio on the user's machine, launched by
the client. No hosting, no auth, no paid service, no network listener. It is a subprocess,
not a server in the prohibited sense. The constraint is about *operational burden and
dependency*, and a stdio subprocess has neither. It is in scope.

### What it buys

- Typed tools (`search_kb(topic, review_status, max_age)`) instead of the agent
  reconstructing a `jq`/`rg` pipeline each time.
- The trust filter becomes **impossible to get wrong** — staleness is computed server-side
  against the real current date, and unreviewed documents can be excluded by default rather
  than by the agent remembering to.
- Results arrive pre-shaped, so no catalog parsing tokens at all.

### What it costs, and why it is not justified at 1,000 documents

- **It serves the wrong population.** MCP helps the shell/IDE agents — the two modes that
  are *already* well served by `rg` at 22 ms. The HTTPS-only agent, the genuinely
  constrained one, gains nothing.
- **Six tools that never talk to each other** means six separate MCP configurations to
  write, install and keep working across upgrades. The stated failure mode of this whole
  project is conventions being silently ignored by tools that never coordinated; MCP is
  *more* coordination surface, not less.
- **It is code that can rot.** `llms.txt` + a JSON catalog degrade gracefully — if nobody
  touches them for six months they still work. An MCP server that breaks on a Node or
  protocol version bump takes retrieval down with it and gives a confusing error while doing
  so.
- **It duplicates logic that must exist anyway.** The trust filter has to work in
  HTTPS-only mode regardless. Building it twice is how the two implementations drift.

### Verdict: LATER

Build it when **either**:

1. **The corpus passes ~2,500 documents** *and* shell-mode queries stop being one-liners
   (i.e. `docs/agent-queries.md` recipes exceed ~10 lines each); **or**
2. **≥3 of the 6 contributing tools support MCP natively** *and* you have logged ≥10
   incidents of an agent using a stale or unreviewed document because it skipped the manual
   filter.

Condition 2 is the one that will actually fire, and it fires on *observed trust failures* —
which is the correct trigger, because trust enforcement is the only thing MCP does that the
static files genuinely cannot.

---

## 7. Trust-filtered retrieval — the mechanism

This is the point of the system, so it gets the most precise specification.

### The staleness question: precomputed or caller-computed?

**Both, and the distinction is the whole design.** Separate the *fact* from the *judgment*:

- **`expires_on` is a FACT and is precomputed at build time.** The validator computes
  `expires_on = (reviewed_at or updated_at) + shelf_life_days`, writes it into frontmatter
  and into the catalog as an **absolute ISO-8601 date**, or the literal string `never`.
  This is time-invariant: it is equally true today and in three years. It never rots.
- **`is_stale` is a JUDGMENT and is computed by the caller**, as
  `expires_on != "never" && expires_on < today`.

Why not bake the boolean? Because **a boolean computed at build time is a lie the day after
the build.** If the last push was 90 days ago, a `"stale": false` flag is actively
dangerous — it asserts freshness with the authority of a generated artifact while being
wrong. In a system whose entire purpose is trust, an index that confidently mis-reports
trust is worse than no index.

The counter-argument — that HTTPS-only agents cannot compute dates — does not hold. An LLM
comparing two ISO-8601 date strings is trivially reliable, precisely *because* ISO-8601
sorts lexicographically. And the `llms.txt` trust rules state the comparison explicitly.

**Concession to pragmatism:** also emit `catalog/verified.json` (measured: 99,534 B, 92
documents) containing verified + non-expired-as-of-build documents, with a mandatory
`"generated_at"` field and this literal string inside the file:

```json
{
  "generated_at": "2026-08-14T09:00:00-05:00",
  "warning": "Pre-filtered as of generated_at. Re-check expires_on against today's date before use.",
  "docs": [ ... ]
}
```

A scheduled CI job regenerates it daily, so the convenience copy is at most 24 h stale, and
it carries the timestamp that lets a caller notice if CI has stopped running. Fast path
available, ground truth never lost.

### Mode A — shell + clone

```bash
# "verified, non-stale documents about Kafka"           [measured: 22 ms]
rg -l '^review_status: verified' -g '*kafka*' kb/ -0 \
  | xargs -0 rg -H -o -m1 '^expires_on: .*' \
  | awk -F'expires_on: ' -v today="$(date +%F)" \
      '{f=$0; sub(/:expires_on.*/,"",f); if ($2=="never" || $2 > today) print f}'
```

Or the same over the catalog with `jq`, which is installed:

```bash
jq -r --arg today "$(date +%F)" '
  .docs[]
  | select(.review_status=="verified")
  | select(.expires_on=="never" or .expires_on > $today)
  | "\(.path)\t\(.confidence)\t\(.expires_on)"
' catalog/topics/kafka-partition-rebalancing.json
```

### Mode B — HTTPS only

Three fetches, no shell, no tools. Total ~6,700 tokens before the document.

```
GET https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/llms.txt
    → learns the URL templates and the trust rules

GET .../main/catalog/index.json                              [17,458 B]
    → 200 topic slugs; agent semantically matches its question to
      "kafka-partition-rebalancing" using its own weights

GET .../main/catalog/topics/kafka-partition-rebalancing.json  [6,242 B]
    → filters entries in-context:
        review_status == "verified"
        AND (expires_on == "never" OR expires_on > <today>)

GET .../main/kb/explainer/kafka-partition-rebalancing/...md   [12,877 B]
```

The filtering happens **in the agent's reasoning, over a 6 KB JSON array** — which is
exactly the kind of work an LLM does reliably. No query language, no runtime, no server.
This mode is the design constraint that forces everything else to be simple, and it is the
reason the catalog must be small enough to read whole.

### Mode C — IDE assistant with file tools (read/glob/grep, no shell)

```
glob   kb/**/*kafka*.md                        → candidate paths from names alone
read   catalog/topics/kafka-partition-rebalancing.json   → 6 KB, all trust fields
       filter in-context exactly as Mode B
read   <the one winning path>
```

If the IDE exposes a grep primitive, `^review_status: verified` works directly — another
payoff from flat frontmatter keys, since IDE grep tools are usually line-oriented and
regex-limited, and would choke on nested-YAML matching.

### Why this works in all three modes

The trust fields exist in **two mutually redundant places**: flat, line-anchored frontmatter
in the document (which grep and file-read reach) and the per-topic catalog shard (which
HTTPS reaches). Both are generated from the same source by the same validator, so they
cannot disagree — and if the catalog is ever deleted, **frontmatter alone still answers
every trust query**. That is the graceful-degradation property the brief asks for: delete
every build artifact in the repo and Mode A still works at full fidelity.

---

## 8. Chunking — no, and the content shape says so

**Whole-document retrieval. Do not chunk.**

The measured document-size distribution decides this:

| | Tokens |
|---|---:|
| Median document | **3,219** |
| p90 | 5,900 |
| Largest in 1,000 | 8,574 |

Retrieving **three whole documents costs ~10k tokens** — routine for any current model.
Chunking exists to solve two problems, and neither one exists here:

1. **Documents exceeding the context window.** The largest document is 8.6k tokens. Not a
   problem, and not close to one.
2. **Embedding-model input limits** (typically 512 tokens). Only relevant if we were
   embedding — and §5 says we are not. Chunking is largely a *consequence* of the embedding
   decision, and dropping embeddings drops the reason to chunk.

Positive arguments against chunking here:

- **These documents are explanatory and argumentative.** An explainer of Kafka partition
  rebalancing has a thesis, a mechanism, and caveats — and the caveats section is precisely
  what a chunked retriever drops. Handing an agent chunk 3 of 7 is how you get a confident
  answer that omits "this only applies before 2.4."
- **Provenance is document-level.** A chunk severed from its frontmatter has no
  `review_status` and no `expires_on`. Every chunk would need the trust block re-attached,
  inflating the index and creating a second place for trust metadata to drift. **Chunking
  actively fights the primary requirement.**
- **Diagrams do not chunk at all.** A Mermaid or C4 source file is atomic; half a diagram is
  not a smaller diagram, it is a syntax error.
- The existing structure already provides free sub-document addressing: `## Summary`
  extracts an abstract via `rg -A5`, and heading anchors give humans and agents deep links
  without any chunk index.

**Revisit chunking only if** documents routinely exceed ~15k tokens (at which point the
right answer is probably to split the *document*, not to chunk the index) **or** if
embeddings are ever adopted under §5's trigger.

---

## 9. Three retrieval strategies I would defend

Presented as genuinely distinct options for the architecture bake-off. S1 and S2 combine
well; S3 is orthogonal and serves a different audience.

---

### Strategy A — **Convention-First Grep** (zero build artifacts)

Retrieval is a property of the *file layout*, not of any generated file. Topic slug in both
directory and filename, flat line-anchored frontmatter, fixed heading set. Agents grep. The
only generated artifact is `llms.txt`, which documents the conventions.

**Wins when:** the consuming agent has a shell; you want something that cannot break; you
value zero maintenance above all. Survives total build-script bit-rot untouched — six months
of neglect costs literally nothing. 22 ms queries, no sync problem because there is nothing
to sync.

**Loses when:** the agent is HTTPS-only (it has no usable entry beyond fetching individual
guessed URLs); or the query is semantic (`message queue` misses `Kafka`); or the user wants
a browsable overview. **Cannot serve 2 of 3 access modes.** Disqualifying on its own.

---

### Strategy B — **Tiered Static Catalog** (`llms.txt` → router → topic shard → doc)

Three generated JSON tiers as specified in §2, sized so every tier is a comfortable single
read. Trust fields live in Tier 2. Staleness is `expires_on` (fact, precomputed) plus a
caller-side comparison (judgment).

**Wins when:** the agent is HTTPS-only or IDE-bound; when you need the trust filter to work
identically everywhere; when topic count grows faster than document count. Measured ~10k
tokens from zero knowledge to a trust-filtered document. Scales cleanly — Tier 1 tracks
topic count, Tier 2 stays ~6 KB regardless of corpus size.

**Loses when:** the build script stops running — the catalog silently drifts from the
documents and, unlike Strategy A, there is no signal that it has. Requires CI discipline and
a validator that fails on drift. Also has a genuine cold-start weakness: a topic slug that
does not match the agent's vocabulary is invisible until someone adds an alias.

---

### Strategy C — **Browser Lexical Search** (Pagefind, humans only)

Pagefind over the generated HTML, with `data-pagefind-filter` on `review_status`, `type` and
`confidence`. ~125 KB baseline + ~31 KB/chunk on demand; filter index costs 1,912 B each.

**Wins when:** a human is browsing on a phone and does not know the topic slug. Faceted
trust filtering in the UI for under 4 KB. Genuinely excellent at its job.

**Loses when:** an agent tries to use it — **verified: it does not load headlessly in Node**,
and is unusable to HTTPS-only and IDE agents. It also adds a Node build dependency and 11 MB
of generated artifacts. It is not agent infrastructure and must not be counted as such.

---

### My preference

**Strategy B as the spine, Strategy A as the mandatory substrate underneath it, Strategy C
for the human site only.**

The reasoning is that A and B are not really competitors — **A is what B degrades into.**
The path and frontmatter conventions of Strategy A are what make the catalog *generatable*
in the first place, and they are what remains when the catalog is stale, deleted, or being
regenerated. Adopting B without A gives you a system with a single point of failure.
Adopting A without B abandons two of three access modes. Together they cost one build script
and give three independent working retrieval paths.

Concretely: **conventions are the contract, the catalog is a cache.** If those two ever
disagree, the documents win and CI fails.

### Downsides of my own preference, stated plainly

1. **Redundancy means two places to be wrong.** Trust fields live in frontmatter *and* in
   the catalog. Generation makes them consistent, but a validator bug or a partially
   completed build could publish a catalog asserting `verified` for a document that is not.
   Mitigation: the validator must diff catalog-against-source and fail on any mismatch, and
   the catalog must never be hand-edited. I would rather have this risk than lose graceful
   degradation, but it is a real risk and it is the failure mode most likely to bite.
2. **The topic router is a vocabulary bottleneck.** Everything rests on the agent matching
   its question to one of 200 slugs. When it guesses wrong it gets *plausible but incorrect*
   results rather than an obvious miss — the most dangerous kind of retrieval failure.
   `aliases.json` helps but is reactive: you only add an alias after someone has already
   been misrouted. This is the honest weak point of choosing no embeddings, and it will
   produce real misses.
3. **Cross-topic questions are served badly.** "What do we know about consistency across
   *all* topics?" requires either scanning 200 shards or falling back to grep. The design
   optimizes hard for *lookup* over *synthesis*, which is the right call for this content
   today, but it is a genuine capability gap and it is exactly the gap embeddings would fill.
4. **A document belonging to three topics is duplicated across three shards.** Measured
   cost: 1.2 MB of Tier 2 for a 1.08 MB flat catalog — ~11% duplication overhead, growing
   with topic promiscuity. Acceptable now; worth watching.
5. **Daily CI regeneration of `verified.json` is a cron job that can silently die.** The
   `generated_at` field makes the failure *detectable*, but only if someone actually checks
   it.

---

## 10. Upgrade ladder — what to add at N documents

| Corpus | Add | Rationale / measured trigger |
|---|---|---|
| **0–100** | Conventions + `llms.txt` + a **single flat `catalog.json`** | At 100 docs the flat catalog is ~108 KB / 27k tokens — still readable in one shot. Tiering here is premature. |
| **100–300** | Split Tier 1 router from Tier 2 topic shards; add `aliases.json` | Flat catalog crosses ~50k tokens around 200 docs. That is the tiering trigger. |
| **300–1,000** | Pagefind for the human site; `catalog/verified.json` fast path; daily CI regen | Pagefind's chunked model only pays off once there is enough content that a monolithic index would hurt. Below ~300 docs, MiniSearch at ~1.8 MB is simpler. |
| **1,000–3,000** | **Nothing new.** Harden the validator, log retrieval misses in `docs/retrieval-misses.md` | This is the stated target and the current design handles it with room to spare. The correct move at the target scale is *measurement*, not features. |
| **~2,500+** | **MCP server**, if ≥3 tools support it natively AND trust-filter misuse has been observed ≥10 times | §6. Fires on observed trust failures, not on document count alone. |
| **~3,000 / 600 topics** | Reconsider **embeddings**: int8-quantized, 384d, whole-doc (~1.31 MB), local model vendored in-repo | §5. Tier 1 router passes ~50 KB / 13k tokens at ~600 topics and stops being a cheap fetch. Requires ≥20 logged retrieval misses aliases could not fix. |
| **~10,000** | Committed SQLite FTS5 index (Python `sqlite3` module builds it; note there is **no `sqlite3` CLI** on this machine, and it is useless to HTTPS-only agents) | Only at a scale where scanning 200+ shards is genuinely slow. Explicitly out of scope now. |
| **Never** | lunr.js | 12.8 MB at 1,000 documents. Measured, disqualified. |

---

## 11. Summary of concrete recommendations

1. Ship `llms.txt` as a **directed entry point with trust rules and URL templates** above the
   first H2. Do not ship `llms-full.txt` — measured at 12.9 MB / 3.2M tokens, it is
   impossible.
2. Generate a **three-tier catalog**. Never a flat one: measured 1.08 MB / 270k tokens.
3. **Flatten frontmatter keys.** Nested `review.status` returns **0 results** from
   `rg '^status: verified'` with no error — the single most dangerous failure mode found.
4. Put the **topic slug in both the directory name and the filename**. The redundancy buys a
   free `-g` prefilter.
5. **`expires_on` is a precomputed absolute date; `is_stale` is computed by the caller.**
   Never bake a freshness boolean without a `generated_at` beside it.
6. **Pagefind for humans, not agents** — verified not to load headlessly in Node.
7. **No embeddings** (revisit at ~3,000 docs / 600 topics + 20 logged misses). The consuming
   agent's own weights do the semantic matching over a 17 KB topic list, for free.
8. **No MCP yet** (revisit at ~2,500 docs, or on 10 observed trust-filter failures).
9. **No chunking.** Median document is 3,219 tokens; chunking would sever documents from the
   provenance that is the entire point.

---

## Appendix: reproducing these measurements

The corpus generator, catalog builders, index builders and benchmark scripts used for this
position are throwaway and were not committed. To reproduce: generate 1,000 markdown files
across 200 topic directories with 700–2,600-word bodies and the frontmatter schema in §2,
then build (a) a flat catalog, (b) tiered catalogs, (c) MiniSearch and lunr indexes over
full bodies, (d) a Pagefind index over generated HTML, and measure serialized byte sizes and
`rg` wall-clock times. All figures in this document are from that run on
Python 3.12.3 / Node 22.23.2 / ripgrep 14.1.0 / Pagefind 1.5.2.

**Sources for `llms.txt` adoption claims:**
- [llms.txt in Practice: Adoption Data, Evidence, and Setup](https://www.digitalapplied.com/blog/llms-txt-in-practice-adoption-evidence-2026)
- [LLMS.txt Adoption: 8.7% of the Top 1,000 (June 2026)](https://www.rankability.com/data/llms-txt-adoption/)
- [State of llms.txt 2026: Adoption, Standards, and Practice](https://presenc.ai/research/state-of-llms-txt-2026)
- [Meet llms.txt, a proposed standard for AI website content crawling](https://searchengineland.com/llms-txt-proposed-standard-453676)
- [llms.txt Explained (May 2026): The Honest Guide to the Spec, Adoption, and How to Ship One](https://codersera.com/blog/llms-txt-complete-guide-2026/)
