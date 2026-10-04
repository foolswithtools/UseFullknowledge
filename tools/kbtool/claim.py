"""Check one claim against the text of a cited source, with Jev. Advice only.

Validated shape (9 of 10 as expected, no option-order drift): one claim plus
a ~1500-character excerpt, and a says_nothing option. Whole pages were not
tested and can exceed the API's 32k-token limit, so the source is cut into
windows and only the few that share the most words with the claim are sent.

Jev answers confidently about a URL it never saw, so it is only ever handed
fetched text. A source that cannot be fetched is "unchecked", never guessed.
"""

import html
import json
import re
import urllib.request

from .links import DOI_RE, USER_AGENT

WINDOW_CHARS = 1500
WINDOW_STRIDE = 750
MAX_WINDOWS = 3
MAX_FETCH_BYTES = 2_000_000

RELATION_Q = {
    "type": "choice",
    "instructions": "How does `source_excerpt` relate to `claim`?",
    "criteria": {
        "supports": "The excerpt states the claim or directly implies that it is true",
        "contradicts": "The excerpt states the opposite of the claim or implies it is false",
        "says_nothing": "The excerpt does not address what the claim asserts, either way",
    },
}

_STOP = set("a an the and or of to in for with on by is are be it its this that as at from "
            "how what why not was were has have had their they them than then into when".split())


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOP}


def html_to_text(markup):
    markup = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", markup))
    return re.sub(r"\s+", " ", text).strip()


def best_windows(text, claim_text):
    """The MAX_WINDOWS excerpts of ``text`` sharing the most words with the claim."""
    wanted = _words(claim_text)
    starts = range(0, max(1, len(text) - WINDOW_STRIDE), WINDOW_STRIDE)
    windows = [text[i:i + WINDOW_CHARS] for i in starts]
    ranked = sorted(windows, key=lambda w: len(wanted & _words(w)), reverse=True)
    return ranked[:MAX_WINDOWS]


def check(claim_text, text, ask):
    """Return (verdict, probability): supports, contradicts, says_nothing or unchecked."""
    if not text.strip():
        return "unchecked", 0.0
    answers = []
    for window in best_windows(text, claim_text):
        reply = ask({"claim": claim_text, "source_excerpt": window},
                    {"relation": RELATION_Q}).answers["relation"]
        answers.append((reply["choice"], reply["probabilities"].get(reply["choice"], 0.0)))
    decisive = [a for a in answers if a[0] != "says_nothing"]
    return max(decisive or answers, key=lambda a: a[1])


def urllib_fetch_text(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_FETCH_BYTES).decode("utf-8", errors="replace")


def source_text(url, fetch_text):
    """Plain text of a source: the Crossref abstract for a DOI, else the page. '' if unavailable."""
    try:
        doi = DOI_RE.search(url)
        if doi:
            record = json.loads(fetch_text("https://api.crossref.org/works/" + doi.group(0)))
            abstract = record.get("message", {}).get("abstract")
            if abstract:
                return html_to_text(abstract)
        return html_to_text(fetch_text(url))
    except Exception:
        return ""


def run(root, doc_id, claim_text, ask, fetch_text, source_file=None):
    """Print a verdict on ``claim_text`` for each cited source of one document."""
    import pathlib

    from .frontmatter import parse
    from .jev import DEFAULT_MODEL, JevRequestError, JevUnavailable

    path = next(pathlib.Path(root).glob(f"kb/*/{doc_id}.md"), None)
    if path is None:
        print(f"Error: no document with id {doc_id}")
        return 1

    if source_file:
        sources = [(pathlib.Path(source_file).name, pathlib.Path(source_file).read_text())]
    else:
        urls = [str(u) for u in parse(path.read_text()).data.get("sources") or []]
        if not urls:
            print("Error: the document lists no sources; pass --source-file.")
            return 1
        sources = [(u, source_text(u, fetch_text)) for u in urls]

    print(f"Claim check by Jev ({DEFAULT_MODEL}), advice for a human reviewer. "
          "Only fetched text is judged; 'unchecked' means it could not be read.\n"
          f"Claim: {claim_text}\n")
    for name, text in sources:
        try:
            verdict, p = check(claim_text, text, ask)
        except JevUnavailable as exc:
            print(f"Jev skipped: {exc}")
            return 0
        except JevRequestError as exc:
            print(f"Error: {exc}")
            return 1
        score = f"{p:.2f}" if verdict != "unchecked" else "    "
        print(f"  {verdict:<12} {score}  {name}")
    return 0
