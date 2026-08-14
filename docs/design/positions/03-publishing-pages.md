# Position: Publishing & GitHub Pages

**Role:** Static Site / GitHub Pages Engineer
**Scope:** how this repo becomes a live site without becoming a maintenance liability
**Scale assumption:** 1,000 documents / 200 unrelated topics / 6 AI tools that never talk to each other
**Date:** 2026-08-14

Everything numeric below was measured on this machine against a synthetic 1,000-document
corpus, not recalled. Commands and outputs are cited inline. Where I am inferring rather
than measuring, I say so.

---

## 0. TL;DR

| Question | Answer |
| --- | --- |
| Pages build mode | **GitHub Actions artifact deploy** (`actions/deploy-pages`). Not Jekyll, not branch-serve. |
| Where output lives | **Nowhere in git.** Built in CI, uploaded as a Pages artifact, `_site/` is gitignored. |
| Committed HTML at 1,000 docs | **No.** Measured: a one-word edit to one document rewrites 133 of 134 search-index chunks. Committing generated output puts ~4 MB of undeltafiable binary churn into history *per content commit*, and creates merge conflicts that no AI agent can resolve. |
| Source → published URL rule | Strip `kb/`, keep the path, swap/append the extension. `kb/<P>.md` → `/<P>.html` and `/<P>.md`. One variable, invertible. |
| SSG vs hand-rolled | **Hand-rolled.** The distinguishing feature (provenance injection + catalog) is custom code in *every* option; an SSG adds its own conventions and upgrade cadence on top of work you still have to do. |
| Renderer | **`mistune`** (pure Python, zero dependencies, single 67 KB wheel, **vendored into the repo**) — *conditional on diagrams rendering client-side*. If diagrams must render at build time via mermaid-cli, switch to Node + `markdown-it` and vendor the lockfile. |
| CSS | Hand-written, one file, **≤ 6 KB uncompressed**. No framework. `prefers-color-scheme` + one breakpoint. |
| Search | `catalog.json` browse/filter from day one (~60 KB gzip). **Pagefind later** (measured: viable). **lunr.js: reject** — measured 18.2 MB index, 2.4 MB gzipped, downloaded in full before the first keystroke. |
| Custom domain | Leave a hook (`build/site/CNAME` copied if present), create nothing, one line in the README. |

---

## 1. Pages build mode

There are exactly three modes. Two of them are wrong for this repo, and it is worth
saying precisely *why*, because the wrong ones are the defaults.

### 1a. Built-in Jekyll (the default when Pages serves a branch)

**Reject. It violates a hard requirement and actively corrupts our content.**

- Jekyll *is* a markdown→HTML generator, so at first glance it satisfies "no agent
  hand-writes HTML." It does not satisfy the rest: provenance must be injected as meta
  tags/JSON-LD **and** a rendered footer, driven off an arbitrary frontmatter schema with
  a validator. Doing that in Jekyll means Liquid templates plus a `_layouts` tree, and
  GitHub's Pages build only permits a whitelisted plugin set — so the catalog generator,
  the staleness computation, and the schema validation all have to live *outside* Jekyll
  anyway. You end up with two build systems.
- **Liquid eats our content.** Pages-Jekyll runs Liquid over markdown. A knowledge base
  whose explicit content type #3 is "code snippets and runnable examples" *will* contain
  `{{ }}` and `{% %}` — Jinja, Handlebars, Vue, Go templates, GitHub Actions expressions,
  Helm charts. Jekyll will either interpolate them to empty strings or throw a Liquid
  syntax error on a file it should have copied verbatim. This is not hypothetical; it is
  the single most common Pages support complaint.
- **The `_` trap.** Jekyll silently ignores any file or directory whose name starts with
  `_` (and `.`), plus anything matching its `exclude` defaults. A document at
  `kb/_internal/notes.md` is simply not published, with no error. Silent omission at
  1,000 documents is the worst possible failure mode.
- **Build failure semantics are bad.** A Jekyll build failure on Pages sends an email to
  the repo owner and *leaves the previous site live*. There is no red X on the commit for
  a contributor to see, no PR gate, and six tools that never talk to each other will
  never see that email.

`.nojekyll` exists precisely to turn this off, and we will ship one regardless of mode.

### 1b. Plain static branch-serve (`main:/docs` or `main:/` + `.nojekyll`)

Coherent, and I would defend it as strategy **B** below. But note what it costs:

- **There is no build, therefore there is nothing to gate.** Whatever is in the served
  directory is live within seconds of the push. A validator can run as a CI check, but it
  runs *after* the content is already public. Branch protection can block a *merge*, which
  does nothing about a direct push to `main` — and direct pushes to `main` are exactly
  what six independent AI tools will do.
- It forces the build to run on the contributor's machine, which means every contributing
  tool needs Python, the vendored renderer, and the discipline to run `build.py` before
  pushing. One tool that forgets ships stale HTML next to fresh markdown — and the whole
  point of generating HTML was that the pair *cannot* drift.
- It puts generated output in git. See §2.

### 1c. GitHub Actions artifact deploy — **RECOMMENDED**

`actions/configure-pages` → build → `actions/upload-pages-artifact` → `actions/deploy-pages`.

**Build failure semantics (the deciding factor).** The validator is a job. If it fails:

- the workflow goes red on the commit and on the PR,
- `deploy-pages` is `needs:`-gated behind it and **never runs**,
- **the previously deployed site stays live, unchanged.**

