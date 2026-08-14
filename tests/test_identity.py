import unittest

from kbtool.identity import make_id, shortid, slugify


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_kebabs(self):
        self.assertEqual(slugify("Kafka Partition Rebalancing"), "kafka-partition-rebalancing")

    def test_strips_punctuation_and_collapses_separators(self):
        self.assertEqual(slugify("C4: Container  Diagram (Acme)"), "c4-container-diagram-acme")

    def test_transliterates_accents_rather_than_dropping_them(self):
        self.assertEqual(slugify("Café Naïve"), "cafe-naive")

    def test_never_starts_or_ends_with_a_separator(self):
        self.assertEqual(slugify("  --Kafka--  "), "kafka")

    def test_rejects_a_title_with_no_usable_characters(self):
        with self.assertRaises(ValueError):
            slugify("!!!")


class TestShortId(unittest.TestCase):
    def test_is_deterministic_for_the_same_inputs(self):
        a = shortid("kafka-partition-rebalancing", "claude-code", "2026-08-14T06:12:00-07:00")
        b = shortid("kafka-partition-rebalancing", "claude-code", "2026-08-14T06:12:00-07:00")

        self.assertEqual(a, b)

    def test_two_tools_filing_the_same_slug_the_same_day_do_not_collide(self):
        """The core multi-writer defence: same slug, same day, different tools."""
        a = shortid("kafka-partition-rebalancing", "claude-code", "2026-08-14T06:12:00-07:00")
        b = shortid("kafka-partition-rebalancing", "cursor", "2026-08-14T06:12:00-07:00")

        self.assertNotEqual(a, b)

    def test_is_four_lowercase_hex_characters(self):
        value = shortid("kafka", "claude-code", "2026-08-14T06:12:00-07:00")

        self.assertRegex(value, r"^[0-9a-f]{4}$")


class TestMakeId(unittest.TestCase):
    def test_combines_slug_and_shortid(self):
        doc_id = make_id("Kafka Partition Rebalancing", "claude-code", "2026-08-14T06:12:00-07:00")

        self.assertRegex(doc_id, r"^kafka-partition-rebalancing-[0-9a-f]{4}$")

    def test_id_is_stable_across_calls(self):
        args = ("Kafka Partition Rebalancing", "claude-code", "2026-08-14T06:12:00-07:00")

        self.assertEqual(make_id(*args), make_id(*args))


if __name__ == "__main__":
    unittest.main()
