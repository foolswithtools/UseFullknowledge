import json
import os
import re
import tempfile
import unittest

from kbtool.render import build_site

DOC = """\
---
id: {id}
title: "{title}"
type: {type}
summary: "{summary}"
tags: [kafka]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
created_by_session: "sess_01H9XKQ2"
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: {review}
confidence_basis: [model-recall-only]
volatility: fast
{extra}---

## Summary

Partitions are reassigned when a consumer joins or leaves.

{body}
"""

VERIFIED_EXTRA = (
    "review_reviewer: chris\n"
    "review_reviewer_kind: human\n"
    'review_reviewed_at: "2026-08-14T06:12:00-07:00"\n'
)


class RenderCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for kind in ("explainer", "diagram", "snippet", "prompt", "note"):
            os.makedirs(os.path.join(self.root, "kb", kind))

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, doc_id="kafka-partition-rebalancing-7f3a", title="Kafka partition rebalancing",
            kind="explainer", review="unreviewed", body="", summary="How Kafka reassigns partitions.",
            extra=""):
        if review != "unreviewed":
            extra += VERIFIED_EXTRA
        text = DOC.format(id=doc_id, title=title, type=kind, review=review,
                          body=body, summary=summary, extra=extra)
        with open(os.path.join(self.root, "kb", kind, f"{doc_id}.md"), "w",
                  encoding="utf-8") as handle:
            handle.write(text)

    def build(self):
        out = os.path.join(self.root, "_site")
        build_site(self.root, out, today="2026-08-14")
        return out

    def page(self, out, relpath="kb/explainer/kafka-partition-rebalancing-7f3a.html"):
        with open(os.path.join(out, relpath), encoding="utf-8") as handle:
            return handle.read()


class TestOutputPaths(RenderCase):
    def test_html_mirrors_the_source_path(self):
        self.add()
        out = self.build()

        self.assertTrue(os.path.exists(
            os.path.join(out, "kb", "explainer", "kafka-partition-rebalancing-7f3a.html")))

    def test_raw_markdown_is_published_alongside_the_html(self):
        """Agents must be able to fetch source without scraping rendered pages."""
        self.add()
        out = self.build()

        md = os.path.join(out, "kb", "explainer", "kafka-partition-rebalancing-7f3a.md")
        self.assertTrue(os.path.exists(md))
        with open(md, encoding="utf-8") as handle:
            self.assertIn("id: kafka-partition-rebalancing-7f3a", handle.read())

    def test_a_home_page_is_generated(self):
        self.add()
        out = self.build()

        self.assertTrue(os.path.exists(os.path.join(out, "index.html")))

    def test_a_tag_page_is_generated(self):
        self.add()
        out = self.build()

        self.assertTrue(os.path.exists(os.path.join(out, "tags", "kafka.html")))


class TestBodyRendering(RenderCase):
    def test_markdown_body_becomes_html(self):
        self.add()

        self.assertIn("<h2", self.page(self.build()))

    def test_tables_render(self):
        self.add(body="| a | b |\n|---|---|\n| 1 | 2 |\n")

        self.assertIn("<table>", self.page(self.build()))

    def test_headings_get_anchor_ids_so_deep_links_work(self):
        self.add()
        html = self.page(self.build())

        self.assertRegex(html, r'<h2[^>]*id="summary"')

    def test_internal_md_links_are_rewritten_to_html(self):
        self.add(body="See [other](./raft-consensus-1a2b.md).")
        html = self.page(self.build())

        self.assertIn('href="./raft-consensus-1a2b.html"', html)

    def test_external_links_are_left_alone(self):
        self.add(body="See [kafka](https://kafka.apache.org/docs.md).")

        self.assertIn('href="https://kafka.apache.org/docs.md"', self.page(self.build()))


class TestMachineReadableProvenance(RenderCase):
    def test_json_ld_block_is_present_and_valid_json(self):
        self.add()
        html = self.page(self.build())

        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        self.assertIsNotNone(match, "no JSON-LD block found")
        json.loads(match.group(1))

    def test_json_ld_describes_the_document_and_its_creator(self):
        self.add()
        html = self.page(self.build())
        data = json.loads(re.search(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL).group(1))

        self.assertEqual(data["@type"], "TechArticle")
        self.assertEqual(data["headline"], "Kafka partition rebalancing")
        self.assertEqual(data["dateCreated"], "2026-08-14T06:12:00-07:00")
        self.assertEqual(data["creator"]["name"], "claude-code")

    def test_meta_tags_expose_review_status_and_expiry(self):
        self.add()
        html = self.page(self.build())

        self.assertIn('<meta name="kb:review_status" content="unreviewed">', html)
        self.assertRegex(html, r'<meta name="kb:expires_on" content="\d{4}-\d{2}-\d{2}">')