That is precisely the behaviour the brief asks for ("a failing validation blocking the
deploy"), and it is the only mode that provides it. A bad document breaks CI; it does not
break the site.

**Permissions / `GITHUB_TOKEN` scopes.** Set `permissions: contents: read` at the workflow
level, then widen *only* on the deploy job:

```yaml
permissions:
  contents: read      # checkout
  pages: write        # create the Pages deployment
  id-token: write     # OIDC token deploy-pages exchanges with the Pages service
```

`id-token: write` is the one people trip over — `deploy-pages` uses OIDC, not the classic
token, so omitting it produces an opaque failure. It is also the one an org policy is most
likely to restrict; if this repo ever moves under an org that disallows `id-token: write`,
this whole mode is unavailable and we fall back to strategy C.

Note the deploy job must also declare `environment: name: github-pages`, and
`concurrency: { group: pages, cancel-in-progress: false }` so that six tools pushing in the
same minute produce a queue of deploys rather than a race. I specifically want
`cancel-in-progress: false`: cancelling an in-flight *deploy* (as opposed to a build) is
how you get a half-published site.

**The manual step the user must do by hand, exactly once:**

> **Settings → Pages → Build and deployment → Source → change from "Deploy from a branch" to "GitHub Actions".**

Until that dropdown is changed, `deploy-pages` fails with a "Get Pages site failed" /
HTTP 404 that reads like a permissions bug and is not one. `actions/configure-pages`
accepts `enablement: true` to create the Pages site over the API, but it needs a token with
repo-admin scope and it is inconsistent in practice — do not rely on it. Do the dropdown.
Also expect the very first deployment of a brand-new Pages site to take a few minutes
longer than subsequent ones while the certificate is provisioned.

**Actions cost:** public repository ⇒ Actions minutes are free and unmetered today. The
build measured below is seconds; the whole workflow will be ~40–70 s wall clock, dominated
by checkout and artifact upload, not by rendering.

### What would change my mind

I would switch off Actions-artifact deploy if any of these became true:

1. **The user wants per-PR preview deploys.** Pages gives you exactly one deployment per
   repo. There is no built-in preview environment. Today the workaround is
   `actions/upload-artifact` on the built `_site/` and downloading a zip — which is bad
   enough that if previews matter, the honest answer is "use a different host," and that
   is out of scope here.
2. **Actions is disabled** for the repo or restricted by org policy (particularly
   `id-token: write`). Then strategy C (workflow force-pushes to `gh-pages`) or B.
3. **The user's hard requirement becomes "the rendered site must be obtainable by
   `git clone`"** — e.g. for offline/air-gapped reading. Then strategy C.
4. **The corpus grows past ~10,000 documents**, where the tar + upload + unpack of the
   artifact starts to dominate and full-rebuild-per-push stops being free. Pages also has a
   1 GB published-site soft limit and 100 GB/month bandwidth soft limit; at 1,000 docs we
   measured ~12 MB of HTML, so we are three orders of magnitude clear. This is a 2029
   problem, noted and deliberately not designed for.

---

## 2. Where the output lives, and the committed-HTML question

**Recommendation: generated output is never committed.** Build to `_site/`, gitignore it,
upload it as a Pages artifact.

This is the item most likely to be argued, so here is the measurement rather than an
opinion.

### The experiment

I generated 1,000 documents (~8 KB each, 24 headings, realistic 73,000-word vocabulary
spread across 200 topic bands), rendered them to HTML, and built a Pagefind index. Then I
changed **one word in one document** and rebuilt.

```
$ node gen.mjs
render+write 1000 docs: 2880 ms; total html bytes: 10.8 MB

$ npx pagefind --site out2 --output-path out2/pagefind
  Indexed 1000 pages / 73000 words ... Finished in 5.550 seconds
  index:     134 chunks, 3723 KB total, avg 27 KB
  fragment:  1000 files, 4998 KB total, avg 4 KB

# edit ONE word in ONE of the 1000 documents, rebuild:
index chunks before/after: 134 / 134
unchanged chunk filenames: 1
changed/new:              133
```

A control run with **no** change reproduced all 134 filenames byte-identically, so the
build is deterministic — the churn is genuinely content-driven. Pagefind sards its index by
term, and shifting one document's term postings rehashes essentially every shard.

### What that means in git

If the built site is committed:

- Each content commit adds ~4 MB of **new** `.pf_index` blobs. These are already-compressed
  binary; git's delta compression gets close to nothing on them. Add the regenerated
  `catalog.json`, `sitemap.xml`, every tag/index page the document appears on, and the page
  itself.
- At a modest 300 content commits a year — six AI tools, 1,000 documents, that is *low* —
  that is over 1 GB of git objects per year, in a repo whose actual source material is
  ~8 MB. `git clone` becomes a minutes-long operation for agents that want to grep the
  corpus, which is one of our two primary access paths.
- `git log --follow kb/messaging/kafka.md` is fine, but `git log` and any diff review is
  drowned. Provenance is the whole point of this repo, and the human-readable history of
  *who changed what* is provenance.
- **The killer, specific to this brief:** two AI tools that never talk to each other push
  two unrelated documents within the same hour. Both regenerated `catalog.json`, both
  regenerated `sitemap.xml`, both regenerated 133 index chunks. That is a merge conflict in
  generated binary and generated JSON, and *no AI agent will resolve it correctly* — it
  will pick a side and silently drop the other tool's document from the catalog. Generated
  files in a multi-writer repo are a correctness bug, not a tidiness complaint.

### The honest case *for* committing output

I want to state it fairly, because it is not stupid:

- The site becomes reproducible without CI. Pull the repo, open `docs/index.html`, read it.
- It survives GitHub Actions being unavailable or policy-restricted.
- "Degrade gracefully if the build script vanishes" is a stated working principle, and
  committed HTML is one reading of that.

I reject the third argument specifically: **the graceful-degradation story is the markdown,
not the HTML.** If `build.py` disappears, `kb/**.md` is still readable in a text editor,
still renders on github.com, still greppable, still fetchable over `raw.githubusercontent`.
The HTML adds nothing to that story — it is a *derivative*, and a stale derivative is worse
than no derivative because a reader cannot tell it is stale.

The first two arguments are real, and they are why strategy **C** exists below: force-push
the built site to an orphan `gh-pages` branch. You get a git-addressable rendered site
without putting a single generated byte into `main`'s history.

### Middle option, named and rejected

"Commit the HTML but not the search index." This removes the 4 MB/commit binary churn and
is genuinely much better than committing everything. It still leaves `catalog.json` and the
index pages as multi-writer merge conflicts, and it still requires every contributing tool
to run the build. Half the cost for a third of the benefit. If someone insists on committed
output, this is the version to insist on — but prefer C.

### `docs/` is already taken

Note a live collision: this repository is already using `/docs` for **design and goal
documents** (`docs/goals/`, `docs/design/positions/` — including this file). Pages' branch-
serve mode can only serve `/` or `/docs`. Using `/docs` as the build output would mean
publishing the design meta-docs as the site, or moving them. **Content goes in `kb/`,
output goes in `_site/` (gitignored), and `docs/` stays what it already is.** This is a
small point that will cause a large mess if it is decided late.

---

## 3. Raw markdown fetchability

### The exact URL shape

```
https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/<repo-relative-path>
```

e.g. `https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/kb/messaging/kafka-partition-rebalancing.md`

Measured response headers (verified against a live public repo on this machine):

```
HTTP/2 200
cache-control: max-age=300
etag: "f31342d556cea9c5785f1e4b48d9954cbc68ef21914dc817dbb009cb63b9ee4d"
content-type: text/plain; charset=utf-8
content-security-policy: default-src 'none'; style-src 'unsafe-inline'; sandbox
access-control-allow-origin: *
x-content-type-options: nosniff
vary: Authorization, Accept-Encoding
```

Four consequences worth writing down:

1. **`access-control-allow-origin: *`** — browser JavaScript on our Pages site *can* fetch
   raw markdown cross-origin. That is a free capability (e.g. a "view source" toggle) and
   we should not waste effort proxying it.
2. **`content-type: text/plain` + `sandbox` CSP** — GitHub will never render our markdown as
   HTML from that origin. Safe, and it means agents get bytes, not a rendered DOM.
3. **`cache-control: max-age=300` on branch refs — and, measured, also on commit-SHA
   pinned URLs.** SHA-pinned raw URLs do *not* get immutable caching, which surprises
   people. The ETag is a content hash, so conditional `If-None-Match` requests are cheap and
   agents should use them.
4. `vary: Authorization` — an authenticated request and an anonymous one are cached
   separately.

**Rate limits.** `raw.githubusercontent.com` is a Fastly-fronted static endpoint, not the
REST API, and GitHub does not publish a number for it. Empirically it is abuse-throttled in
the low thousands of requests/hour per IP, returning 429. That matters at our scale:

> **An agent that wants the whole corpus must not make 1,000 raw requests.** It should
> `git clone --depth 1 https://github.com/clostaunau/UseFullknowledge.git` (~8 MB of
> markdown) or pull the tarball from
> `https://codeload.github.com/clostaunau/UseFullknowledge/tar.gz/refs/heads/main`.
> Raw fetches are for *targeted* retrieval of a handful of documents after consulting
> `catalog.json`. This belongs in `AGENTS.md` as an explicit instruction — left unsaid, a
> naive agent will loop over the catalog and get itself 429'd.

### The path derivation rule

**Proposal — one variable, `<P>`, and pure string operations:**

| Thing | URL / path |
| --- | --- |
| source | `kb/<P>.md` |
| raw markdown | `https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/kb/<P>.md` |
| rendered page | `https://clostaunau.github.io/UseFullknowledge/<P>.html` |
| markdown on the site | `https://clostaunau.github.io/UseFullknowledge/<P>.md` |
| github.com view | `https://github.com/clostaunau/UseFullknowledge/blob/main/kb/<P>.md` |

```python
RAW  = "https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main"
SITE = "https://clostaunau.github.io/UseFullknowledge"

def urls(source_path):                       # "kb/messaging/kafka.md"
    P = source_path.removeprefix("kb/").removesuffix(".md")
    return {"raw": f"{RAW}/{source_path}",
            "html": f"{SITE}/{P}.html",
            "md":   f"{SITE}/{P}.md"}

def source_of(site_url):                     # exact inverse
    P = site_url.removeprefix(SITE + "/").removesuffix(".html").removesuffix(".md")
    return f"kb/{P}.md"
```

Three properties I care about:

- **It is invertible.** Given any one of the four URLs, the other three are derivable with
  no lookup table. An agent that lands on an HTML page from a search engine can construct
  the markdown URL without fetching anything.
- **The output tree is the source tree.** `_site/` mirrors `kb/` exactly, with the `.md`
  copied verbatim and a `.html` added beside it. Nothing is nested, flattened, renamed, or
  slugified during the build. That means the build script has no path-mapping logic to get
  wrong, and the validator can assert the invariant in one line.
- **Inter-document links become a suffix swap.** A markdown link `../messaging/kafka.md`
  becomes `../messaging/kafka.html` — `s/\.md$/\.html/`, always correct, no path
  arithmetic. Compare the pretty-URL alternative (`<P>/index.html` served at `/<P>/`),
  where the same link must become `../../messaging/kafka/` because the page moved down a
  directory level. AI agents will write relative markdown links; the suffix-swap rule is the
  one they cannot get wrong.

**Belt and braces.** The rule exists so the mapping is *guessable*, but no consumer should
be forced to guess. Every generated page carries:

```html
<link rel="canonical"  href="https://clostaunau.github.io/UseFullknowledge/<P>.html">
<link rel="alternate"  type="text/markdown" href="https://clostaunau.github.io/UseFullknowledge/<P>.md">
<meta name="kb:source" content="kb/<P>.md">
<meta name="kb:raw"    content="https://raw.githubusercontent.com/clostaunau/UseFullknowledge/main/kb/<P>.md">
```

and the visible provenance footer carries three human links: **View markdown · View on
GitHub · History**. (The `kb:` meta names are placeholders — the metadata specialist owns
the actual field vocabulary. The two `<link rel>` elements are publishing's responsibility
and I am asserting them.)

**Why copy the `.md` into the site at all**, given `raw.githubusercontent` already satisfies
the hard requirement? Three cheap wins: it is same-origin with the HTML (no CORS
consideration for any future client-side feature), it is served by the Pages CDN at
`max-age=600` rather than raw's 300 with different and more generous throttling, and it
makes the mirror invariant testable — if `_site/<P>.md` is missing, the build is broken. The
cost is one `shutil.copy` and ~8 MB in the artifact.

---

## 4. Path and casing gotchas

These are the things that break links at 1,000 documents. Every one gets a validator rule,
because a convention that is not checked is a convention that is not followed — especially
by six tools that never read each other's output.

**1. Case sensitivity is the number one link killer.** The Pages server is case-sensitive.
macOS (APFS default) and Windows are case-*insensitive*. `kb/Messaging/Kafka.md` linked as
`kb/messaging/kafka.md` works perfectly on the contributor's laptop, passes their local
build, and 404s in production. Worse, `git config core.ignorecase` is `true` by default on
those platforms, so a rename that only changes case may not even be recorded.

> **Rule: every path segment under `kb/` must match `^[a-z0-9]+(-[a-z0-9]+)*$`.**
> Lowercase, digits, single hyphens. No uppercase, no underscores, no spaces, no `%20`, no
> `+`, no dots except the final extension, no non-ASCII. Enforced by the validator against
> `git ls-files`, not against the working tree, so case-only renames are caught.

Five lines of validator for the highest-value durability guarantee in the whole design.

**2. The `_` prefix trap.** Even though `actions/deploy-pages` does not run Jekyll, forbid
leading `_` and `.` on any `kb/` path segment. The cost is zero and it keeps the door open
to strategy B/C without a silent content-disappearance bug. Covered by the regex above.

**3. `.nojekyll`.** Ship one at the root of `_site/` unconditionally. With artifact deploy
it is inert. If anyone ever flips Pages back to branch-serve, its absence would silently
drop `_`-prefixed paths and run Liquid over our code samples. It is an empty file. Ship it.

**4. Trailing slashes and pretty URLs.** We are emitting `<P>.html`, so there is exactly one
canonical form and no trailing-slash ambiguity. GitHub Pages will generally also serve
`/<P>` for a `<P>.html` file, but **do not link that way** — emit the explicit `.html`
everywhere and set `<link rel="canonical">` to it, so search engines and agents converge on
one string. Mixed conventions across 1,000 pages contributed by six tools is how you get
duplicate indexing and broken relative links.

**5. Base path.** This is a *project* Pages site, so the site root is
`/UseFullknowledge/`, not `/`. Absolute root-relative links like `/assets/site.css` will
404. Two rules: inter-document links are **relative** (they work in the built site, in a
local `python -m http.server`, and would keep working under a custom domain), and site
chrome (CSS, `catalog.json`, search) is emitted through a single `BASE` constant sourced
from `actions/configure-pages`' `base_path` output. Never hardcode the absolute origin
anywhere except canonical/JSON-LD, and build those from `BASE` too.

**6. 404 handling.** Pages serves `/404.html` from the site root for any unmatched path,
with a real HTTP 404 status. Generate one, and make it earn its place: link to the catalog,
the search page, and the repo. At 1,000 documents with 6 uncoordinated contributors, people
*will* hit stale links.

**7. Renames are the scale failure.** Moving `kb/data/kafka.md` → `kb/messaging/kafka.md`
breaks every inbound link, every external bookmark, and every citation another document
made. Static hosting has no redirect engine. The static-safe fix:

> Support an `aliases:` list in frontmatter. For each alias, the build emits a stub at the
> old path containing `<meta http-equiv="refresh" content="0; url=...">` plus
> `<link rel="canonical">` plus a visible "this page moved" line. ~15 lines of build script,
> degrades gracefully (the stub is readable HTML even with JS off), and costs nothing until
> the first rename.

If the information architect settles on stable opaque IDs, the same mechanism generates
`/id/<id>.html` redirect stubs from frontmatter — permanent addresses that survive any
reshelving. I am not asserting that ID scheme; I am asserting that *whatever* it is, the
publishing layer can honour it with redirect stubs and needs no server.

**8. Anchor slugs.** Heading anchors must be generated deterministically and lowercased
(`## Kafka Partition Rebalancing` → `#kafka-partition-rebalancing`). GitHub's own markdown
renderer uses a specific slug algorithm; match it, so a `#anchor` link written against the
github.com view also works on the published page. Otherwise deep links work in exactly one
of the two places a reader might be.

---

## 5. Static-site generator vs. hand-rolled build script

Honest evaluation, weighted by the criteria in the charge: dependency count, three-year
rot under neglect, build time at 1,000 pages, and the hard constraint that HTML must carry
injected provenance in two forms.

| Option | Deps (transitive) | 3-year rot risk | Build @1,000 | Provenance injection |
| --- | --- | --- | --- | --- |
| **Hand-rolled Python** | 3 (pyyaml, jsonschema, mistune) | **Very low** — all pure Python, vendorable | ~3–20 s (measured) | Trivial; it's your template |
| Hand-rolled Node | 1–7 (marked or markdown-it) | Low–medium; Node major churn, ESM/CJS | ~3 s (measured) | Trivial |
| Eleventy | ~90–200 | **Medium-high** — roughly annual majors, ESM migration in v3 | fast | Easy (data cascade + layouts) |
| Astro / Starlight | 400–700+, Vite toolchain | **High** — fastest-moving option here | fast | Medium (component overrides) |
| Docusaurus | ~1,000, React | **High** | slow-ish | Medium |
| MkDocs + Material | ~30 (pip, not installed) | Medium — Material ships very frequently | fast | **Requires a custom theme override anyway** |
| Hugo | 0 (single static binary) | **Lowest**, but not installed; must fetch+checksum a binary in CI | very fast | Painful — Go templates for arbitrary JSON-LD |

**Verdict: hand-rolled, in Python.**

The reasoning is not "frameworks bad." It is specific to this repo:

**The custom part is the whole product.** Frontmatter schema validation, staleness
computation, the two-form provenance injection, `catalog.json`, `llms.txt`, the trust-filter
query surface — none of that comes free from any generator on the list. You write it in all
seven columns. What an SSG donates is the *generic* part: layouts, nav, pagination,
sitemap, RSS. In this design that generic part is maybe 150 lines, because the site
structure is deliberately flat and mirrors the source tree. Paying 200–700 transitive
dependencies and an upgrade cadence to save 150 lines, while still writing all the custom
logic *inside that framework's conventions*, is a bad trade.

**The rot argument is the decisive one, and it is asymmetric.** Consider the repo untouched
for two years and then someone pushes a document. Hand-rolled Python + a vendored wheel:
`python build.py` runs, because pure-Python packages and the stdlib do not break across
minor versions. Astro: `npm ci` against a two-year-old lockfile pulls deprecated transitive
packages, the Vite major has moved twice, Node 22 is out of support in CI, and fixing it is
an afternoon — an afternoon nobody will spend, so the site stays stale. That is precisely
the "elegant system nobody maintains" failure the working agreement warns about.

Hugo deserves an honourable mention: a single static binary, checksum-pinned in the
workflow, is genuinely the most rot-proof option on the list, and I would not fight hard
against it. It loses on the provenance requirement specifically — building a JSON-LD blob
and a conditional footer out of arbitrary, per-content-type frontmatter in Go templates is
genuinely unpleasant, and Hugo's own major versions have broken sites (the 0.146 template
reorganisation). If the team already knew Hugo well, I would reconsider.

