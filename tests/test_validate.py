import os
import tempfile
import textwrap
import unittest

from kbtool.validate import ERROR, WARNING, validate_repo

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

## Summary

Body text.
"""


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for kind in ("explainer", "diagram", "snippet", "prompt", "note"):
            os.makedirs(os.path.join(self.root, "kb", kind))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relpath, text):
        full = os.path.join(self.root, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(textwrap.dedent(text))
        return full

    def codes(self, severity=None):
        report = validate_repo(self.root, today="2026-08-14")
        return sorted(
            f.code for f in report.findings if severity is None or f.severity == severity
        )


class TestCleanRepo(RepoCase):
    def test_a_valid_document_produces_no_findings(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md", GOOD)

        self.assertEqual(self.codes(), [])

    def test_report_has_no_errors_for_a_clean_repo(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md", GOOD)

        self.assertFalse(validate_repo(self.root, today="2026-08-14").has_errors)


class TestSchemaAndProvenance(RepoCase):
    def test_missing_required_field_is_an_error(self):
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD.replace('created_at: "2026-08-14T06:12:00-07:00"\n', ""),
        )

        self.assertIn("KB001", self.codes(ERROR))

    def test_unparseable_frontmatter_is_an_error(self):
        self.write("kb/explainer/broken-0001.md", "# no frontmatter at all\n")

        self.assertIn("KB000", self.codes(ERROR))

    def test_agent_self_declared_verified_is_an_error(self):
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD.replace(
                "review_status: unreviewed",
                'review_status: verified\nreview_reviewer: gpt-5\n'
                'review_reviewer_kind: agent\n'
                'review_reviewed_at: "2026-08-14T06:12:00-07:00"',
            ),
        )

        self.assertIn("KB001", self.codes(ERROR))


class TestIdentityAndPaths(RepoCase):
    def test_filename_must_match_the_document_id(self):
        self.write("kb/explainer/wrong-name-0000.md", GOOD)

        self.assertIn("KB010", self.codes(ERROR))

    def test_directory_must_match_the_declared_type(self):
        self.write("kb/note/kafka-partition-rebalancing-7f3a.md", GOOD)

        self.assertIn("KB011", self.codes(ERROR))

    def test_duplicate_ids_across_files_are_an_error(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md", GOOD)
        self.write("kb/note/kafka-partition-rebalancing-7f3a.md", GOOD.replace(
            "type: explainer", "type: note"))

        self.assertIn("KB012", self.codes(ERROR))


class TestLinks(RepoCase):
    def test_broken_relative_link_is_an_error(self):
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD + "\nSee [the other doc](../explainer/does-not-exist-0000.md).\n",
        )

        self.assertIn("KB020", self.codes(ERROR))

    def test_working_relative_link_is_accepted(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md",
                   GOOD + "\nSee [other](./raft-consensus-1a2b.md).\n")
        self.write("kb/explainer/raft-consensus-1a2b.md",
                   GOOD.replace("kafka-partition-rebalancing-7f3a", "raft-consensus-1a2b"))

        self.assertNotIn("KB020", self.codes(ERROR))

    def test_broken_anchor_in_the_same_document_is_an_error(self):
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD + "\nJump to [nowhere](#no-such-heading).\n",
        )

        self.assertIn("KB021", self.codes(ERROR))

    def test_valid_anchor_is_accepted(self):
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD + "\nJump to [summary](#summary).\n",
        )

        self.assertNotIn("KB021", self.codes(ERROR))

    def test_external_links_are_not_checked(self):
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD + "\nSee [kafka](https://kafka.apache.org/nonexistent).\n",
        )

        self.assertEqual(self.codes(ERROR), [])


class TestStaleness(RepoCase):
    def test_a_document_past_its_shelf_life_is_a_warning_not_an_error(self):
        """Time passing is not a commit defect. An error here turns CI red on a
        day nobody committed, and that is how validators get bypassed."""
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD.replace('created_at: "2026-08-14T06:12:00-07:00"',
                         'created_at: "2020-01-01T00:00:00-07:00"')
                .replace('updated_at: "2026-08-14T06:12:00-07:00"',
                         'updated_at: "2020-01-01T00:00:00-07:00"'),
        )

        self.assertIn("KB030", self.codes(WARNING))
        self.assertNotIn("KB030", self.codes(ERROR))

    def test_stale_document_does_not_fail_the_build(self):
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD.replace('created_at: "2026-08-14T06:12:00-07:00"',
                         'created_at: "2020-01-01T00:00:00-07:00"')
                .replace('updated_at: "2026-08-14T06:12:00-07:00"',
                         'updated_at: "2020-01-01T00:00:00-07:00"'),
        )

        self.assertFalse(validate_repo(self.root, today="2026-08-14").has_errors)


class TestSecrets(RepoCase):
    def test_an_api_key_in_the_body_is_an_error(self):
        """Public repo, six tools dumping raw output."""
        self.write(
            "kb/note/leaky-0001.md",
            GOOD.replace("type: explainer", "type: note").replace(
                "kafka-partition-rebalancing-7f3a", "leaky-0001")
            + "\nUse key sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.\n",
        )

        self.assertIn("KB040", self.codes(ERROR))

    def test_ordinary_prose_is_not_flagged_as_a_secret(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md", GOOD)

        self.assertNotIn("KB040", self.codes())


class TestFindingQuality(RepoCase):
    def test_findings_name_the_file_and_the_fix(self):
        self.write("kb/explainer/wrong-name-0000.md", GOOD)
        report = validate_repo(self.root, today="2026-08-14")
        finding = next(f for f in report.findings if f.code == "KB010")

        self.assertIn("wrong-name-0000.md", finding.path)
        self.assertIn("kafka-partition-rebalancing-7f3a", finding.message)


if __name__ == "__main__":
    unittest.main()


class TestPlaceholders(RepoCase):
    def test_unfilled_todo_in_frontmatter_is_an_error(self):
        """kb new leaves TODO markers; shipping one means the agent never looked."""
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD.replace(
                'summary: "How Kafka reassigns partitions across consumer group members."',
                'summary: "TODO: one paragraph describing what this explains."',
            ),
        )

        self.assertIn("KB050", self.codes(ERROR))

    def test_unfilled_todo_in_the_body_is_a_warning(self):
        """A TODO in prose can be legitimate future work, so it must not block."""
        self.write(
            "kb/explainer/kafka-partition-rebalancing-7f3a.md",
            GOOD + "\nTODO: expand the cooperative sticky assignor section.\n",
        )

        self.assertIn("KB051", self.codes(WARNING))
        self.assertNotIn("KB051", self.codes(ERROR))

    def test_clean_document_has_no_placeholder_findings(self):
        self.write("kb/explainer/kafka-partition-rebalancing-7f3a.md", GOOD)

        self.assertNotIn("KB050", self.codes())
        self.assertNotIn("KB051", self.codes())
