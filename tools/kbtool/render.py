"""Markdown -> HTML, with provenance injected in both machine and human form.

HTML is generated, never hand-written, so the rendered page and the markdown
cannot drift. Every page carries the same provenance twice: as JSON-LD plus meta
tags for machines, and as a visible footer for a person who arrived from a
search engine and will otherwise have no way to judge the page.

The published tree mirrors the source tree exactly, so the URL rule is
invertible in both directions:

    kb/explainer/foo-7f3a.md  ->  /kb/explainer/foo-7f3a.html   (rendered)
                              ->  /kb/explainer/foo-7f3a.md     (source)
"""

import html
import json
import pathlib
import re
import shutil

from markdown_it import MarkdownIt

from kbtool.catalog import RAW_BASE, SITE_BASE, build_catalog
from kbtool.frontmatter import ParseError, parse
from kbtool.shelflife import expires_on, is_stale
from kbtool.validate import heading_slug, iter_documents

# The single-file UMD build is vendored rather than the ESM one: the ESM entry
# lazy-loads from a 542-file, 84 MB chunk tree, which is not something to commit
# to a knowledge repo. This is 3.5 MB in git, ~975 KB gzipped over the wire, and
# is loaded only on pages that actually contain a diagram.
MERMAID_JS = "assets/mermaid.min.js"

BASIS_LABELS = {
    "executed-verified": "code was executed and its output checked",
    "primary-source-cited": "cites a primary source",
    "secondary-source-cited": "cites a secondary source",
    "human-expert-review": "reviewed by a human with domain knowledge",
    "cross-model-corroborated": "corroborated across models",
    "synthetic-example": "illustrative example, not drawn from a source",
    "model-recall-only": "model recall only, uncited",
}


MERMAID_MARKER = '<pre class="mermaid">'


def _markdown():
    md = MarkdownIt("commonmark").enable("table").enable("strikethrough")

    default_fence = md.renderer.rules.get("fence")

    def fence(tokens, idx, options, env):
        token = tokens[idx]
        if (token.info or "").strip().lower() == "mermaid":
            # mermaid's startOnLoad scans for elements with class="mermaid".
            # The default <pre><code class="language-mermaid"> is invisible to
            # it, so the diagram would silently ship as a code block.
            return f'{MERMAID_MARKER}{html.escape(token.content)}</pre>\n'
        return default_fence(tokens, idx, options, env)

    md.renderer.rules["fence"] = fence
    return md


def _add_heading_ids(tokens):
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            text = tokens[i + 1].content
            token.attrSet("id", heading_slug(text))


def _rewrite_internal_links(tokens):
    """Point .md links at their rendered .html twin; leave external URLs alone."""
    for token in tokens:
        if token.type == "inline" and token.children:
            for child in token.children:
                if child.type == "link_open":
                    href = child.attrGet("href") or ""
                    if href.startswith(("http://", "https://", "mailto:", "//")):
                        continue
                    path, sep, anchor = href.partition("#")
                    if path.endswith(".md"):
                        child.attrSet("href", path[:-3] + ".html" + sep + anchor)


def render_body(md_text):
    md = _markdown()
    tokens = md.parse(md_text)
    _add_heading_ids(tokens)
    _rewrite_internal_links(tokens)
    return md.renderer.render(tokens, md.options, {})


def _json_ld(data, expiry, url):
    payload = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": data["title"],
        "abstract": data["summary"],
        "url": url,
        "dateCreated": data["created_at"],
        "dateModified": data["updated_at"],
        "keywords": sorted(data.get("tags", [])),
        "creator": {
            "@type": "SoftwareApplication" if data.get("updated_by_kind", "agent") == "agent"
            else "Person",
            "name": data.get("created_by_tool", "unknown"),
            "applicationSuite": data.get("created_by_model", "unknown"),
        },
        "creativeWorkStatus": data.get("review_status", "unreviewed"),
        "expires": expiry,
    }
    if data.get("sources"):
        payload["citation"] = data["sources"]
    if data.get("review_reviewer"):
        payload["reviewedBy"] = {
            "@type": "Person" if data.get("review_reviewer_kind") == "human"
            else "SoftwareApplication",
            "name": data["review_reviewer"],
        }
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    # JSON escaping is not HTML escaping: a literal `</script>` inside a string
    # would close the script element and inject markup into the page.
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _meta_tags(data, expiry):
    fields = {
        "kb:id": data["id"],
        "kb:type": data["type"],
        "kb:review_status": data.get("review_status", "unreviewed"),
        "kb:created_at": data["created_at"],
        "kb:updated_at": data["updated_at"],
        "kb:created_by_tool": data.get("created_by_tool", ""),
        "kb:created_by_model": data.get("created_by_model", ""),
        "kb:confidence_basis": ",".join(sorted(data.get("confidence_basis", []))),
        "kb:volatility": data.get("volatility", ""),
        "kb:expires_on": expiry,
    }
    if data.get("review_reviewer"):
        fields["kb:review_reviewer"] = data["review_reviewer"]
        fields["kb:review_reviewed_at"] = data.get("review_reviewed_at", "")
    return "\n".join(
        f'<meta name="{k}" content="{html.escape(str(v), quote=True)}">'
        for k, v in fields.items()
    )