### The honest downside of hand-rolled

- **"~300 lines" is a lie people tell.** With templates, TOC generation, anchor slugs,
  relative-link rewriting, redirect stubs, `catalog.json`, `sitemap.xml`, `404.html`, and
  the edge cases you find on document #600, it will be **600–900 lines** plus templates. Do
  not budget 300.
- **No community, no plugins, no Stack Overflow.** Every bug is yours. Syntax highlighting,
  footnotes, admonitions, RSS, incremental builds — each is a small project.
- **It will look worse than Starlight.** Starlight ships a genuinely good docs UI. Our site
  will look like a clean, fast, readable, plain document site. If "looks like a polished
  product" is a real requirement, hand-rolled loses and I would swap to Eleventy (not
  Astro — Eleventy has the best rot/capability ratio of the JS options).
- **No incremental build.** Every push rebuilds all 1,000 pages. At the measured 3–20 s that
  is irrelevant; at 10,000 pages it is a minute and someone will want caching.

---

## 6. Markdown → HTML with no pandoc, no python-markdown

Verified on this machine — everything below was actually installed and run, not assumed.

| Renderer | Install footprint | Deps | 1,000 docs | Notes |
| --- | --- | --- | --- | --- |
| **mistune 3.3.4** (pip) | **one 67 KB wheel** | **zero** | 20.0 s (with table/strikethrough/footnote plugins) | Pure Python. Vendorable as a wheel or as source. |
| markdown-it-py 4.2.0 (pip) | 2 wheels | 1 (mdurl) | **3.1 s** | Pure Python, CommonMark-strict, plugin ecosystem |
| markdown-it 15 (npm) | 2.0 MB | 6 | **2.9 s** | `html:false` default, mature plugin set |
| marked 18 (npm) | 492 KB | **zero** | ~3 s | Oldest, most stable API; HTML-permissive |

