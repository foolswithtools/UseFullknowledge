"""A stdlib client for TypeSafe's Jev decision model.

Jev does not generate text: it takes a ``state`` and typed questions (choice,
score, noul) and returns calibrated typed answers. See
https://docs.typesafe.ai/introduction.

Only the opt-in ``kb.py advise`` command uses this. ``check`` and ``build``
never import it, so CI and the published site stay offline and secret-free.
"""

import dataclasses
import json
import time
import urllib.error
import urllib.request

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
# Pinned, not jev-latest: every threshold in advise.py was tuned against this
# version, and an alias would silently re-tune them on TypeSafe's release day.
DEFAULT_MODEL = "jev-1.13.0"
# The API refuses about 32k tokens of state with a 400; refuse locally first.
MAX_STATE_CHARS = 100_000
RETRYABLE = {429, 529}


class JevUnavailable(Exception):
    """No key, a rejected key, the network, or a busy service. Skip, don't fail."""


class JevRequestError(Exception):
    """The API says our request is malformed: a bug in the caller."""


@dataclasses.dataclass(frozen=True)
class Result:
    model: str
    answers: dict
    usage: dict


def _urllib_transport(body, key, timeout):
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            try:
                return response.status, json.loads(response.read())
            except ValueError:
                raise JevUnavailable(f"reply was not JSON ({response.status})") from None
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        except ValueError:
            return exc.code, {}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise JevUnavailable(f"network error ({exc.__class__.__name__})") from None


def ask(state, questions, *, env, model=DEFAULT_MODEL, transport=None,
        timeout=15.0, retries=2, backoff=0.5):
    """Evaluate ``questions`` against ``state`` and return a Result.

    Raises JevUnavailable when the caller should skip, and JevRequestError
    when the request itself is wrong. Neither message ever includes the key.
    """
    if len(json.dumps(state)) > MAX_STATE_CHARS:
        raise JevRequestError("state too large: send one document at a time")
    key = env.get("TYPESAFE_API_KEY")
    if not key:
        raise JevUnavailable("TYPESAFE_API_KEY is not set")

    body = {"model": model, "state": state, "questions": questions}
    send = transport or _urllib_transport
    for attempt in range(retries + 1):
        status, reply = send(body, key, timeout)
        if status not in RETRYABLE or attempt == retries:
            break
        time.sleep(backoff * 2 ** attempt)

    if status == 401:
        raise JevUnavailable("API key rejected")
    if not isinstance(reply, dict):
        raise JevUnavailable(f"unexpected reply ({status})")
    if status in RETRYABLE:
        raise JevUnavailable(f"service busy ({status})")
    if status in (400, 422):
        # Redact before truncating: a key straddling the cut would survive in part.
        detail = json.dumps(reply.get("detail", reply)).replace(key, "***")[:300]
        raise JevRequestError(f"request rejected ({status}): {detail}")
    if status != 200:
        raise JevUnavailable(f"unexpected status {status}")
    if reply.get("model") != model:
        raise JevUnavailable(f"asked for {model} but {reply.get('model')} answered")
    return Result(reply["model"], reply["answers"], reply.get("usage", {}))
