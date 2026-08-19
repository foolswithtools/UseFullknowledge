"""TDD tests for the `kb search` command.

The tiered catalog is designed for agent retrieval via HTTPS, but there's
no local search command. An agent working in the repo can't query
"show me all verified explainers about Kafka" without grep.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_search -v
"""

import os
import pathlib
import tempfile
import unittest
import io
from contextlib import redirect_stdout

from kbtool.cli import main


def _make_repo_with_docs(root):
    """Create a repo with multiple documents for search testing."""
    for kind in ("explainer", "diagram", "snippet", "prompt", "note"):
        os.makedirs(os.path.join(root, "kb", kind), exist_ok=True)
    os.makedirs(os.path.join(root, "templates"), exist_ok=True)

    doc1 = """\
---
id: kafka-partition-rebalancing-7f3a
title: "Kafka partition rebalancing"
type: explainer
summary: "How Kafka reassigns partitions across consumer group members."
tags: [kafka, consumer-groups]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only]
volatility: fast
---

Body about Kafka partitions.
"""
    doc2 = """\
---
id: redis-cluster-sharding-a1b2
title: "Redis cluster sharding"
type: explainer
summary: "How Redis distributes data across cluster nodes."
tags: [redis, sharding]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: cursor
created_by_model: gpt-5
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: reviewed
review_reviewer: chris
review_reviewer_kind: human
confidence_basis: [primary-source-cited]
sources: ["https://redis.io/docs"]
volatility: slow
---

Body about Redis sharding.
"""
    doc3 = """\
---
id: kafka-connect-sinks-3c4d
title: "Kafka Connect sink connectors"
type: explainer
summary: "How Kafka Connect writes data to external systems."
tags: [kafka, connect]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only]
volatility: fast
---

Body about Kafka Connect.
"""
    for doc, name in [
        (doc1, "kafka-partition-rebalancing-7f3a.md"),
        (doc2, "redis-cluster-sharding-a1b2.md"),
        (doc3, "kafka-connect-sinks-3c4d.md"),
    ]:
        (pathlib.Path(root) / "kb" / "explainer" / name).write_text(doc)


class TestSearchCommand(unittest.TestCase):
    """`kb search` queries documents locally without HTTPS."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _make_repo_with_docs(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_search_by_tag(self):
        """`kb search --tag kafka` finds both Kafka documents."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "search", "--tag", "kafka"])
        self.assertEqual(rc, 0)
        output = buf.getvalue()
        self.assertIn("kafka-partition-rebalancing", output)
        self.assertIn("kafka-connect-sinks", output)
        self.assertNotIn("redis-cluster", output)

    def test_search_by_status(self):
        """`kb search --status reviewed` finds only reviewed docs."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "search", "--status", "reviewed"])
        self.assertEqual(rc, 0)
        output = buf.getvalue()
        self.assertIn("redis-cluster-sharding", output)
        self.assertNotIn("kafka-partition", output)

    def test_search_by_type(self):
        """`kb search --type explainer` finds all explainers."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "search", "--type", "explainer"])
        self.assertEqual(rc, 0)
        output = buf.getvalue()
        self.assertIn("kafka-partition", output)
        self.assertIn("redis-cluster", output)
        self.assertIn("kafka-connect", output)

    def test_search_with_no_filters_lists_all(self):
        """`kb search` with no filters lists all documents."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "search"])
        self.assertEqual(rc, 0)
        output = buf.getvalue()
        self.assertIn("kafka-partition", output)
        self.assertIn("redis-cluster", output)
        self.assertIn("kafka-connect", output)

    def test_search_combined_filters(self):
        """`kb search --tag kafka --status unreviewed` finds unreviewed Kafka docs."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--root", self.root, "search",
                        "--tag", "kafka", "--status", "unreviewed"])
        self.assertEqual(rc, 0)
        output = buf.getvalue()
        self.assertIn("kafka-partition", output)
        self.assertIn("kafka-connect", output)
        self.assertNotIn("redis-cluster", output)


if __name__ == "__main__":
    unittest.main()
