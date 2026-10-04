"""Tests for the `kb review` command.

Recording a review used to go through `kb update --reviewer --reviewer-kind`,
which let any agent quietly declare itself a human reviewer. `kb review` is the
one command that writes the review fields, so AGENTS.md can name exactly what
an agent must never run, and it writes all of them together so the result
passes the schema.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_review -v
"""

import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

from kbtool.cli import main
from kbtool.frontmatter import parse
from kbtool.schema import validate

from test_update import _make_repo

DOC_ID = "kafka-partition-rebalancing-7f3a"
NOW = "2026-08-19T14:00:00+00:00"


class TestReviewCommand(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _make_repo(self.root)
        self.doc_path = (pathlib.Path(self.root) / "kb" / "explainer" /
                         f"{DOC_ID}.md")

    def tearDown(self):
        self.tmp.cleanup()

    def _review(self, *extra):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "review", DOC_ID, *extra])
        return rc, buf.getvalue()

    def test_human_verification_writes_every_review_field(self):
        rc, _ = self._review("--status", "verified", "--reviewer", "chris",
                             "--kind", "human", "--now", NOW)
        self.assertEqual(rc, 0)
        data = parse(self.doc_path.read_text()).data
        self.assertEqual(data["review_status"], "verified")
        self.assertEqual(data["review_reviewer"], "chris")
        self.assertEqual(data["review_reviewer_kind"], "human")
        self.assertEqual(data["review_reviewed_at"], NOW)
        self.assertEqual(data["updated_at"], NOW)
        self.assertEqual(data["updated_by_kind"], "human")

    def test_reviewed_document_passes_the_schema(self):
        """The old flags left review_reviewed_at unset, so verified docs failed."""
        rc, _ = self._review("--status", "verified", "--reviewer", "chris",
                             "--kind", "human", "--now", NOW)
        self.assertEqual(rc, 0)
        self.assertEqual(validate(parse(self.doc_path.read_text()).data), [])

    def test_agent_review_is_recorded_as_an_agent(self):
        rc, _ = self._review("--status", "reviewed", "--reviewer", "gpt-5",
                             "--kind", "agent", "--now", NOW)
        self.assertEqual(rc, 0)
        data = parse(self.doc_path.read_text()).data
        self.assertEqual(data["review_status"], "reviewed")
        self.assertEqual(data["review_reviewer_kind"], "agent")
        self.assertEqual(data["updated_by_kind"], "agent")

    def test_agent_cannot_verify_and_the_file_is_untouched(self):
        before = self.doc_path.read_text()
        rc, out = self._review("--status", "verified", "--reviewer", "gpt-5",
                               "--kind", "agent", "--now", NOW)
        self.assertEqual(rc, 1)
        self.assertIn("human", out)
        self.assertEqual(self.doc_path.read_text(), before)

    def test_a_partial_id_is_refused(self):
        """A review is a signature: it names exactly one document, never a prefix."""
        before = self.doc_path.read_text()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "review", "kafka-partition",
                       "--status", "reviewed", "--reviewer", "chris",
                       "--kind", "human"])
        self.assertEqual(rc, 1)
        self.assertIn(DOC_ID, buf.getvalue())
        self.assertEqual(self.doc_path.read_text(), before)

    def test_an_ambiguous_partial_id_is_an_error_not_a_traceback(self):
        (self.doc_path.parent / "kafka-partition-rebalancing-e6a4.md").write_text(
            self.doc_path.read_text().replace(DOC_ID, "kafka-partition-rebalancing-e6a4"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "review", "kafka-partition-rebalancing",
                       "--status", "reviewed", "--reviewer", "chris",
                       "--kind", "human"])
        self.assertEqual(rc, 1)

    def test_unknown_document_returns_error(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "review", "nonexistent-id-1234",
                       "--status", "reviewed", "--reviewer", "chris",
                       "--kind", "human"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