```
$ python3 -m pip download mistune -d ./pipdl
  Saved ./pipdl/mistune-3.3.4-py3-none-any.whl        # 66.9 kB, no other downloads

$ node gen.mjs
  render+write 1000 docs: 2880 ms

$ ./.venv/bin/python bench.py
  mistune 1000 docs: 20.00s, 10.5 MB html
  markdown-it-py 1000 docs: 3.10s
```

**Build time is a non-issue.** Everything is in the seconds. Choose on rot, not speed.

**Recommendation: `mistune`, vendored — conditional.**

- Pure Python, **zero dependencies**, one 67 KB wheel. It can be committed to
  `build/vendor/` and installed offline with
  `pip install --no-index --find-links build/vendor mistune`. That single move makes the
  build reproducible in 2029 regardless of what happened to PyPI resolution, yanked
  versions, or `pip`'s resolver. It costs 67 KB.
- It keeps the build **single-runtime**: pyyaml and jsonschema (already installed, already
  the validator's tools) plus mistune, and nothing else. A two-runtime build (Python
  validator + Node renderer) is two dependency trees, two setup steps in CI, and two things
  to break.
- Python 3.12 → 3.20 is a materially gentler slope than Node 22 → Node 30 for a pure-Python
  package with no C extensions.

**The condition.** If the diagram specialist concludes that C4/Mermaid diagrams must be
rendered to SVG **at build time** via `mermaid-cli`, then Node is already a mandatory build
dependency and the "single runtime" argument inverts. In that case: **Node + markdown-it**,
with a committed `package-lock.json` and `npm ci` (or `node_modules` vendored outright —
measured at 3.4 MB for markdown-it + marked together, which is small enough to commit). If
Mermaid renders **client-side** from one vendored `mermaid.min.js`, Python wins. I am
flagging this as a cross-cutting decision, not deciding it unilaterally.

