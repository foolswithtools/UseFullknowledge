import json
import os
import tempfile
import textwrap
import unittest

from kbtool.catalog import build_catalog

DOC = """\
---
id: {id}
title: "{title}"
type: {type}
summary: "{summary}"
tags: [{tags}]
created_at: "2026-08-14T06:12:00-07:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-08-14T06:12:00-07:00"
updated_by_kind: agent
review_status: {review}
{extra}---

Body.
"""

VERIFIED_EXTRA = (
    "review_reviewer: chris\n"
    "review_reviewer_kind: human\n"
    'review_reviewed_at: "2026-08-14T06:12:00-07:00"\n'
)


class CatalogCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for kind in ("explainer", "diagram", "snippet", "prompt", "note"):
            os.makedirs(os.path.join(self.root, "kb", kind))

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, doc_id, title, tags, kind="explainer", review="unreviewed",
            summary="A summary.", volatility="fast"):
        extra = f"confidence_basis: [model-recall-only]\nvolatility: {volatility}\n"
        if review != "unreviewed":
            extra += VERIFIED_EXTRA
        text = DOC.format(id=doc_id, title=title, type=kind, summary=summary,
                          tags=", ".join(tags), review=review, extra=extra)
        path = os.path.join(self.root, "kb", kind, f"{doc_id}.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(textwrap.dedent(text))

    def build(self):
        out = os.path.join(self.root, "_site")
        build_catalog(self.root, out, today="2026-08-14")
        return out

    def read(self, out, relpath):
        with open(os.path.join(out, relpath), encoding="utf-8") as handle:
            return json.load(handle)


class TestTierOneRouter(CatalogCase):
    def test_router_lists_every_topic_with_counts(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        self.add("kafka-acls-1b2c", "Kafka ACLs", ["kafka", "security"])
        out = self.build()

        index = self.read(out, "catalog/index.json")
        topics = {t["topic"]: t for t in index["topics"]}

        self.assertEqual(topics["kafka"]["documents"], 2)
        self.assertEqual(topics["security"]["documents"], 1)

    def test_router_reports_how_many_documents_are_verified(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        self.add("kafka-acls-1b2c", "Kafka ACLs", ["kafka"], review="verified")
        out = self.build()

        topics = {t["topic"]: t for t in self.read(out, "catalog/index.json")["topics"]}

        self.assertEqual(topics["kafka"]["verified"], 1)

    def test_router_does_not_contain_full_document_records(self):
        """Tier 1 must stay a router: it grows with topic count, not corpus size."""
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"],
                 summary="A very distinctive summary string.")
        out = self.build()

        with open(os.path.join(out, "catalog", "index.json"), encoding="utf-8") as handle:
            raw = handle.read()

        self.assertNotIn("A very distinctive summary string.", raw)


class TestTierTwoShards(CatalogCase):
    def test_each_topic_gets_a_shard_with_full_records(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"],
                 summary="How Kafka reassigns partitions.")
        out = self.build()

        shard = self.read(out, "catalog/topics/kafka.json")
        entry = shard["documents"][0]

        self.assertEqual(entry["id"], "kafka-partition-rebalancing-7f3a")
        self.assertEqual(entry["summary"], "How Kafka reassigns partitions.")
        self.assertEqual(entry["review_status"], "unreviewed")

    def test_shard_entries_carry_expiry_as_a_precomputed_date(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        out = self.build()

        entry = self.read(out, "catalog/topics/kafka.json")["documents"][0]

        self.assertRegex(entry["expires_on"], r"^\d{4}-\d{2}-\d{2}$")

    def test_shard_entries_do_not_store_a_stale_boolean(self):
        """Staleness depends on the day it is asked, so storing it bakes in a lie."""
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        out = self.build()

        entry = self.read(out, "catalog/topics/kafka.json")["documents"][0]

        self.assertNotIn("stale", entry)
        self.assertNotIn("is_stale", entry)

    def test_shard_entry_points_at_both_markdown_and_html(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        out = self.build()

        entry = self.read(out, "catalog/topics/kafka.json")["documents"][0]

        self.assertEqual(entry["md"], "kb/explainer/kafka-partition-rebalancing-7f3a.md")
        self.assertEqual(entry["html"], "kb/explainer/kafka-partition-rebalancing-7f3a.html")

    def test_a_document_with_three_topics_appears_in_three_shards(self):
        self.add("kafka-on-k8s-9z9z", "Kafka on Kubernetes",
                 ["kafka", "kubernetes", "operations"])
        out = self.build()

        for topic in ("kafka", "kubernetes", "operations"):
            shard = self.read(out, f"catalog/topics/{topic}.json")
            self.assertEqual(shard["documents"][0]["id"], "kafka-on-k8s-9z9z")


class TestVerifiedFastPath(CatalogCase):
    def test_verified_catalog_contains_only_verified_documents(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        self.add("kafka-acls-1b2c", "Kafka ACLs", ["kafka"], review="verified")
        out = self.build()

        ids = [d["id"] for d in self.read(out, "catalog/verified.json")["documents"]]

        self.assertEqual(ids, ["kafka-acls-1b2c"])


class TestLlmsTxt(CatalogCase):
    def test_llms_txt_is_written_and_explains_the_trust_query(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        out = self.build()

        with open(os.path.join(out, "llms.txt"), encoding="utf-8") as handle:
            text = handle.read()

        self.assertIn("catalog/index.json", text)
        self.assertIn("review_status", text)
        self.assertIn("expires_on", text)

    def test_llms_txt_stays_small_enough_to_be_a_cheap_first_fetch(self):
        for i in range(50):
            self.add(f"topic-{i:03d}-aaaa", f"Doc {i}", [f"topic-{i:03d}"])
        out = self.build()

        size = os.path.getsize(os.path.join(out, "llms.txt"))

        self.assertLess(size, 8000, "llms.txt must remain a cheap single fetch")


class TestDeterminism(CatalogCase):
    def test_rebuilding_produces_byte_identical_output(self):
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        self.add("crispr-base-editing-4d4d", "CRISPR base editing", ["crispr", "biology"])

        first = self.build()
        snapshot = {}
        for base, _, files in os.walk(first):
            for name in files:
                full = os.path.join(base, name)
                with open(full, "rb") as handle:
                    snapshot[os.path.relpath(full, first)] = handle.read()

        second = self.build()
        for rel, content in snapshot.items():
            with open(os.path.join(second, rel), "rb") as handle:
                self.assertEqual(handle.read(), content, f"{rel} changed between builds")

    def test_output_contains_no_wall_clock_timestamp(self):
        """A build-time clock would make every rebuild a diff."""
        self.add("kafka-partition-rebalancing-7f3a", "Kafka rebalancing", ["kafka"])
        out = self.build()

        with open(os.path.join(out, "catalog", "index.json"), encoding="utf-8") as handle:
            index = json.load(handle)

        self.assertNotIn("generated_at", index)

    def test_documents_are_ordered_deterministically(self):
        self.add("zzz-last-0001", "Z", ["shared"])
        self.add("aaa-first-0002", "A", ["shared"])
        out = self.build()

        ids = [d["id"] for d in self.read(out, "catalog/topics/shared.json")["documents"]]

        self.assertEqual(ids, sorted(ids))


if __name__ == "__main__":
    unittest.main()
