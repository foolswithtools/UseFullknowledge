import unittest

from kbtool.schema import validate

BASE = {
    "id": "kafka-partition-rebalancing-7f3a",
    "title": "Kafka partition rebalancing",
    "type": "explainer",
    "summary": "How Kafka reassigns partitions across consumer group members.",
    "tags": ["kafka"],
    "created_at": "2026-08-14T06:12:00-07:00",
    "created_by_tool": "claude-code",
    "created_by_model": "claude-opus-5",
    "updated_at": "2026-08-14T06:12:00-07:00",
    "updated_by_kind": "agent",
    "review_status": "unreviewed",
    "confidence_basis": ["model-recall-only"],
    "volatility": "fast",
}


def errors_for(**overrides):
    data = dict(BASE)
    for key, value in overrides.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return validate(data)


class TestValidBaseline(unittest.TestCase):
    def test_a_well_formed_explainer_passes(self):
        self.assertEqual(errors_for(), [])


class TestRequiredFields(unittest.TestCase):
    def test_missing_created_at_is_rejected(self):
        self.assertTrue(any("created_at" in e for e in errors_for(created_at=None)))

    def test_missing_creating_tool_is_rejected(self):
        self.assertTrue(any("created_by_tool" in e for e in errors_for(created_by_tool=None)))

    def test_missing_volatility_is_rejected(self):
        """volatility drives the computed shelf life, so it cannot be defaulted away."""
        self.assertTrue(any("volatility" in e for e in errors_for(volatility=None)))


class TestTimestamps(unittest.TestCase):
    def test_date_without_time_is_rejected(self):
        """format: date-time is a silent no-op here, so this must be a pattern."""
        self.assertTrue(any("created_at" in e for e in errors_for(created_at="2026-08-14")))

    def test_timestamp_without_timezone_offset_is_rejected(self):
        problems = errors_for(created_at="2026-08-14T06:12:00")
        self.assertTrue(any("created_at" in e for e in problems))

    def test_utc_z_suffix_is_accepted(self):
        self.assertEqual(errors_for(created_at="2026-08-14T06:12:00Z", updated_at="2026-08-14T06:12:00Z"), [])


class TestReviewLifecycle(unittest.TestCase):
    def test_verified_requires_a_reviewer(self):
        problems = errors_for(review_status="verified")
        self.assertTrue(any("review_reviewer" in e for e in problems))

    def test_verified_by_an_agent_is_rejected(self):
        """The premise of the whole system: an agent cannot self-promote."""
        problems = errors_for(
            review_status="verified",
            review_reviewer="gpt-5",
            review_reviewer_kind="agent",
            review_reviewed_at="2026-08-14T06:12:00-07:00",
        )
        self.assertTrue(any("human" in e for e in problems))

    def test_verified_by_a_human_is_accepted(self):
        self.assertEqual(
            errors_for(
                review_status="verified",
                review_reviewer="chris",
                review_reviewer_kind="human",
                review_reviewed_at="2026-08-14T06:12:00-07:00",
            ),
            [],
        )

    def test_reviewed_also_requires_a_reviewer(self):
        problems = errors_for(review_status="reviewed")
        self.assertTrue(any("review_reviewer" in e for e in problems))

    def test_unknown_review_status_is_rejected(self):
        self.assertTrue(any("review_status" in e for e in errors_for(review_status="approved")))


class TestConfidenceBasis(unittest.TestCase):
    def test_claiming_a_citation_requires_sources(self):
        problems = errors_for(confidence_basis=["primary-source-cited"])
        self.assertTrue(any("sources" in e for e in problems))

    def test_claiming_a_citation_with_sources_is_accepted(self):
        self.assertEqual(
            errors_for(
                confidence_basis=["primary-source-cited"],
                sources=["https://kafka.apache.org/documentation/"],
            ),
            [],
        )

    def test_unknown_basis_value_is_rejected(self):
        self.assertTrue(any("confidence_basis" in e for e in errors_for(confidence_basis=["vibes"])))

    def test_empty_basis_is_rejected(self):
        self.assertTrue(any("confidence_basis" in e for e in errors_for(confidence_basis=[])))

    def test_source_must_be_a_url_not_prose(self):
        """format: uri is a silent no-op here too, so this must be a pattern."""
        problems = errors_for(
            confidence_basis=["primary-source-cited"],
            sources=["the Kafka docs, probably"],
        )
        self.assertTrue(any("sources" in e for e in problems))


class TestPerTypeExtensions(unittest.TestCase):
    def test_diagram_requires_notation_and_kind(self):
        problems = errors_for(type="diagram")
        self.assertTrue(any("diagram_notation" in e for e in problems))
        self.assertTrue(any("diagram_kind" in e for e in problems))

    def test_c4_diagram_requires_level_and_subject_system(self):
        """C4 levels only mean something for C4 diagrams."""
        problems = errors_for(type="diagram", diagram_notation="mermaid", diagram_kind="c4")
        self.assertTrue(any("c4_level" in e for e in problems))
        self.assertTrue(any("subject_system" in e for e in problems))

    def test_c4_diagram_with_its_extension_fields_is_accepted(self):
        self.assertEqual(
            errors_for(
                type="diagram",
                diagram_notation="mermaid",
                diagram_kind="c4",
                c4_level="container",
                subject_system="acme-booking",
            ),
            [],
        )

    def test_sequence_diagram_does_not_require_a_c4_level(self):
        self.assertEqual(
            errors_for(type="diagram", diagram_notation="mermaid", diagram_kind="sequence"),
            [],
        )

    def test_snippet_requires_language_and_validated_version(self):
        problems = errors_for(type="snippet")
        self.assertTrue(any("lang" in e for e in problems))

    def test_snippet_with_its_extension_fields_is_accepted(self):
        self.assertEqual(
            errors_for(type="snippet", lang="python", lang_version="3.12"),
            [],
        )

    def test_explainer_does_not_require_diagram_fields(self):
        self.assertEqual(errors_for(), [])

    def test_unknown_type_is_rejected(self):
        self.assertTrue(any("type" in e for e in errors_for(type="blogpost")))


class TestUnknownFields(unittest.TestCase):
    def test_unknown_field_is_rejected_so_typos_do_not_pass_silently(self):
        """`review_stat: verified` must fail loudly, not be ignored."""
        problems = errors_for(review_stat="verified")
        self.assertTrue(any("review_stat" in e for e in problems))


if __name__ == "__main__":
    unittest.main()