def _banner(data, stale, expiry):
    status = data.get("review_status", "unreviewed")
    if data["type"] == "note":
        return (
            '<div class="kb-banner kb-banner-raw"><strong>Raw AI output.</strong> '
            "This is an unreviewed research note kept deliberately separate from "
            "curated explanations. Do not cite it as a reviewed explainer.</div>"
        )
    if status == "unreviewed":
        return (
            '<div class="kb-banner kb-banner-warn"><strong>Unreviewed.</strong> '
            "This document has not been reviewed by a human. Treat it as a "
            "starting point, not as a verified reference.</div>"
        )
    if stale:
        return (
            f'<div class="kb-banner kb-banner-warn"><strong>Past its shelf life.</strong> '
            f"This was due for re-review on {html.escape(expiry)}.</div>"
        )
    return ""


def _provenance_footer(data, expiry, stale, md_href):
    esc = lambda value: html.escape(str(value), quote=True)  # noqa: E731
    status = data.get("review_status", "unreviewed")

    rows = [
        ("Created by", f"{esc(data.get('created_by_tool'))} "
                       f"<span class=\"kb-model\">({esc(data.get('created_by_model'))})</span>"),
        ("Created", f"<time datetime=\"{esc(data['created_at'])}\">{esc(data['created_at'])}</time>"),
        ("Last updated", f"<time datetime=\"{esc(data['updated_at'])}\">{esc(data['updated_at'])}</time>"
                         f" by {esc(data.get('updated_by_kind', 'agent'))}"),
        ("Review status", f'<span class="kb-status kb-status-{esc(status)}">{esc(status)}</span>'),
    ]
    if data.get("review_reviewer"):
        rows.append((
            "Reviewed by",
            f"{esc(data['review_reviewer'])} "
            f"({esc(data.get('review_reviewer_kind', 'human'))}) on "
            f"{esc(data.get('review_reviewed_at', ''))}",
        ))
    basis = ", ".join(BASIS_LABELS.get(b, b) for b in sorted(data.get("confidence_basis", [])))
    rows.append(("Confidence basis", esc(basis)))
    rows.append((
        "Shelf life",
        f"{esc(data.get('volatility'))} &mdash; due for re-review "
        f"{esc(expiry)}{' <strong>(overdue)</strong>' if stale else ''}",
    ))
    if data.get("created_by_session"):
        rows.append(("Session", f"<code>{esc(data['created_by_session'])}</code>"))
    if data.get("sources"):
        links = " ".join(
            f'<a href="{esc(s)}" rel="nofollow noopener">{esc(s)}</a>'
            for s in data["sources"]
        )
        rows.append(("Sources", links))

    body = "\n".join(
        f"<div class=\"kb-row\"><dt>{label}</dt><dd>{value}</dd></div>"
        for label, value in rows
    )
    return (
        '<footer class="kb-provenance" data-pagefind-ignore>\n'
        "<h2>Provenance</h2>\n"
        f"<dl>{body}</dl>\n"
        f'<p class="kb-source">Source: <a href="{esc(md_href)}">raw markdown</a></p>\n'
        "</footer>"
    )


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} &middot; UseFullknowledge</title>
<meta name="description" content="{summary}">
{meta_tags}
<link rel="stylesheet" href="{root}assets/kb.css">
<script type="application/ld+json">
{json_ld}
</script>
</head>
<body>
<nav class="kb-nav" data-pagefind-ignore><a href="{root}index.html">UseFullknowledge</a></nav>
<main data-pagefind-body>
<h1>{title}</h1>
<p class="kb-summary">{summary}</p>
<span hidden data-pagefind-filter="review_status">{review_status}</span>
<span hidden data-pagefind-filter="type">{type}</span>
<span hidden data-pagefind-filter="confidence">{confidence}</span>
{banner}
{tags}
{body}
{footer}
</main>
{mermaid}
</body>
</html>
"""

MERMAID_SNIPPET = """<script src="{root}%s"></script>
<script>
mermaid.initialize({{
  startOnLoad: true,
  securityLevel: "strict",
  theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default"
}});
</script>
""" % MERMAID_JS


def _render_document(rel, doc, today, out):
    data = doc.data
    expiry = expires_on(data["created_at"], data["volatility"], data.get("review_reviewed_at"))
    stale = is_stale(expiry, today)
    depth = rel.count("/")
    root = "../" * depth
    name = pathlib.PurePosixPath(rel).name

    body_html = render_body(doc.body)
    has_mermaid = MERMAID_MARKER in body_html

    tag_links = " ".join(
        f'<a class="kb-tag" href="{root}tags/{html.escape(t)}.html">{html.escape(t)}</a>'
        for t in sorted(data.get("tags", []))
    )

    page = PAGE.format(
        title=html.escape(data["title"]),
        summary=html.escape(data["summary"]),
        review_status=html.escape(data.get("review_status", "unreviewed")),
        type=html.escape(data["type"]),
        confidence=html.escape(sorted(data.get("confidence_basis", ["unknown"]))[0]),
        meta_tags=_meta_tags(data, expiry),
        json_ld=_json_ld(data, expiry, f"{SITE_BASE}/{rel[:-3]}.html"),
        root=root,
        banner=_banner(data, stale, expiry),
        tags=f'<p class="kb-tags">{tag_links}</p>' if tag_links else "",
        body=body_html,
        footer=_provenance_footer(data, expiry, stale, name),
        mermaid=MERMAID_SNIPPET.format(root=root) if has_mermaid else "",
    )

    target = out / (rel[:-3] + ".html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


LIST_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} &middot; UseFullknowledge</title>
<link rel="stylesheet" href="{root}assets/kb.css">
<link rel="stylesheet" href="{root}pagefind/pagefind-ui.css">
</head>
<body>
<nav class="kb-nav"><a href="{root}index.html">UseFullknowledge</a></nav>
<main>
<h1>{title}</h1>
{intro}
<div id="search"></div>
<script src="{root}pagefind/pagefind-ui.js"></script>
<script>
window.addEventListener("DOMContentLoaded", () => {{
  if (window.PagefindUI) {{
    new PagefindUI({{ element: "#search", showSubResults: true, showImages: false }});
  }}
}});
</script>
{body}
</main>
</body>
</html>
"""