**Rejected: hand-writing a markdown parser.** CommonMark is a 60-page spec with brutal edge
cases in nested emphasis, link reference definitions, and HTML blocks. A hand-rolled
regex renderer will mangle real documents and you will not notice until document #400.
Not a place to save a dependency.

**Also rejected: `commonmark` (pip).** Effectively unmaintained; markdown-it-py is its
successor.

---

## 7. Mobile and theme-aware CSS

**Hand-written, one file, target ≤ 6 KB uncompressed (~2 KB gzipped). No framework.**

No Tailwind (build step + purge step + config churn + a major version every ~18 months), no
Bootstrap, no Pico. A document site needs typography, a measure, a code block, a table, and
a footer. That is not a framework's worth of problem.

Contents:

- **Palette as custom properties on bare `:root`** — the complete light palette. Redefine
  *only* the tokens under `@media (prefers-color-scheme: dark)`, and again under
  `:root[data-theme="dark"]` if a manual toggle is ever added. Never let a colour's only
  definition live inside a media query. `body` gets an explicit token background.
- **System font stack** — `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. Zero
  network requests, zero layout shift, native on every phone. Web fonts would be the single
  largest asset on the site; they are not worth it.
- **Measure and rhythm** — `max-width: 72ch`, `line-height: 1.6`, `font-size: 1.05rem`.
- **One breakpoint at `48rem`** for the sidebar/TOC. Below it, the TOC collapses to a
  `<details>` element — no JavaScript.
- **`overflow-x: auto` wrappers** on `table`, `pre`, and rendered diagram SVG. This is the
  single most common mobile bug on documentation sites: a wide code block or a C4 diagram
  makes the whole *page* scroll sideways. Wrap them, always.
- **The provenance footer** gets a `.provenance` block with a status chip coloured by review
  state (`unreviewed` / `reviewed` / `verified`) and a visible staleness warning when the
  review-by date has passed. This is the search-engine-landing requirement, and it is
  ~25 lines of CSS. It must be legible in both themes and must not rely on colour alone —
  the chip carries text.
- **Print styles**: 6 lines. Hide nav, black on white, show link targets.

**One external stylesheet, not inlined.** Across 1,000 pages a single cached `site.css`
beats inlining 6 KB into every page.

**No JavaScript on a document page.** Zero. A rendered explainer should be HTML and CSS. JS
appears on exactly two surfaces: the search/browse page, and the Mermaid renderer *if*
diagrams are client-side.

**Deliberate YAGNI: no syntax highlighting in v1.** highlight.js and Shiki are the two
obvious options and both are heavy (highlight.js ships ~200 languages and ~250 themes;
Shiki pulls a large grammar bundle). A monospace block with a subtle background, a border,
and correct `overflow-x` is genuinely fine and readable on a phone. If highlighting is later
judged worth it, do it **at build time** with an explicit language allowlist (~10 languages)
so no runtime JS is added — that keeps the "no JS on document pages" property intact.

---

## 8. Client-side search

Three tiers, with measured numbers.

### Tier 1 — `catalog.json` browse/filter. **Do this from day one.**

The catalog has to exist anyway: it is the agent entry point and the trust-filter surface
("only `verified`, non-stale documents about X"). One record per document — path, title,
type, topic, tags, review status, dates, confidence, one-line summary — is roughly 250
bytes, so **~250 KB raw / ~60 KB gzipped at 1,000 documents**. A browse page that fetches it
and filters by title/tag/topic/status is ~60 lines of vanilla JS with no dependency.

That covers the dominant human query ("what do we have about Kafka?") and the entire agent
query surface, for free, because we were building the catalog regardless.

### Tier 2 — Pagefind. **Add when full-text is actually missed. Measured: viable.**

```
Indexed 1000 pages / 73000 words in 5.55 s
index:     134 chunks, 3.7 MB total, avg 27 KB per chunk   ← loaded on demand, per query
fragment:  1000 files, 5.0 MB total, avg  4 KB per page    ← loaded only for shown results
runtime:   pagefind.js 48 KB (+ optional UI 120 KB)
```

The number that matters is **what a phone downloads for one search**: ~48 KB runtime +
~30 KB entry metadata + one or two ~27 KB index chunks + ~5 KB per displayed result ≈
**150–200 KB**. That is acceptable on mobile. My 73,000-word vocabulary was a deliberate
worst case (synthetic unique tokens); real English prose across 200 topics will be
meaningfully smaller.

Two important properties:

- **Pagefind runs over the built HTML as a post-processing step.** It needs *zero* changes
  to the build script — it is six lines added to the workflow between build and upload.
  That is exactly what makes deferring it correct rather than lazy: adding it later is
  cheap, so YAGNI applies cleanly.
- **Its output must never be committed** (see §2: 133/134 chunks churn on a one-word edit).
  This is a hard coupling: *Pagefind and committed-output strategies are incompatible.* If
  the panel picks strategy B, full-text search gets materially worse.

At 100 documents Pagefind is not worth it — the catalog filter covers you. At 1,000 it is.
At 10,000 it is mandatory.

### Tier 3 — lunr.js. **Reject, with evidence.**

```
$ node lunrbench.mjs
lunr build 8516 ms; index JSON 18.2 MB; gzipped 2.4 MB
```

lunr builds one monolithic index that the browser must **download in full and parse into
memory before the first keystroke**. 2.4 MB gzipped on a phone, to search a document site,
is disqualifying. lunr is the right tool at ~200 documents; at 1,000 it falls off a cliff.
This is the sharpest measured result in this document and it should settle the question.

---

## 9. Custom domain

Not requested. **Leave the hook, create nothing, move on.**

Concretely: the build copies `build/site/CNAME` into `_site/` **if that file exists**. Three
lines of build script and one sentence in the README. Do not create the file.

Two gotchas worth recording now, because they cost an afternoon when discovered later:

1. With Actions artifact deploy, **the `CNAME` file must be inside the artifact**. Setting a
   custom domain in the Pages settings UI writes `CNAME` to the served branch — which does
   not exist in this mode — so the next deploy silently drops the domain and the site starts
   404ing on the custom hostname.
2. Moving to a custom apex domain changes the base path from `/UseFullknowledge/` to `/`,
   which rewrites every absolute URL on the site. This is already handled by §4 rule 5
   (relative inter-document links, single `BASE` constant for chrome) — which is most of why
   that rule is worth following even though we have no custom domain today.

---

## 10. Recommended repository layout

```
/
├── README.md                       # human entry point → links to catalog + site
├── AGENTS.md                       # contribution contract for the 6 tools
├── llms.txt                        # agent entry point (copied verbatim to site root)
├── .gitignore                      # contains: _site/  .venv/  node_modules/
│
├── kb/                             # ══ SOURCE OF TRUTH. markdown only. ══
│   ├── messaging/
│   │   ├── kafka-partition-rebalancing.md
│   │   └── kafka-partition-rebalancing.mmd      # diagram source beside its doc
│   ├── biology/
│   │   └── crispr-base-editing.md
│   └── ...                                       # 200 topics, path shape owned by the IA
│
├── build/
│   ├── build.py                    # md → html, provenance injection, catalog, sitemap
│   ├── validate.py                 # schema + links + casing + slug uniqueness + orphans
│   ├── requirements.txt            # mistune==3.3.4  pyyaml==6.0.1  jsonschema==...
│   ├── schema/
│   │   ├── common.json             # shared provenance block
│   │   └── explainer.json ...      # one per content type
│   ├── templates/
│   │   ├── page.html               # article + machine metadata + provenance footer
│   │   ├── index.html              # directory / topic listing
│   │   ├── search.html             # catalog.json browse+filter
│   │   └── 404.html
│   ├── site/
│   │   ├── site.css                # ~6 KB, hand-written, theme-aware
│   │   ├── robots.txt
│   │   └── (CNAME)                 # ← optional hook; does not exist today
│   └── vendor/
│       └── mistune-3.3.4-py3-none-any.whl        # 67 KB, offline-installable
│
├── docs/                           # design + goal documents. NOT the site. NOT published.
│   ├── goals/
│   └── design/positions/
│
├── .github/workflows/pages.yml
│
└── _site/                          # ══ BUILD OUTPUT. GITIGNORED. NEVER COMMITTED. ══
    ├── .nojekyll
    ├── index.html
    ├── 404.html
    ├── catalog.json                # ~250 KB / ~60 KB gz
    ├── llms.txt
    ├── sitemap.xml
    ├── robots.txt
    ├── site.css
    ├── search.html
    ├── messaging/
    │   ├── kafka-partition-rebalancing.html      # ← generated
    │   ├── kafka-partition-rebalancing.md        # ← verbatim copy of source
    │   └── kafka-partition-rebalancing.svg       # ← rendered diagram (if build-time)
    └── pagefind/                                 # ← tier 2, added later
