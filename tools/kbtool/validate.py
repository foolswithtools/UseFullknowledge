"""Repo-wide validation.

Checks are registered functions so each one is unit-testable in isolation and
new checks can land as WARNING before being promoted to ERROR.

Severity rule of thumb: an ERROR means *this commit is defective*. Anything that
can go wrong purely because time passed - staleness above all - is a WARNING.
A validator that turns CI red on a day nobody committed is a validator people
learn to bypass.
"""

import datetime
import os
import pathlib
import re

from kbtool import schema as schema_mod
from kbtool.frontmatter import ParseError, parse
from kbtool.gitmeta import git_updated_map, reconcile
from kbtool.shelflife import expires_on, is_stale

ERROR = "error"
WARNING = "warning"

CONTENT_TYPES = ("explainer", "diagram", "snippet", "prompt", "note")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

SECRET_PATTERNS = (
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")),
)


class Finding:
    def __init__(self, code, severity, path, message):
        self.code = code
        self.severity = severity
        self.path = path
        self.message = message

    def __repr__(self):
        return f"<{self.code} {self.severity} {self.path}>"

    def format(self):
        return f"{self.severity.upper():7} {self.code}  {self.path}\n         {self.message}"


class Report:
    def __init__(self, findings):
        self.findings = findings

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self):
        return [f for f in self.findings if f.severity == WARNING]

    @property
    def has_errors(self):
        return bool(self.errors)


def heading_slug(text):
    """GitHub-compatible heading anchor."""
    text = re.sub(r"[`*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s]+", "-", text)


def _strip_code(body):
    return FENCE_RE.sub("", body)


def iter_documents(root):
    """Yield (relative path, text) for every markdown file under kb/."""
    kb = pathlib.Path(root) / "kb"
    if not kb.is_dir():
        return
    for path in sorted(kb.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        yield rel, path.read_text(encoding="utf-8")


def validate_repo(root, today=None):
    today = today or datetime.date.today().isoformat()
    findings = []
    parsed = {}

    for rel, text in iter_documents(root):
        try:
            doc = parse(text)
        except ParseError as exc:
            findings.append(Finding("KB000", ERROR, rel, str(exc)))
            continue
        parsed[rel] = doc

    _check_schema(parsed, findings)
    _check_paths(parsed, findings)
    _check_duplicate_ids(parsed, findings)
    _check_links(root, parsed, findings)
    _check_staleness(parsed, findings, today)
    _check_secrets(parsed, findings)
    _check_placeholders(parsed, findings)
    _check_git_drift(root, parsed, findings)

    findings.sort(key=lambda f: (f.path, f.code))
    return Report(findings)


def _check_schema(parsed, findings):
    for rel, doc in parsed.items():
        for problem in schema_mod.validate(doc.data):
            findings.append(Finding("KB001", ERROR, rel, problem))


def _check_paths(parsed, findings):
    for rel, doc in parsed.items():
        doc_id = doc.data.get("id")
        declared = doc.data.get("type")
        stem = pathlib.PurePosixPath(rel).stem
        parent = pathlib.PurePosixPath(rel).parent.name

        if doc_id and stem != doc_id:
            findings.append(Finding(
                "KB010", ERROR, rel,
                f"filename must match the document id: rename this file to "
                f"'{doc_id}.md' (or change id to '{stem}')",
            ))
        if declared in CONTENT_TYPES and parent != declared:
            findings.append(Finding(
                "KB011", ERROR, rel,
                f"a document of type '{declared}' must live in kb/{declared}/, "
                f"not kb/{parent}/",
            ))


def _check_duplicate_ids(parsed, findings):
    seen = {}
    for rel, doc in parsed.items():
        doc_id = doc.data.get("id")
        if not doc_id:
            continue
        if doc_id in seen:
            findings.append(Finding(
                "KB012", ERROR, rel,
                f"duplicate id '{doc_id}' - already used by {seen[doc_id]}. "
                f"Ids must be unique; regenerate this one.",
            ))
        else:
            seen[doc_id] = rel


def _check_links(root, parsed, findings):
    for rel, doc in parsed.items():
        body = _strip_code(doc.body)
        own_anchors = {heading_slug(m.group(2)) for m in HEADING_RE.finditer(body)}
        here = pathlib.PurePosixPath(rel).parent

        for match in LINK_RE.finditer(body):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:", "//")):
                continue

            path_part, _, anchor = target.partition("#")

            if not path_part:
                if anchor and anchor not in own_anchors:
                    findings.append(Finding(
                        "KB021", ERROR, rel,
                        f"link to '#{anchor}' matches no heading in this document",
                    ))
                continue

            resolved = os.path.normpath(str(here / path_part))
            if not (pathlib.Path(root) / resolved).exists():
                findings.append(Finding(
                    "KB020", ERROR, rel,
                    f"broken link: '{target}' does not resolve to a file "
                    f"(looked for {resolved})",
                ))
                continue

            if anchor:
                target_rel = pathlib.PurePosixPath(resolved).as_posix()
                target_doc = parsed.get(target_rel)
                if target_doc is not None:
                    anchors = {
                        heading_slug(m.group(2))
                        for m in HEADING_RE.finditer(_strip_code(target_doc.body))
                    }
                    if anchor not in anchors:
                        findings.append(Finding(
                            "KB021", ERROR, rel,
                            f"link to '{target}' - no heading '#{anchor}' in that document",
                        ))


def _check_staleness(parsed, findings, today):
    for rel, doc in parsed.items():
        created = doc.data.get("created_at")
        volatility = doc.data.get("volatility")
        if not created or volatility not in ("ephemeral", "fast", "slow", "evergreen"):
            continue
        expiry = expires_on(created, volatility, doc.data.get("review_reviewed_at"))
        if is_stale(expiry, today):
            findings.append(Finding(
                "KB030", WARNING, rel,
                f"past its shelf life (due {expiry}, volatility '{volatility}'). "
                f"Re-review it, or change volatility if the subject moves slower "
                f"than declared.",
            ))


def _check_secrets(parsed, findings):
    for rel, doc in parsed.items():
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(doc.body):
                findings.append(Finding(
                    "KB040", ERROR, rel,
                    f"looks like a committed {label}. Remove it - this repo is public.",
                ))


def _check_placeholders(parsed, findings):
    """Templates ship TODO markers. Shipping one back means nobody looked."""
    for rel, doc in parsed.items():
        for key, value in sorted(doc.data.items()):
            text = " ".join(value) if isinstance(value, list) else str(value)
            if "TODO" in text:
                findings.append(Finding(
                    "KB050", ERROR, rel,
                    f"'{key}' still holds the template placeholder ({text!r}). "
                    f"Replace it with a real value.",
                ))
        if "TODO" in doc.body:
            findings.append(Finding(
                "KB051", WARNING, rel,
                "body still contains a TODO placeholder from the template",
            ))


def _check_git_drift(root, parsed, findings):
    if not (pathlib.Path(root) / ".git").exists():
        return
    actual = git_updated_map(root)
    for rel, doc in parsed.items():
        claimed = doc.data.get("updated_at")
        if not claimed:
            continue
        problem = reconcile(claimed, actual.get(rel))
        if problem:
            findings.append(Finding("KB019", ERROR, rel, problem))