def _card(entry, root, today):
    stale = is_stale(entry["expires_on"], today)
    flags = f'<span class="kb-status kb-status-{entry["review_status"]}">{entry["review_status"]}</span>'
    if stale:
        flags += ' <span class="kb-status kb-status-stale">stale</span>'
    tags = " ".join(
        f'<a class="kb-tag" href="{root}tags/{html.escape(t)}.html">{html.escape(t)}</a>'
        for t in entry["tags"]
    )
    return (
        '<article class="kb-card">'
        f'<h3><a href="{root}{entry["html"]}">{html.escape(entry["title"])}</a></h3>'
        f'<p>{html.escape(entry["summary"])}</p>'
        f'<p class="kb-meta">{flags} <span class="kb-type">{entry["type"]}</span> {tags}</p>'
        "</article>"
    )


def _write_index_pages(out, entries, today):
    by_tag = {}
    for entry in entries:
        for tag in entry["tags"]:
            by_tag.setdefault(tag, []).append(entry)

    for tag, docs in by_tag.items():
        body = "\n".join(_card(d, "../", today) for d in docs)
        (out / "tags").mkdir(parents=True, exist_ok=True)
        (out / "tags" / f"{tag}.html").write_text(
            LIST_PAGE.format(title=f"Tag: {tag}", root="../", intro="", body=body),
            encoding="utf-8",
        )

    verified = sum(1 for e in entries if e["review_status"] == "verified")
    tag_cloud = " ".join(
        f'<a class="kb-tag" href="tags/{html.escape(t)}.html">{html.escape(t)} '
        f'<span class="kb-count">{len(d)}</span></a>'
        for t, d in sorted(by_tag.items())
    )
    intro = (
        f'<p class="kb-summary">{len(entries)} documents across {len(by_tag)} topics. '
        f'{verified} verified by a human.</p>'
        f'<p class="kb-tags">{tag_cloud}</p>'
        '<p class="kb-agent">Agents: start at <a href="llms.txt">llms.txt</a> or '
        '<a href="catalog/index.json">catalog/index.json</a>.</p>'
    )
    body = "\n".join(_card(e, "", today) for e in entries)
    (out / "index.html").write_text(
        LIST_PAGE.format(title="UseFullknowledge", root="", intro=intro, body=body),
        encoding="utf-8",
    )


