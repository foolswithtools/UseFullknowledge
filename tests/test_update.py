"""TDD tests for the `kb update` command.

The review workflow currently requires manual YAML editing — the exact
friction that ensures review never happens.  These tests specify the
behaviour we want: one command to update frontmatter fields on an
existing document, with automatic updated_at timestamping.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_update -v
"""

import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

from kbtool.cli import main
from kbtool.frontmatter import parse


def _make_repo(root):
    """Create a minimal repo with one valid explainer document."""
    for kind in ("explainer", "diagram", "snippet", "prompt", "note"):
        os.makedirs(os.path.join(root, "kb", kind), exist_ok=True)
    os.makedirs(os.path.join(root, "templates"), exist_ok=True)
    # Copy the real explainer template.
    src = pathlib.Path(root) / ".." / "templates" / "explainer.md"
    if src.exists():
        (pathlib.Path(root) / "templates" / "explainer.md").write_text(
            src.read_text()
        )
    else:
        # Fallback: minimal template.
        (pathlib.Path(root) / "templates" / "explainer.md").write_text(
            "---\nid: TODO\ntitle: \"TODO\"\ntype: explainer\nsummary: \"TODO\"\n"
            "tags: [todo]\ncreated_at: \"2026-08-14T06:12:00-07:00\"\n"
            "created_by_tool: test\ncreated_by_model: test\n"
            "updated_at: \"2026-08-14T06:12:00-07:00\"\nupdated_by_kind: agent\n"
            "review_status: unreviewed\nconfidence_basis: [model-recall-only]\n"
            "volatility: fast\n---\n\nBody.\n"
        )
    # Create one valid document.
    doc = """\
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
confidence_basis: [model-recall-only]
volatility: fast
---

Body.
"""
    (pathlib.Path(root) / "kb" / "explainer" /
     "kafka-partition-rebalancing-7f3a.md").write_text(doc)


class TestUpdateCommand(unittest.TestCase):
    """`kb update` changes frontmatter fields in place."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _make_repo(self.root)
        self.doc_path = pathlib.Path(self.root) / "kb" / "explainer" / \
            "kafka-partition-rebalancing-7f3a.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_update_changes_review_status(self):
        """`kb update <id> --set review_status=reviewed` changes the field."""
        rc = main(["--root", self.root, "update",
                    "kafka-partition-rebalancing-7f3a",
                    "--set", "review_status=reviewed"])
        self.assertEqual(rc, 0)
        text = self.doc_path.read_text()
        doc = parse(text)
        self.assertEqual(doc.data["review_status"], "reviewed")

    def test_update_sets_reviewer_for_verified(self):
        """`kb update --set review_status=verified --reviewer chris --reviewer-kind human`
        sets all three fields together."""
        rc = main(["--root", self.root, "update",
                    "kafka-partition-rebalancing-7f3a",
                    "--set", "review_status=verified",
                    "--reviewer", "chris",
                    "--reviewer-kind", "human"])
        self.assertEqual(rc, 0)
        doc = parse(self.doc_path.read_text())
        self.assertEqual(doc.data["review_status"], "verified")
        self.assertEqual(doc.data["review_reviewer"], "chris")
        self.assertEqual(doc.data["review_reviewer_kind"], "human")

    def test_update_refreshes_updated_at(self):
        """`kb update` always refreshes updated_at to now."""
        rc = main(["--root", self.root, "update",
                    "kafka-partition-rebalancing-7f3a",
                    "--set", "review_status=reviewed",
                    "--now", "2026-08-19T14:00:00+00:00"])
        self.assertEqual(rc, 0)
        doc = parse(self.doc_path.read_text())
        self.assertEqual(doc.data["updated_at"], "2026-08-19T14:00:00+00:00")

    def test_update_nonexistent_document_returns_error(self):
        """`kb update nonexistent-id` returns 1 and prints an error."""
        import io
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "update",
                        "nonexistent-id-1234",
                        "--set", "review_status=reviewed"])
        self.assertEqual(rc, 1)

    def test_update_unknown_field_returns_error(self):
        """`kb update --set bogus_field=value` returns 1."""
        import io
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "update",
                        "kafka-partition-rebalancing-7f3a",
                        "--set", "bogus_field=value"])
        self.assertEqual(rc, 1)

    def test_update_preserves_body_and_other_fields(self):
        """`kb update` only changes the specified fields, leaving the rest
        (including body) intact."""
        original_body = self.doc_path.read_text().split("---\n", 2)[-1]
        rc = main(["--root", self.root, "update",
                    "kafka-partition-rebalancing-7f3a",
                    "--set", "review_status=reviewed",
                    "--now", "2026-08-19T14:00:00+00:00"])
        self.assertEqual(rc, 0)
        new_text = self.doc_path.read_text()
        new_body = new_text.split("---\n", 2)[-1]
        self.assertEqual(original_body.strip(), new_body.strip())
        doc = parse(new_text)
        self.assertEqual(doc.data["title"], "Kafka partition rebalancing")


if __name__ == "__main__":
    unittest.main()
