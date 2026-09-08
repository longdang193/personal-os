import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_runtime_surface as generator


SKILL_PATH = ROOT / ".agents" / "skills" / "skill-daily-planner" / "SKILL.md"


class DailyPlannerSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")

    def test_frontmatter_and_workflow_sections_exist(self):
        self.assertTrue(self.skill.startswith("---\n"))
        self.assertIn("name: skill-daily-planner", self.skill)
        self.assertIn("description:", self.skill)
        for section in ("## Inputs", "## SSOT Layout", "## Task Contract", "## Commands", "## Authorization"):
            self.assertIn(section, self.skill)

    def test_ssot_and_safe_write_contract_is_explicit(self):
        for phrase in (
            "only durable task and planning state",
            "Preserve all content outside markers",
            "Repeating the same plan must replace one block",
            "never claim a write without result evidence",
            "ask when identity is unclear",
        ):
            self.assertIn(phrase, self.skill)

        self.assertEqual(self.skill.count("<!-- daily-planner:managed:start -->"), 2)
        self.assertEqual(self.skill.count("<!-- daily-planner:managed:end -->"), 2)

    def test_skill_has_no_second_store_or_runtime_install_command(self):
        self.assertIn("Do not create", self.skill)
        self.assertIn("runtime memory, `~/planner/`", self.skill)
        for forbidden in ("openclaw skills install", "api_key", "access_token"):
            self.assertNotIn(forbidden, self.skill.lower())

        self.assertIsNone(re.search(r"[A-Za-z]:\\Users\\|/Users/|/home/", self.skill))

    def test_generated_openclaw_skill_matches_source_and_nanobot_stays_relay_only(self):
        generated_path = ROOT / "generated_runtime" / "openclaw" / "skills" / "skill-daily-planner" / "SKILL.md"
        self.assertEqual(generated_path.read_text(encoding="utf-8"), self.skill)

        nanobot_path = ROOT / "generated_runtime" / "nanobot" / "skills" / "skill-daily-planner" / "SKILL.md"
        self.assertFalse(nanobot_path.exists())

        expected = generator.output_files(ROOT, runtime="openclaw")
        self.assertEqual(expected[generated_path], self.skill.encode())


if __name__ == "__main__":
    unittest.main()
