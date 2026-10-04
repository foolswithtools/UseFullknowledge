"""Check that external links resolve and cited DOIs exist. Opt-in: needs network.

``kb check`` validates internal links offline; this covers what it cannot.
It found a DOI in the corpus that never existed (10.1257/aer.20220693).

Only a definite answer fails a run: 404, 410, a host that does not resolve,
or a DOI Crossref has no record of. Many publishers refuse scripts (403, 429)
or are briefly down; those links are reported as unchecked, never as broken.
A URL that carries a DOI is checked through Crossref instead of the publisher.
"""

import pathlib
import re
import socket
import urllib.error
import urllib.request

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>)\]&]+")
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
TRAILING = ".,;:"
BROKEN_STATUSES = {404, 410}
CROSSREF = "https://api.crossref.org/works/"
# Some publishers turn away the default Python agent outright.
USER_AGENT = "Mozilla/5.0 (compatible; UseFullknowledge-linkcheck/1.0)"


class LinkError(Exception):
    """A fetch that produced no status. ``kind`` is 'broken' or 'unchecked'."""

    def __init__(self, kind, reason):
        super().__init__(reason)
        self.kind = kind


def _unique(items):
    return list(dict.fromkeys(items))


def extract_urls(text):
    """External URLs from `sources` and the body, code blocks excluded, in order."""
    from .frontmatter import parse

    doc = parse(text)
    found = [str(u) for u in doc.data.get("sources") or []]
    found += [u.rstrip(TRAILING) for u in URL_RE.findall(FENCE_RE.sub("", doc.body))]
    return _unique(found)


def extract_dois(text):
    return _unique(d.rstrip(TRAILING) for d in DOI_RE.findall(" ".join(extract_urls(text))))


def urllib_fetch(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, socket.gaierror):
            raise LinkError("broken", "host not found") from None
        raise LinkError("unchecked", str(exc.reason)) from None
    except (TimeoutError, OSError) as exc:
        raise LinkError("unchecked", exc.__class__.__name__) from None


def check_url(url, fetch):
    """Return 'ok', 'broken' or 'unchecked'."""
    try:
        status = fetch(url)
    except LinkError as exc:
        return exc.kind
    if status in BROKEN_STATUSES:
        return "broken"
    return "ok" if 200 <= status < 400 else "unchecked"


def check_doi(doi, fetch):
    return check_url(CROSSREF + doi, fetch)


def run(root, ids, fetch):
    """Check every document, or only those in ``ids``. Exit 1 if anything is broken."""
    from .validate import iter_documents

    docs = [(rel, text) for rel, text in iter_documents(root)
            if not ids or pathlib.PurePosixPath(rel).stem in ids]
    missing = set(ids) - {pathlib.PurePosixPath(rel).stem for rel, _ in docs}
    if missing:
        print(f"Error: no document with id {', '.join(sorted(missing))}")
        return 1

    broken = unchecked = checked = 0
    for rel, text in docs:
        # A URL carrying a DOI is judged by Crossref alone: publishers such as
        # Springer answer scripts with 404 from behind a bot wall.
        results = [("link", u, check_url(u, fetch)) for u in extract_urls(text)
                   if not DOI_RE.search(u)]
        results += [("DOI", d, check_doi(d, fetch)) for d in extract_dois(text)]
        checked += len(results)
        problems = [r for r in results if r[2] != "ok"]
        if problems:
            print(rel)
            for kind, target, status in problems:
                print(f"  {status:<9} {kind:<4} {target}")
        broken += sum(r[2] == "broken" for r in results)
        unchecked += sum(r[2] == "unchecked" for r in results)
    print(f"\n{checked} link(s) and DOI(s) in {len(docs)} document(s): "
          f"{broken} broken, {unchecked} unchecked.")
    return 1 if broken else 0
