"""Tests for `kb advise <id> --claim`: one claim against its cited sources.

The validated shape was one claim and a ~1500-character excerpt of the
source, with a says_nothing option (9 of 10 as expected). Jev answers
confidently about URLs it never saw, so it is only ever given fetched text.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_claim -v
"""

import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

from kbtool import claim
from kbtool.jev import JevUnavailable
from kbtool.jev import Result

SOURCE = ("Unrelated preamble about cookies and site navigation. " * 60
          + "Under the eager protocol every consumer revokes all of its partitions "
            "when a rebalance starts, so consumption stops across the group. "
          + "Footer text about copyright and newsletters. " * 60)


class FakeJev:
    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.requests = []

    def __call__(self, state, questions):
        self.requests.append((state, questions))
        verdict = self.verdicts.pop(0)
        return Result("jev-1.13.0", {"relation": {
            "type": "choice", "choice": verdict, "confidence": 0.9,
            "probabilities": {verdict: 0.9}}}, {})


class TestWindows(unittest.TestCase):

    def test_windows_are_short_and_the_best_one_contains_the_claim_words(self):
        windows = claim.best_windows(SOURCE, "every consumer revokes all partitions in a rebalance")
        self.assertLessEqual(len(windows), claim.MAX_WINDOWS)
        self.assertTrue(all(len(w) <= claim.WINDOW_CHARS for w in windows))
        self.assertIn("revokes all of its partitions", windows[0])

    def test_html_is_reduced_to_text(self):
        html = ("<html><head><script>var x = 1;</script><style>p{}</style></head>"
                "<body><p>Every consumer &amp; partition.</p></body></html>")
        self.assertEqual(claim.html_to_text(html), "Every consumer & partition.")


class TestCheck(unittest.TestCase):

    def test_each_window_is_asked_with_the_tested_state_and_question(self):
        jev = FakeJev(["says_nothing", "supports", "says_nothing"])
        claim.check("every consumer revokes all partitions", SOURCE, jev)
        state, questions = jev.requests[0]
        self.assertEqual(sorted(state), ["claim", "source_excerpt"])
        self.assertEqual(questions, {"relation": claim.RELATION_Q})

    def test_any_window_that_supports_wins(self):
        jev = FakeJev(["says_nothing", "supports", "says_nothing"])
        verdict, p = claim.check("every consumer revokes all partitions", SOURCE, jev)
        self.assertEqual((verdict, p), ("supports", 0.9))

    def test_contradiction_is_reported(self):
        jev = FakeJev(["contradicts", "says_nothing", "says_nothing"])
        verdict, _ = claim.check("every consumer revokes all partitions", SOURCE, jev)
        self.assertEqual(verdict, "contradicts")

    def test_silence_everywhere_is_says_nothing(self):
        jev = FakeJev(["says_nothing"] * claim.MAX_WINDOWS)
        verdict, _ = claim.check("every consumer revokes all partitions", SOURCE, jev)
        self.assertEqual(verdict, "says_nothing")

    def test_no_source_text_is_unchecked_and_jev_is_not_asked(self):
        jev = FakeJev([])
        self.assertEqual(claim.check("anything", "", jev), ("unchecked", 0.0))
        self.assertEqual(jev.requests, [])


class TestSourceText(unittest.TestCase):

    def test_a_doi_source_uses_the_crossref_abstract(self):
        seen = []

        def fetch_text(url):
            seen.append(url)
            return '{"message": {"abstract": "<jats:p>Vocal tone moves stock prices.</jats:p>"}}'

        text = claim.source_text("https://www.aeaweb.org/articles?id=10.1257/aer.20220129", fetch_text)
        self.assertEqual(seen, ["https://api.crossref.org/works/10.1257/aer.20220129"])
        self.assertEqual(text, "Vocal tone moves stock prices.")

    def test_an_unfetchable_source_is_empty(self):
        def fetch_text(url):
            raise OSError("blocked")
        self.assertEqual(claim.source_text("https://example.org/walled", fetch_text), "")


DOC = """\
---
id: kafka-0001
title: "Kafka"
type: explainer
summary: "s"
tags: [kafka]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: t
created_by_model: m
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [primary-source-cited]
volatility: fast
sources:
  - https://example.org/kip-429
  - https://example.org/walled
---

Body.
"""


class TestRun(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "kb" / "explainer").mkdir(parents=True)
        (self.root / "kb" / "explainer" / "kafka-0001.md").write_text(DOC)

    def tearDown(self):
        self.tmp.cleanup()

    def run_claim(self, ask, fetch_text, doc_id="kafka-0001", source_file=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = claim.run(self.root, doc_id, "every consumer revokes all partitions",
                           ask, fetch_text, source_file=source_file)
        return rc, buf.getvalue()

    def test_each_cited_source_gets_a_verdict_and_walled_ones_are_unchecked(self):
        def fetch_text(url):
            if "walled" in url:
                raise OSError("403")
            return SOURCE
        rc, out = self.run_claim(FakeJev(["supports", "says_nothing", "says_nothing"]), fetch_text)
        self.assertEqual(rc, 0)
        self.assertRegex(out, r"supports\s+0\.90\s+https://example.org/kip-429")
        self.assertRegex(out, r"unchecked\s+https://example.org/walled")

    def test_a_source_file_replaces_fetching(self):
        path = self.root / "excerpt.txt"
        path.write_text(SOURCE)

        def fetch_text(url):
            raise AssertionError("must not fetch when a source file is given")
        rc, out = self.run_claim(FakeJev(["contradicts", "says_nothing", "says_nothing"]),
                                 fetch_text, source_file=str(path))
        self.assertEqual(rc, 0)
        self.assertIn("contradicts", out)
        self.assertIn("excerpt.txt", out)

    def test_unavailable_jev_skips_with_exit_0(self):
        def ask(state, questions):
            raise JevUnavailable("TYPESAFE_API_KEY is not set")
        rc, out = self.run_claim(ask, lambda url: SOURCE)
        self.assertEqual(rc, 0)
        self.assertIn("skipped", out)

    def test_unknown_id_is_an_error(self):
        rc, _ = self.run_claim(FakeJev([]), lambda url: SOURCE, doc_id="nope-0000")
        self.assertEqual(rc, 1)

    def test_cli_requires_exactly_one_id_with_claim(self):
        from kbtool.cli import main
        with redirect_stdout(io.StringIO()) as buf:
            rc = main(["--root", str(self.root), "advise", "--claim", "x"])
        self.assertEqual(rc, 1)
        self.assertIn("exactly one", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
