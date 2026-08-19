"""Sensitive-data pre-commit hook.

Scans document text for patterns that should never appear in a public
knowledge base: email addresses, phone numbers, API keys, and Slack
channel names.  The hook is a safety net — the real protection is the
contributor\'s discipline, but a safety net catches what discipline misses.
"""

import re

class SensitiveDataError(Exception):
    """Raised when staged text contains sensitive data."""

# Patterns are intentionally broad — false positives are better than
# false negatives when the cost is leaking private data to a public repo.
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
API_KEY_RE = re.compile(r"\b(?:sk-[a-zA-Z0-9]{16,}|AKIA[A-Z0-9]{16,}|ghp_[a-zA-Z0-9]{20,})\b")
# Slack channel names: #word-word, but NOT markdown headers (#word or ##word at line start)
SLACK_CHANNEL_RE = re.compile(r"(?<![#\n])#[a-z][a-z0-9_-]{2,}[a-z0-9]")

PATTERNS = [
    (EMAIL_RE, "email address"),
    (PHONE_RE, "phone number"),
    (API_KEY_RE, "API key"),
    (SLACK_CHANNEL_RE, "Slack channel name"),
]

def scan_text(text, raise_on_find=False):
    """Return a list of findings (human-readable strings).

    If raise_on_find is True, raise SensitiveDataError on the first finding.
    """
    findings = []
    for pattern, label in PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            finding = f"sensitive data: {label} ({m})"
            findings.append(finding)
            if raise_on_find:
                raise SensitiveDataError(finding)
    return findings