def build_site(root, out_dir, today):
    """Render the whole corpus plus catalog, nav and assets into ``out_dir``."""
    root_path = pathlib.Path(root)
    out = pathlib.Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for rel, text in iter_documents(root):
        try:
            doc = parse(text)
        except ParseError:
            continue
        if not all(k in doc.data for k in
                   ("id", "title", "type", "summary", "created_at", "updated_at", "volatility")):
            continue
        _render_document(rel, doc, today, out)
        # Publish the source next to the render so agents can fetch either.
        target_md = out / rel
        target_md.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root_path / rel, target_md)

    entries = build_catalog(root, out_dir, today)
    _write_index_pages(out, entries, today)

    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "kb.css").write_text(CSS, encoding="utf-8")

    # Self-hosted so a published page never calls an external runtime.
    vendored = root_path / "vendor" / "mermaid.min.js"
    if vendored.exists():
        shutil.copyfile(vendored, assets / "mermaid.min.js")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return entries


CSS = """\
:root {
  color-scheme: light dark;
  --bg: #ffffff;
  --fg: #1a1a1a;
  --muted: #5a5f6a;
  --line: #e2e5ea;
  --card: #f7f8fa;
  --link: #0b5fff;
  --warn-bg: #fff6e5;
  --warn-line: #e8a33d;
  --raw-bg: #f3eaff;
  --raw-line: #8b5cf6;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1115;
    --fg: #e6e8ec;
    --muted: #9aa1ad;
    --line: #262b33;
    --card: #161a21;
    --link: #7aa2ff;
    --warn-bg: #2b2213;
    --warn-line: #c98a2e;
    --raw-bg: #201a2e;
    --raw-line: #a78bfa;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 46rem; margin: 0 auto; padding: 1.5rem 1.1rem 4rem; }
.kb-nav {
  padding: 0.9rem 1.1rem;
  border-bottom: 1px solid var(--line);
  font-weight: 600;
}
.kb-nav a, main a { color: var(--link); }
h1 { font-size: 1.8rem; line-height: 1.25; margin: 1.2rem 0 0.4rem; }
h2 { font-size: 1.3rem; margin-top: 2rem; }
h3 { font-size: 1.08rem; }
.kb-summary { color: var(--muted); font-size: 1.05rem; margin-top: 0; }
.kb-banner {
  border-left: 4px solid var(--warn-line);
  background: var(--warn-bg);
  padding: 0.7rem 0.9rem;
  border-radius: 0 6px 6px 0;
  margin: 1.1rem 0;
}
.kb-banner-raw { border-left-color: var(--raw-line); background: var(--raw-bg); }
.kb-tag {
  display: inline-block;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.1rem 0.6rem;
  margin: 0.15rem 0.2rem 0.15rem 0;
  font-size: 0.85rem;
  text-decoration: none;
}
.kb-count { color: var(--muted); }
.kb-status {
  display: inline-block;
  border-radius: 4px;
  padding: 0.05rem 0.45rem;
  font-size: 0.8rem;
  border: 1px solid var(--line);
  background: var(--card);
}
.kb-status-verified { border-color: #2e9e5b; color: #2e9e5b; }
.kb-status-unreviewed, .kb-status-stale { border-color: var(--warn-line); color: var(--warn-line); }
.kb-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.8rem 1rem;
  margin: 0.8rem 0;
  background: var(--card);
}
.kb-card h3 { margin: 0 0 0.3rem; }
.kb-card p { margin: 0.25rem 0; }
.kb-meta { font-size: 0.85rem; color: var(--muted); }
pre {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0.8rem;
  overflow-x: auto;
}
code { font-size: 0.9em; }
/* Diagram source before mermaid replaces it, and the SVG after. Bordered like a
   figure rather than a code block, and horizontally scrollable on a phone. */
pre.mermaid {
  background: transparent;
  border: 1px solid var(--line);
  text-align: center;
  padding: 1rem 0.5rem;
  overflow-x: auto;
  font-size: 0.8rem;
  color: var(--muted);
}
pre.mermaid svg { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 0.4rem 0.6rem; text-align: left; }
.kb-provenance {
  margin-top: 3rem;
  border-top: 2px solid var(--line);
  padding-top: 1rem;
  font-size: 0.92rem;
}
.kb-provenance h2 { font-size: 1.05rem; margin: 0 0 0.6rem; }
.kb-provenance dl { margin: 0; }
.kb-row { display: flex; gap: 0.8rem; padding: 0.3rem 0; border-bottom: 1px solid var(--line); }
.kb-row dt { flex: 0 0 9.5rem; color: var(--muted); margin: 0; }
.kb-row dd { margin: 0; flex: 1; word-break: break-word; }
.kb-model { color: var(--muted); }
.kb-source { margin-top: 0.7rem; }
@media (max-width: 34rem) {
  .kb-row { flex-direction: column; gap: 0.1rem; }
  .kb-row dt { flex: none; font-size: 0.82rem; }
}
"""
