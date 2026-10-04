"""One real call to Jev. Skipped unless KB_JEV_LIVE=1 and TYPESAFE_API_KEY is set.

Gated on an explicit opt-in, not on the key alone: a contributor whose shell
always exports the key should not hit the network on every test run.

Run:  KB_JEV_LIVE=1 PYTHONPATH=tools python3 -m unittest tests.test_jev_live -v
"""

import os
import unittest

from kbtool.jev import DEFAULT_MODEL, ask

LIVE = os.environ.get("KB_JEV_LIVE") == "1" and os.environ.get("TYPESAFE_API_KEY")


@unittest.skipUnless(LIVE, "set KB_JEV_LIVE=1 and TYPESAFE_API_KEY to call the real API")
class TestLive(unittest.TestCase):

    def test_the_pinned_model_answers_an_obvious_question(self):
        result = ask("Kafka consumer groups rebalance partitions across their members.",
                     {"kafka": {"type": "noul", "instructions": "Is this text about Apache Kafka?"}},
                     env=os.environ)
        self.assertEqual(result.model, DEFAULT_MODEL)
        self.assertGreater(result.answers["kafka"]["noul"], 0.8)


if __name__ == "__main__":
    unittest.main()
