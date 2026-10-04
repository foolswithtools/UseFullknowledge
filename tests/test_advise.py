"""Tests for kb.py advise's per-document checks. No network: `ask` is faked.

The question wording and the state each question sees were validated live in
the Jev evaluation; these tests pin both so neither drifts unnoticed.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_advise -v
"""

import io
import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from kbtool import advise
from kbtool.cli import main
from kbtool.jev import JevRequestError, JevUnavailable
from kbtool.frontmatter import parse
from kbtool.jev import Result

DOC = """\
---
id: kafka-partition-rebalancing-7f3a
title: "Kafka partition rebalancing"
type: explainer
summary: "How Kafka reassigns partitions across consumer group members."
tags: [kafka]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [primary-source-cited]
volatility: fast
sources:
  - https://kafka.apache.org/documentation/
---

## Summary

Eager rebalancing revokes every partition. <!-- hidden note -->
"""


class FakeJev:
    """Answers by question id; records each request's state and questions."""

    def __init__(self, guard=0.05, overclaim=0.1, summary="faithful", summary_p=0.95):
        self.replies = {
            "injection": {"type": "noul", "noul": guard},
            "overclaim": {"type": "noul", "noul": overclaim},
            "summary": {"type": "choice", "choice": summary,
                        "probabilities": {summary: summary_p}, "confidence": 0.9},
        }
        self.requests = []

    def __call__(self, state, questions):
        self.requests.append((state, questions))
        return Result("jev-1.13.0", {q: self.replies[q] for q in questions}, {})

    def state_for(self, question_id):
        return next(s for s, q in self.requests if question_id in q)


def run(jev):
    return advise.advise_document(parse(DOC), jev)


def by_check(advice):
    return {a.check: a for a in advice}


class TestRequests(unittest.TestCase):

    def test_each_check_is_its_own_request(self):
        """Each question was validated against its own state shape; merging them is untested."""
        jev = FakeJev()
        run(jev)
        self.assertEqual(sorted(tuple(q) for _, q in jev.requests),
                         [("injection",), ("overclaim",), ("summary",)])

    def test_the_guard_sees_html_comments(self):
        """Hidden comments are where an injection would hide."""
        jev = FakeJev()
        run(jev)
        self.assertIn("<!-- hidden note -->", jev.state_for("injection")["body"])

    def test_the_other_checks_never_see_html_comments(self):
        jev = FakeJev()
        run(jev)
        self.assertNotIn("hidden note", jev.state_for("summary")["body"])
        self.assertNotIn("hidden note", jev.state_for("overclaim")["document"]["body"])

    def test_summary_state_has_the_tested_keys(self):
        jev = FakeJev()
        run(jev)
        state = jev.state_for("summary")
        self.assertEqual(sorted(state), ["body", "frontmatter_summary", "tags", "title"])
        self.assertEqual(state["frontmatter_summary"],
                         "How Kafka reassigns partitions across consumer group members.")

    def test_overclaim_state_explains_each_declared_basis(self):
        jev = FakeJev()
        run(jev)
        state = jev.state_for("overclaim")
        self.assertEqual(sorted(state), ["declared_confidence_basis", "declared_sources", "document"])
        self.assertIn("primary source", state["declared_confidence_basis"]["primary-source-cited"])
        self.assertEqual(state["declared_sources"], ["https://kafka.apache.org/documentation/"])


class TestAdvice(unittest.TestCase):

    def test_a_clean_document_gets_no_advice(self):
        self.assertEqual(run(FakeJev()), [])

    def test_a_firing_guard_suppresses_all_other_advice(self):
        jev = FakeJev(guard=0.95, overclaim=0.9, summary="unfaithful")
        advice = run(jev)
        self.assertEqual([a.check for a in advice], ["injection"])
        self.assertEqual([tuple(q) for _, q in jev.requests], [("injection",)])

    def test_strong_overclaim_is_likely(self):
        self.assertEqual(by_check(run(FakeJev(overclaim=0.75)))["overclaim"].level, "likely")

    def test_middling_overclaim_is_possible(self):
        self.assertEqual(by_check(run(FakeJev(overclaim=0.39)))["overclaim"].level, "possible")

    def test_low_overclaim_is_not_reported(self):
        self.assertNotIn("overclaim", by_check(run(FakeJev(overclaim=0.2))))

    def test_vague_or_unfaithful_summary_is_reported(self):
        for verdict in ("vague", "unfaithful"):
            advice = by_check(run(FakeJev(summary=verdict, summary_p=0.99)))
            self.assertIn(verdict, advice["summary"].message, verdict)

    def test_faithful_summary_is_not_reported(self):
        self.assertNotIn("summary", by_check(run(FakeJev(summary="faithful"))))


class TestRun(unittest.TestCase):
    """`kb advise [ids]` over a repo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "kb" / "explainer").mkdir(parents=True)
        (self.root / "kb" / "explainer" / "kafka-partition-rebalancing-7f3a.md").write_text(DOC)

    def tearDown(self):
        self.tmp.cleanup()

    def run_advise(self, jev, ids=()):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = advise.run(self.root, list(ids), jev)
        return rc, buf.getvalue()

    def test_advice_names_the_file_check_level_and_score(self):
        rc, out = self.run_advise(FakeJev(overclaim=0.39))
        self.assertEqual(rc, 0)
        self.assertIn("kb/explainer/kafka-partition-rebalancing-7f3a.md", out)
        self.assertRegex(out, r"overclaim\s+possible\s+0\.39")

    def test_output_says_it_is_advice_not_a_fact_check(self):
        _, out = self.run_advise(FakeJev())
        self.assertIn("not a fact check", out.lower())

    def test_ids_limit_the_documents(self):
        jev = FakeJev()
        rc, _ = self.run_advise(jev, ids=["no-such-doc-0000"])
        self.assertEqual(rc, 1)
        self.assertEqual(jev.requests, [])

    def test_unavailable_jev_is_skipped_with_exit_0(self):
        def unavailable(state, questions):
            raise JevUnavailable("TYPESAFE_API_KEY is not set")
        rc, out = self.run_advise(unavailable)
        self.assertEqual(rc, 0)
        self.assertIn("skipped", out)

    def test_a_malformed_request_fails_loudly(self):
        def broken(state, questions):
            raise JevRequestError("request rejected (422)")
        rc, out = self.run_advise(broken)
        self.assertEqual(rc, 1)
        self.assertIn("422", out)

    def test_cli_without_a_key_skips_and_sends_nothing(self):
        env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
        buf = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("kbtool.jev._urllib_transport") as transport, redirect_stdout(buf):
            rc = main(["--root", str(self.root), "advise"])
        self.assertEqual(rc, 0)
        self.assertIn("skipped", buf.getvalue())
        transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()
