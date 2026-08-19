"""TDD tests for the sensitive-data pre-commit hook.

A pre-commit hook that scans staged documents for sensitive data:
person names, email addresses, phone numbers, and project-specific
identifiers.  If any are found, the commit is rejected.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_precommit -v
"""

import os
import pathlib
import tempfile
import unittest

from kbtool.precommit import scan_text, SensitiveDataError


class TestPrecommitScan(unittest.TestCase):
    """scan_text returns the sensitive patterns it finds, or raises."""

    def test_clean_text_passes(self):
        """Text with no sensitive data returns an empty list."""
        text = "This is a normal document about Kafka partition rebalancing."
        findings = scan_text(text)
        self.assertEqual(findings, [])

    def test_email_address_is_flagged(self):
        """Email addresses are flagged as sensitive."""
        text = "Contact me at chris@example.com for details."
        findings = scan_text(text)
        self.assertTrue(any("email" in f.lower() for f in findings),
                        f"Expected email flag in {findings}")

    def test_phone_number_is_flagged(self):
        """Phone numbers are flagged as sensitive."""
        text = "Call me at 555-123-4567."
        findings = scan_text(text)
        self.assertTrue(any("phone" in f.lower() for f in findings),
                        f"Expected phone flag in {findings}")

    def test_api_key_pattern_is_flagged(self):
        """API key patterns (sk-..., AKIA...) are flagged."""
        text = "Use the key sk-1234567890abcdef for authentication."
        findings = scan_text(text)
        self.assertTrue(any("api" in f.lower() or "key" in f.lower() for f in findings),
                        f"Expected API key flag in {findings}")

    def test_slack_channel_name_is_flagged(self):
        """Slack channel names (#founders-random, #aios-loup) are flagged."""
        text = "Posted in #aios-loup today."
        findings = scan_text(text)
        self.assertTrue(any("slack" in f.lower() or "channel" in f.lower() for f in findings),
                        f"Expected Slack channel flag in {findings}")

    def test_normal_technical_text_is_not_flagged(self):
        """Technical text that happens to contain # (headers) is not flagged."""
        text = "## Kafka Partition Rebalancing\n\n### Consumer Groups"
        findings = scan_text(text)
        self.assertEqual(findings, [])

    def test_raise_on_sensitive_blocks_commit(self):
        """check_staged raises SensitiveDataError when findings exist."""
        text = "My email is secret@private.com"
        with self.assertRaises(SensitiveDataError):
            scan_text(text, raise_on_find=True)


if __name__ == "__main__":
    unittest.main()
