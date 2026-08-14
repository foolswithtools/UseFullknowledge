"""Reconcile claimed timestamps against git history.

Frontmatter is a *claim*; git is the *fact*. An agent that edits a document and
forgets to bump ``updated_at`` is the most likely way this corpus rots, so the
validator checks the claim against history rather than trusting it.

The whole map comes from one ``git log --name-only`` pass: invoking ``git log``
once per file is roughly two orders of magnitude slower at corpus scale.
"""

import datetime
import subprocess

# Beyond this, a claimed updated_at and the real commit time have diverged
# enough that someone forgot to bump it.
DRIFT_TOLERANCE = datetime.timedelta(hours=24)

# Small allowance so a commit made moments after writing the file is not "future".
FUTURE_TOLERANCE = datetime.timedelta(hours=1)

_SEP = "\x1e"


def git_updated_map(root, runner=subprocess.run):
    """Map ``repo-relative path -> ISO timestamp of the commit that last touched it``.

    Files that have never been committed are absent rather than guessed.
    """
    result = runner(
        ["git", "log", "--name-only", "--no-merges", f"--pretty=format:{_SEP}%cI"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {}

    updated = {}
    stamp = None
    # split("\n"), not splitlines(): Python treats \x1e as a line boundary, which
    # would silently eat the record separator and leave every stamp unattached.
    for line in result.stdout.split("\n"):
        if line.startswith(_SEP):
            stamp = line[len(_SEP) :].strip()
        elif line.strip() and stamp:
            # git log walks newest first, so the first stamp seen wins.
            updated.setdefault(line.strip(), stamp)
    return updated


def _parse(value):
    return datetime.datetime.fromisoformat(value)


def reconcile(claimed, actual):
    """Return a problem string, or None when the claim is consistent with git."""
    if actual is None:
        return None

    claimed_at = _parse(claimed)
    actual_at = _parse(actual)
    delta = claimed_at - actual_at

    if delta > FUTURE_TOLERANCE:
        return (
            f"updated_at is in the future relative to the last commit "
            f"({claimed} claimed, {actual} in git)"
        )
    if -delta > DRIFT_TOLERANCE:
        return (
            f"updated_at is stale: the file was committed at {actual} but "
            f"updated_at still says {claimed}. Set updated_at to the time you "
            f"changed the file."
        )
    return None