```

**The one invariant to hold onto:** `_site/` is `kb/` with the markdown copied through and
an `.html` sibling added. No renaming, no flattening, no nesting. Everything in §3 and §4
falls out of that.

---

## 11. GitHub Actions workflow sketch

```yaml
name: build-and-deploy

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

# Least privilege at the top; widened only on the deploy job.
permissions:
  contents: read

# Serialize deploys. Six tools pushing in the same minute must queue, not race.
# cancel-in-progress MUST be false: cancelling a mid-flight deploy half-publishes.
concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  # ── Gate. Runs on every push AND every PR. Nothing deploys unless this is green. ──
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      # Offline install from the vendored wheels: reproducible in 2029.
      - run: pip install --no-index --find-links build/vendor -r build/requirements.txt
      - name: Validate frontmatter, links, casing, uniqueness
        run: python build/validate.py --strict

  # ── Build + deploy. Only on main. needs: validate ⇒ a red validator never deploys. ──
  deploy:
    needs: validate
    if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write        # create the Pages deployment
      id-token: write     # OIDC — deploy-pages fails opaquely without this
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install --no-index --find-links build/vendor -r build/requirements.txt

      # Exposes base_path (/UseFullknowledge) and base_url. Never hardcode these.
      - id: pages
        uses: actions/configure-pages@v5

      - name: Build site
        run: |
          python build/build.py \
            --source kb \
            --out _site \
            --base "${{ steps.pages.outputs.base_path }}" \
            --site-url "${{ steps.pages.outputs.base_url }}"

      # ── Tier 2, add later. Six lines, zero build-script changes. ──
      # - name: Build search index
      #   run: npx --yes pagefind@1 --site _site

      - name: Assert publish invariant
        run: python build/validate.py --check-output _site   # every kb/<P>.md has _site/<P>.html and _site/<P>.md

      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site

      - id: deploy
        uses: actions/deploy-pages@v4
