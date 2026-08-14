"""The contribution contract must stay true to the code it describes.

AGENTS.md is the only file a foreign AI tool is guaranteed to read. If it drifts
from the templates or the schema, it teaches the wrong thing confidently - so
the drift is a test failure, not a documentation chore.
"""

import pathlib
import unittest

from kbtool.frontmatter import parse

REPO = pathlib.Path(__file__).resolve().parents[1]
CONTENT_TYPES = ("explainer", "diagram", "snippet", "prompt", "note")


def read(relpath):
    return (REPO / relpath).read_text(encoding="utf-8")


class TestTemplates(unittest.TestCase):
    def test_every_content_type_has_a_template(self):
        for kind in CONTENT_TYPES:
            self.assertTrue((REPO / "templates" / f"{kind}.md").exists(), kind)

    def test_every_template_has_parseable_frontmatter(self):
        for kind in CONTENT_TYPES:
            with self.subTest(kind=kind):
                parse(read(f"templates/{kind}.md"))

    def test_every_template_declares_its_own_type(self):
        for kind in CONTENT_TYPES:
            with self.subTest(kind=kind):
                self.assertEqual(parse(read(f"templates/{kind}.md")).data["type"], kind)

    def test_templates_never_offer_a_review_field_for_an_agent_to_fill(self):
        """The template is the strongest prompt in the system: any key present
        will receive a value. Review fields are human-only, so they must be
        absent entirely rather than present-and-blank."""
        for kind in CONTENT_TYPES:
            with self.subTest(kind=kind):
                data = parse(read(f"templates/{kind}.md")).data
                self.assertNotIn("review_reviewer", data)
                self.assertNotIn("review_reviewer_kind", data)
                self.assertNotIn("review_reviewed_at", data)

    def test_templates_default_to_unreviewed(self):
        for kind in CONTENT_TYPES:
            with self.subTest(kind=kind):
                self.assertEqual(
                    parse(read(f"templates/{kind}.md")).data["review_status"], "unreviewed"
                )

    def test_templates_do_not_pre_claim_a_citation_without_sources(self):
        for kind in CONTENT_TYPES:
            with self.subTest(kind=kind):
                basis = parse(read(f"templates/{kind}.md")).data["confidence_basis"]
                self.assertNotIn("primary-source-cited", basis)
                self.assertNotIn("executed-verified", basis)


class TestAgentsContract(unittest.TestCase):
    def test_agents_md_exists(self):
        self.assertTrue((REPO / "AGENTS.md").exists())

    def test_agents_md_embeds_the_explainer_template_byte_identically(self):
        """Two sources of truth drift within a month and then contradict."""
        template = read("templates/explainer.md")

        self.assertIn(template.strip(), read("AGENTS.md"))

    def test_agents_md_names_every_content_type(self):
        contract = read("AGENTS.md")
        for kind in CONTENT_TYPES:
            self.assertIn(kind, contract)

    def test_agents_md_states_that_agents_cannot_set_verified(self):
        contract = read("AGENTS.md").lower()

        self.assertIn("verified", contract)
        self.assertIn("human", contract)

    def test_agents_md_gives_the_check_command(self):
        self.assertIn("tools/kb.py check", read("AGENTS.md"))

    def test_claude_md_mirrors_the_contract(self):
        self.assertTrue((REPO / "CLAUDE.md").exists())
        self.assertIn("AGENTS.md", read("CLAUDE.md"))

    def test_agents_md_is_short_enough_that_an_agent_will_read_it(self):
        lines = len(read("AGENTS.md").splitlines())

        self.assertLess(lines, 200, "contract too long; agents will skim past the rules")


if __name__ == "__main__":
    unittest.main()


class TestContractCoversEveryField(unittest.TestCase):
    """The clean-room test found `prompt_target` in a template but nowhere in
    AGENTS.md, so a foreign agent had to guess its value. Any field a template
    can put in front of a contributor must be explained by the contract."""

    def test_every_template_frontmatter_key_is_mentioned_in_agents_md(self):
        contract = read("AGENTS.md")
        undocumented = set()
        for kind in CONTENT_TYPES:
            for key in parse(read(f"templates/{kind}.md")).data:
                if key not in contract:
                    undocumented.add(key)

        self.assertEqual(
            undocumented, set(),
            f"template fields absent from AGENTS.md: {sorted(undocumented)}",
        )

    def test_contract_states_the_filename_is_the_id_plus_extension(self):
        """'the filename must equal the id' is literally false: the file has .md."""
        self.assertIn(".md", read("AGENTS.md"))
        self.assertNotIn("filename must equal the `id`", read("AGENTS.md"))
