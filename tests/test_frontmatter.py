import unittest

from kbtool.frontmatter import ParseError, parse


class TestFrontmatterSplit(unittest.TestCase):
    def test_parses_fields_and_body(self):
        doc = parse('---\ntitle: "Kafka"\ntype: explainer\n---\n\nBody text.\n')

        self.assertEqual(doc.data["title"], "Kafka")
        self.assertEqual(doc.data["type"], "explainer")
        self.assertEqual(doc.body.strip(), "Body text.")

    def test_timestamps_stay_strings_and_are_not_coerced_by_yaml(self):
        """PyYAML turns unquoted ISO timestamps into datetime objects and re-emits
        them with a space instead of 'T'. The tz-offset check must see raw text."""
        doc = parse("---\ncreated_at: 2026-08-14T06:12:00-07:00\n---\nbody\n")

        self.assertIsInstance(doc.data["created_at"], str)
        self.assertEqual(doc.data["created_at"], "2026-08-14T06:12:00-07:00")

    def test_reports_line_number_of_each_key(self):
        doc = parse('---\ntitle: "K"\ntype: explainer\nreview_status: verified\n---\nbody\n')

        self.assertEqual(doc.line_of("title"), 2)
        self.assertEqual(doc.line_of("review_status"), 4)

    def test_rejects_document_with_no_frontmatter(self):
        with self.assertRaises(ParseError) as cm:
            parse("# Just a heading\n\nNo frontmatter here.\n")

        self.assertIn("no frontmatter", str(cm.exception).lower())

    def test_rejects_unterminated_frontmatter(self):
        with self.assertRaises(ParseError) as cm:
            parse('---\ntitle: "K"\n\nbody with no closing fence\n')

        self.assertIn("unterminated", str(cm.exception).lower())

    def test_rejects_duplicate_keys_instead_of_silently_overriding(self):
        """A duplicate key silently overrides in PyYAML - which could overwrite
        provenance with a later value. Must be loud."""
        with self.assertRaises(ParseError) as cm:
            parse("---\nreview_status: unreviewed\nreview_status: verified\n---\nbody\n")

        self.assertIn("duplicate", str(cm.exception).lower())
        self.assertIn("review_status", str(cm.exception))

    def test_yes_no_style_tags_are_not_coerced_to_booleans(self):
        """YAML 1.1 parses bare no/on/off as booleans - a tag named 'no' would
        become False and vanish from the catalog."""
        doc = parse("---\ntags: [no, on, kafka]\n---\nbody\n")

        self.assertEqual(doc.data["tags"], ["no", "on", "kafka"])

    def test_handles_crlf_line_endings(self):
        doc = parse('---\r\ntitle: "K"\r\n---\r\nbody\r\n')

        self.assertEqual(doc.data["title"], "K")

    def test_strips_utf8_bom(self):
        doc = parse('﻿---\ntitle: "K"\n---\nbody\n')

        self.assertEqual(doc.data["title"], "K")


if __name__ == "__main__":
    unittest.main()
