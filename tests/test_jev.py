"""Tests for the Jev client. No network: every test injects a transport.

Run:  PYTHONPATH=tools python3 -m unittest tests.test_jev -v
"""

import unittest

from kbtool.jev import (
    DEFAULT_MODEL,
    MAX_STATE_CHARS,
    JevRequestError,
    JevUnavailable,
    ask,
)

KEY = {"TYPESAFE_API_KEY": "test-key-not-real"}
Q = {"q": {"type": "noul", "instructions": "Is this about Kafka?"}}
OK = {"model": DEFAULT_MODEL, "answers": {"q": {"type": "noul", "noul": 0.9}},
      "usage": {"input_tokens": 12}}


def fake(*replies):
    """A transport returning each (status, json) in turn, recording requests."""
    queue = list(replies)

    def transport(body, key, timeout):
        transport.calls.append((body, key))
        return queue.pop(0) if len(queue) > 1 else queue[0]

    transport.calls = []
    return transport


class TestAsk(unittest.TestCase):

    def test_returns_the_answers(self):
        result = ask("Kafka rebalancing.", Q, env=KEY, transport=fake((200, OK)))
        self.assertEqual(result.answers["q"]["noul"], 0.9)
        self.assertEqual(result.model, DEFAULT_MODEL)

    def test_sends_the_pinned_model_state_and_questions(self):
        transport = fake((200, OK))
        ask("state", Q, env=KEY, transport=transport)
        body, key = transport.calls[0]
        self.assertEqual(body, {"model": DEFAULT_MODEL, "state": "state", "questions": Q})
        self.assertEqual(key, "test-key-not-real")

    def test_no_key_is_unavailable_and_nothing_is_sent(self):
        transport = fake((200, OK))
        with self.assertRaises(JevUnavailable):
            ask("state", Q, env={}, transport=transport)
        self.assertEqual(transport.calls, [])

    def test_rejected_key_is_unavailable(self):
        with self.assertRaises(JevUnavailable):
            ask("state", Q, env=KEY, transport=fake((401, {"detail": "bad key"})))

    def test_errors_never_contain_the_key(self):
        for status in (401, 422, 500):
            try:
                ask("state", Q, env=KEY,
                    transport=fake((status, {"detail": "test-key-not-real"})))
            except (JevUnavailable, JevRequestError) as exc:
                self.assertNotIn("test-key-not-real", str(exc), status)

    def test_malformed_request_is_a_caller_bug(self):
        with self.assertRaises(JevRequestError):
            ask("state", Q, env=KEY,
                transport=fake((422, {"detail": [{"msg": "Field required"}]})))

    def test_busy_service_is_retried_then_succeeds(self):
        transport = fake((529, {}), (200, OK))
        result = ask("state", Q, env=KEY, transport=transport, backoff=0)
        self.assertEqual(result.answers["q"]["noul"], 0.9)
        self.assertEqual(len(transport.calls), 2)

    def test_busy_service_that_stays_busy_is_unavailable(self):
        with self.assertRaises(JevUnavailable):
            ask("state", Q, env=KEY, transport=fake((429, {})), backoff=0)

    def test_a_different_model_answering_a_pinned_request_is_refused(self):
        """Thresholds are tuned to one model; silently answering with another re-tunes them."""
        drifted = dict(OK, model="jev-1.14.0")
        with self.assertRaises(JevUnavailable):
            ask("state", Q, env=KEY, transport=fake((200, drifted)))

    def test_oversize_state_is_refused_before_sending(self):
        transport = fake((200, OK))
        with self.assertRaises(JevRequestError):
            ask("x" * (MAX_STATE_CHARS + 1), Q, env=KEY, transport=transport)
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