```

Notes on the sketch:

- **Action major versions drift.** Confirm the current majors of `configure-pages`,
  `upload-pages-artifact`, and `deploy-pages` when this is actually written; the four
  official actions are versioned independently and this is the most likely line to be stale.
- **Do not add a `paths:` filter to the `push` trigger.** It is tempting ("only rebuild when
  `kb/**` changes") and it is a trap: a change to `build/templates/page.html` or `site.css`
  must also rebuild, and the day someone forgets to add a path the site silently stops
  updating. Full rebuild takes seconds. Rebuild always.
- **`validate.py` runs twice** — once as the gate, once against the output to assert the
  mirror invariant. The second call is the cheap insurance that §3's derivation rule is a
  fact and not a hope.
- The `pull_request` trigger validates but never deploys, so a PR from any tool gets a
  green/red signal without touching production.
- **Prerequisite, once, by hand:** Settings → Pages → Source → **GitHub Actions**.

---

## 12. Three publishing strategies

All three satisfy the hard requirements. They differ in where generated bytes live and what
the site depends on.

### Strategy A — "Artifact Pipeline" ★ **preferred**

Actions builds on every push to `main`. `validate` gates `deploy`. Output goes to an ephemeral
Pages artifact. **No generated byte is ever committed.** `_site/` is gitignored.

- **Wins when:** multiple uncoordinated writers (our case), full-text search is wanted
  (Pagefind's churn is free here), git history must stay legible, `git clone` must stay
  fast for agents.
- **Loses when:** you need per-PR previews, Actions is restricted, or you need the rendered
  site by `git clone`.

### Strategy B — "Committed `docs/`"

Build runs locally; output is committed to a served directory on `main` with `.nojekyll`;
Pages serves the branch. No Actions required to host.

- **Wins when:** you want the site to exist with zero CI dependency, you want to open the
  built HTML straight from a clone, or Actions is unavailable.
- **Loses when:** more than one writer exists. Merge conflicts in generated `catalog.json`
  and index pages; every contributing tool must run the build or the HTML drifts from the
  markdown (defeating the stated reason for generating it); the validator cannot gate a
  direct push, so bad content goes live first and fails CI second. Also collides with this
  repo's existing use of `/docs` for design documents.
- **If chosen:** commit the HTML but **not** the search index, and accept catalog-filter
  search only.

### Strategy C — "gh-pages Orphan Branch"

Actions builds, then force-pushes `_site/` to an orphan `gh-pages` branch as a **single
commit with no history** (`git checkout --orphan` → commit → `push --force`). Pages serves
that branch. `main` never receives a generated byte.

- **Wins when:** you want A's clean history *and* a git-addressable rendered site
  (`git clone -b gh-pages --depth 1` gives you the whole site offline), or when
  `id-token: write` is policy-blocked so `deploy-pages` is unavailable.
- **Loses on:** needing `contents: write` on the workflow (a broader scope than A's), the
  force-push leaving unreferenced objects that GitHub garbage-collects on its own schedule
  rather than immediately, and one more moving part. Search-index churn is neutralised by
  the truncated history, but only as long as nobody ever removes the `--force`.

**Preference: A.** The measured index churn (§2) plus the multi-writer merge-conflict
argument makes committed generated output the wrong default for this specific repo, and A is
the only mode where the validator is a genuine gate. A→C is a ten-line workflow change if
the constraints shift; A→B is a Pages setting plus un-gitignoring the output. Nothing here
is a one-way door.

---

## 13. Downsides of my own preference, stated plainly

1. **No site without Actions.** If Actions is disabled, quota'd, or org-policy-restricted
   (`id-token: write` especially), there is no published site at all — only markdown on
   github.com. I consider this acceptable *because* the graceful-degradation story is the
   markdown, and github.com renders it fine. But it is a real single point of failure and I
   am not going to pretend otherwise.
2. **No PR previews, and no easy local preview of the deployed thing.** You cannot see the
   rendered site by pulling the repo; you must run `python build/build.py && python -m
   http.server -d _site`. For a *reviewer* on github.com the only workaround is downloading
   an artifact zip. If review-of-rendered-output turns out to matter, this is the sharpest
   cost of A.
3. **Full rebuild on every push, and deploys serialize.** Six tools pushing in the same
   minute produce a queue of ~60 s deploys; the last one wins and the site converges, but
   "I pushed and it isn't live yet" will happen. Incremental builds are a real future ask I
   am explicitly not designing for.
4. **Hand-rolled build script means every feature is ours.** No plugin ecosystem. The line
   count will exceed the estimate. The site will look plainer than Starlight. If the user's
   real bar is "looks like a product," I am wrong and Eleventy is the answer.
5. **The Python/Node renderer choice is conditional on someone else's decision** (build-time
   vs client-side Mermaid). I have stated the condition rather than resolving it, which
   means one cross-cutting decision is still open after this position.
6. **`catalog.json`-only search in v1 is a real capability gap.** A human who remembers a
   phrase from a document but not its title cannot find it until Pagefind lands. I think
   that is the correct YAGNI trade because adding Pagefind is six workflow lines — but it is
   a gap, not a non-issue.

---

## 14. Open questions for the panel

- **Diagrams:** build-time (mermaid-cli ⇒ Node in the build) or client-side (one vendored
  `mermaid.min.js`)? This decides §6 and whether the build is single- or dual-runtime.
- **Information architect:** is `kb/<topic-path>/<slug>.md` compatible with the chosen
  shelving scheme? The publishing layer needs the source tree to be directly publishable —
  if the taxonomy demands a document live at several paths, I will serve one canonical path
  plus generated redirect stubs, and I need to know that early.
- **Metadata specialist:** exact `<meta>` names and JSON-LD field vocabulary. I am asserting
  the two `<link rel="canonical">` / `<link rel="alternate" type="text/markdown">` elements
  and the visible footer block as publishing's responsibility; the rest is yours.
- **DX/automation:** `validate.py` is assumed to check frontmatter schema, internal links,
  **path casing/slug regex**, slug uniqueness, and orphans. The casing rule (§4.1) is the one
  I most want owned by the validator and not by documentation.
