import unittest

from kbtool.shelflife import SHELF_LIFE_DAYS, expires_on, is_stale


class TestShelfLife(unittest.TestCase):
    def test_every_volatility_value_has_a_shelf_life(self):
        self.assertEqual(
            set(SHELF_LIFE_DAYS), {"ephemeral", "fast", "slow", "evergreen"}
        )

    def test_fast_moving_content_expires_sooner_than_evergreen(self):
        self.assertLess(SHELF_LIFE_DAYS["fast"], SHELF_LIFE_DAYS["evergreen"])

    def test_expiry_is_measured_from_the_review_date_when_reviewed(self):
        """Reviewing a document resets its shelf life."""
        result = expires_on(
            created_at="2026-01-01T00:00:00Z",
            volatility="fast",
            reviewed_at="2026-06-01T00:00:00Z",
        )

        self.assertTrue(result.startswith("2026-"))
        self.assertGreater(result, "2026-06-01")

    def test_expiry_falls_back_to_creation_when_never_reviewed(self):
        result = expires_on(created_at="2026-01-01T00:00:00Z", volatility="fast")

        self.assertEqual(result, "2026-04-01")

    def test_evergreen_content_expires_far_out(self):
        result = expires_on(created_at="2026-01-01T00:00:00Z", volatility="evergreen")

        self.assertGreater(result, "2035-01-01")

    def test_expiry_is_a_plain_date_not_a_timestamp(self):
        result = expires_on(created_at="2026-01-01T00:00:00Z", volatility="slow")

        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2}$")


class TestIsStale(unittest.TestCase):
    def test_document_past_its_expiry_is_stale(self):
        self.assertTrue(is_stale("2026-01-01", today="2026-08-14"))

    def test_document_before_its_expiry_is_not_stale(self):
        self.assertFalse(is_stale("2027-01-01", today="2026-08-14"))

    def test_expiry_today_is_not_yet_stale(self):
        self.assertFalse(is_stale("2026-08-14", today="2026-08-14"))


if __name__ == "__main__":
    unittest.main()
