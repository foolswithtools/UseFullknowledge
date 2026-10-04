"""Tests for kb.py links, the opt-in external link and DOI checker. No network.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_links -v
"""

import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

from kbtool import links

DOC = """\
---
id: tone-0fdd
title: "Tone"
type: explainer
summary: "s"
tags: [t]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: t
created_by_model: m
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [primary-source-cited]
volatility: slow
sources:
  - https://www.aeaweb.org/articles?id=10.1257/aer.20220693
---

See [the paper](https://example.org/paper) and https://example.org/bare.
Internal links like [summary](#summary) and [other](../note/x.md) are kb check's job.

```bash
curl https://example.org/in-code-block
```
"""


class TestExtract(unittest.TestCase):

    def test_finds_source_markdown_and_bare_urls(self):
        urls = links.extract_urls(DOC)
        self.assertEqual(urls, [
            "https://www.aeaweb.org/articles?id=10.1257/aer.20220693",
            "https://example.org/paper",
            "https://example.org/bare",
        ])

    def test_finds_dois_inside_urls(self):
        self.assertEqual(links.extract_dois(DOC), ["10.1257/aer.20220693"])


class FakeFetch:
    def __init__(self, statuses):
        self.statuses = statuses
        self.seen = []

    def __call__(self, url):
        self.seen.append(url)
        status = self.statuses.get(url, 200)
        if isinstance(status, Exception):
            raise status
        return status


class TestClassify(unittest.TestCase):

    def test_404_and_410_are_broken(self):
        for status in (404, 410):
            self.assertEqual(links.check_url("u", FakeFetch({"u": status})), "broken")

    def test_bot_walls_and_server_errors_are_unchecked_not_broken(self):
        """3 of 7 real cited URLs refused a script; that says nothing about the link."""
        for status in (401, 403, 429, 500, 503):
            self.assertEqual(links.check_url("u", FakeFetch({"u": status})), "unchecked")

    def test_dns_failure_is_broken(self):
        fetch = FakeFetch({"u": links.LinkError("broken", "host not found")})
        self.assertEqual(links.check_url("u", fetch), "broken")

    def test_timeout_is_unchecked(self):
        fetch = FakeFetch({"u": links.LinkError("unchecked", "timed out")})
        self.assertEqual(links.check_url("u", fetch), "unchecked")

    def test_a_doi_is_checked_against_crossref(self):
        fetch = FakeFetch({"https://api.crossref.org/works/10.1257/aer.20220693": 404})
        self.assertEqual(links.check_doi("10.1257/aer.20220693", fetch), "broken")
        self.assertEqual(fetch.seen, ["https://api.crossref.org/works/10.1257/aer.20220693"])


class TestRun(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "kb" / "explainer").mkdir(parents=True)
        (self.root / "kb" / "explainer" / "tone-0fdd.md").write_text(DOC)

    def tearDown(self):
        self.tmp.cleanup()

    def run_links(self, fetch, ids=()):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = links.run(self.root, list(ids), fetch)
        return rc, buf.getvalue()

    def test_a_missing_doi_fails_and_names_file_and_doi(self):
        fetch = FakeFetch({"https://api.crossref.org/works/10.1257/aer.20220693": 404})
        rc, out = self.run_links(fetch)
        self.assertEqual(rc, 1)
        self.assertIn("kb/explainer/tone-0fdd.md", out)
        self.assertIn("10.1257/aer.20220693", out)

    def test_a_url_carrying_a_doi_is_judged_by_crossref_not_the_publisher(self):
        """Springer answers Python with 404 behind its bot wall; Crossref is authoritative."""
        fetch = FakeFetch({"https://www.aeaweb.org/articles?id=10.1257/aer.20220693": 404})
        rc, _ = self.run_links(fetch)
        self.assertEqual(rc, 0)
        self.assertNotIn("https://www.aeaweb.org/articles?id=10.1257/aer.20220693", fetch.seen)
        self.assertIn("https://api.crossref.org/works/10.1257/aer.20220693", fetch.seen)

    def test_unchecked_links_are_reported_but_do_not_fail(self):
        rc, out = self.run_links(FakeFetch({"https://example.org/paper": 403}))
        self.assertEqual(rc, 0)
        self.assertIn("unchecked", out)

    def test_all_good_passes(self):
        rc, _ = self.run_links(FakeFetch({}))
        self.assertEqual(rc, 0)

    def test_an_unknown_id_is_an_error(self):
        rc, _ = self.run_links(FakeFetch({}), ids=["nope-0000"])
        self.assertEqual(rc, 1)

    def test_cli_is_wired(self):
        from kbtool.cli import main
        with redirect_stdout(io.StringIO()):
            rc = main(["--root", str(self.root), "links", "nope-0000"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