class TestVisibleProvenance(RenderCase):
    def test_footer_shows_what_created_the_document(self):
        """A reader arriving from a search engine must be able to judge this
        without opening the repo."""
        self.add()
        html = self.page(self.build())

        self.assertIn("claude-code", html)
        self.assertIn("claude-opus-5", html)

    def test_footer_shows_review_status_and_timestamps(self):
        self.add()
        html = self.page(self.build())

        self.assertIn("unreviewed", html)
        self.assertIn("2026-08-14T06:12:00-07:00", html)

    def test_unreviewed_document_carries_a_visible_warning(self):
        self.add()

        self.assertIn("not been reviewed", self.page(self.build()).lower())

    def test_verified_document_names_its_human_reviewer(self):
        self.add(review="verified")
        html = self.page(self.build())

        self.assertIn("chris", html)
        self.assertIn("verified", html.lower())

    def test_raw_note_is_visibly_quarantined(self):
        self.add(doc_id="scratch-thoughts-0001", title="Scratch", kind="note")
        html = self.page(self.build(), "kb/note/scratch-thoughts-0001.html")

        self.assertIn("raw", html.lower())
        self.assertIn("unreviewed", html.lower())


class TestDiagrams(RenderCase):
    def test_mermaid_fence_becomes_the_element_mermaid_actually_looks_for(self):
        """mermaid's startOnLoad scans for class="mermaid"; it ignores the
        <code class="language-mermaid"> that markdown-it emits by default."""
        self.add(body="```mermaid\nC4Container\n  title Acme\n```")
        html = self.page(self.build())

        self.assertIn('<pre class="mermaid">', html)
        self.assertIn("C4Container", html)

    def test_mermaid_source_is_html_escaped_inside_the_block(self):
        self.add(body="```mermaid\nC4Container\n  title A <b>x</b> B\n```")
        html = self.page(self.build())

        self.assertIn("&lt;b&gt;", html)
        self.assertNotIn("<b>x</b>", html)

    def test_mermaid_runtime_is_only_loaded_on_pages_that_need_it(self):
        self.add(body="Just prose, no diagram.")

        self.assertNotIn("mermaid.min.js", self.page(self.build()))

    def test_diagram_source_stays_greppable_in_the_published_markdown(self):
        self.add(body="```mermaid\nC4Container\n```")
        out = self.build()

        with open(os.path.join(out, "kb", "explainer",
                               "kafka-partition-rebalancing-7f3a.md"), encoding="utf-8") as h:
            self.assertIn("C4Container", h.read())


class TestPresentation(RenderCase):
    def test_stylesheet_is_written_and_theme_aware(self):
        self.add()
        out = self.build()

        with open(os.path.join(out, "assets", "kb.css"), encoding="utf-8") as handle:
            css = handle.read()

        self.assertIn("prefers-color-scheme: dark", css)

    def test_pages_are_mobile_ready(self):
        self.add()

        self.assertIn('name="viewport"', self.page(self.build()))


class TestEscaping(RenderCase):
    def test_title_with_markup_is_escaped_not_injected(self):
        self.add(title="Kafka <script>alert(1)</script>")
        html = self.page(self.build())

        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()


class TestSearchIndexing(RenderCase):
    def test_document_body_is_marked_for_indexing(self):
        self.add()

        self.assertIn("data-pagefind-body", self.page(self.build()))

    def test_review_status_is_exposed_as_a_search_filter(self):
        """Faceted trust filtering in the UI: show me only verified documents."""
        self.add()

        self.assertIn('data-pagefind-filter="review_status"', self.page(self.build()))

    def test_type_is_exposed_as_a_search_filter(self):
        self.add()

        self.assertIn('data-pagefind-filter="type"', self.page(self.build()))

    def test_provenance_footer_is_excluded_from_the_index(self):
        """Otherwise every document matches a search for 'claude-opus-5'."""
        html = self.page(self.build()) if self.add() is None else None
        self.assertIn("data-pagefind-ignore", html)

    def test_home_page_offers_search(self):
        self.add()
        out = self.build()

        with open(os.path.join(out, "index.html"), encoding="utf-8") as handle:
            self.assertIn("pagefind-ui", handle.read())
