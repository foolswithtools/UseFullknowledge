import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from kbtool.cli import main

GOOD = """\
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


class CliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for kind in ("explainer", "diagram", "snippet", "prompt", "note"):
            os.makedirs(os.path.join(self.root, "kb", kind))
        os.makedirs(os.path.join(self.root, "templates"), exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relpath, text):
        full = os.path.join(self.root, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(text)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--root", self.root, *args])
        return code, out.getvalue() + err.getvalue()


class TestCheck(CliCase):
    def test_clean_repo_exits_zero(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md", GOOD)

        code, _ = self.run_cli("check", "--today", "2026-08-14")

        self.assertEqual(code, 0)

    def test_broken_document_exits_nonzero(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md",
                   GOOD.replace('created_at: "2026-08-14T06:12:00-07:00"\n', ""))

        code, _ = self.run_cli("check", "--today", "2026-08-14")

        self.assertEqual(code, 1)

    def test_failure_output_names_the_file_and_the_check(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md",
                   GOOD.replace('created_at: "2026-08-14T06:12:00-07:00"\n', ""))

        _, output = self.run_cli("check", "--today", "2026-08-14")

        self.assertIn("kafka-partition-rebalancing-7f3a.md", output)
        self.assertIn("created_at", output)

    def test_warnings_alone_do_not_fail_the_build(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md",
                   GOOD.replace('created_at: "2026-08-14T06:12:00-07:00"',
                                'created_at: "2020-01-01T00:00:00-07:00"')
                       .replace('updated_at: "2026-08-14T06:12:00-07:00"',
                                'updated_at: "2020-01-01T00:00:00-07:00"'))

        code, output = self.run_cli("check", "--today", "2026-08-14")

        self.assertEqual(code, 0)
        self.assertIn("WARNING", output.upper())


class TestBuild(CliCase):
    def test_build_writes_a_site(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md", GOOD)

        code, _ = self.run_cli("build", "--today", "2026-08-14")

        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.root, "_site", "index.html")))

    def test_build_refuses_to_publish_an_invalid_corpus(self):
        """Validation gates the build, so bad provenance can never reach the site."""
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md",
                   GOOD.replace("review_status: unreviewed",
                                'review_status: verified\nreview_reviewer: gpt\n'
                                'review_reviewer_kind: agent\n'
                                'review_reviewed_at: "2026-08-14T06:12:00-07:00"'))

        code, _ = self.run_cli("build", "--today", "2026-08-14")

        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.root, "_site", "index.html")))


class TestNew(CliCase):
    def _template(self):
        self.write("templates/explainer.md", """\
---
id: TODO
title: "TODO"
type: explainer
summary: "TODO"
tags: [TODO]
created_at: "TODO"
created_by_tool: TODO
created_by_model: TODO
updated_at: "TODO"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only]
volatility: fast
---

## Summary

TODO
""")

    def test_new_scaffolds_a_document_that_passes_validation(self):
        self._template()

        code, output = self.run_cli(
            "new", "explainer", "Kafka partition rebalancing",
            "--tool", "claude-code", "--model", "claude-opus-5",
            "--now", "2026-08-14T06:12:00-07:00",
        )

        self.assertEqual(code, 0)
        created = [f for f in os.listdir(os.path.join(self.root, "kb", "explainer"))]
        self.assertEqual(len(created), 1)
        self.assertTrue(created[0].startswith("kafka-partition-rebalancing-"))
        self.assertIn(created[0], output)

    def test_scaffolded_document_has_matching_id_and_filename(self):
        self._template()
        self.run_cli("new", "explainer", "Kafka partition rebalancing",
                     "--tool", "claude-code", "--model", "claude-opus-5",
                     "--now", "2026-08-14T06:12:00-07:00")

        name = os.listdir(os.path.join(self.root, "kb", "explainer"))[0]
        with open(os.path.join(self.root, "kb", "explainer", name), encoding="utf-8") as h:
            text = h.read()

        self.assertIn(f"id: {name[:-3]}", text)

    def test_two_tools_filing_the_same_title_do_not_overwrite_each_other(self):
        self._template()
        self.run_cli("new", "explainer", "Kafka partition rebalancing",
                     "--tool", "claude-code", "--model", "m", "--now", "2026-08-14T06:12:00-07:00")
        self.run_cli("new", "explainer", "Kafka partition rebalancing",
                     "--tool", "cursor", "--model", "m", "--now", "2026-08-14T06:12:00-07:00")

        self.assertEqual(len(os.listdir(os.path.join(self.root, "kb", "explainer"))), 2)


if __name__ == "__main__":
    unittest.main()
