import json
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_openclaw_surface as generator
import validate_repo_contracts as validator


class ValidateRepoContractsTests(unittest.TestCase):
    def test_sync_reports_and_removes_deleted_generated_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            copy_root = Path(directory) / "repo"
            shutil.copytree(ROOT, copy_root, ignore=shutil.ignore_patterns(".git", ".serena", "__pycache__"))
            shutil.rmtree(copy_root / ".agents" / "skills" / "skill-mail-management")

            drift = generator.sync_repo(copy_root, check=True)

            stale_path = "generated_runtime/openclaw/skills/skill-mail-management/SKILL.md"
            self.assertIn(stale_path, drift)
            generator.sync_repo(copy_root, check=False)
            self.assertFalse((copy_root / stale_path).exists())

    def test_tool_registry_rejects_duplicate_ids_and_unknown_capabilities(self):
        registry = {
            "version": 1,
            "capabilities": ["mail.read"],
            "tools": [
                {"id": "mail", "domains": ["mail"], "capabilities": ["mail.read"]},
                {"id": "mail", "domains": ["mail"], "capabilities": ["mail.send"]},
            ],
            "accounts": [{"id": "personal", "domain": "mail", "tool": "missing"}],
        }

        issues = validator.tool_registry_issues(registry)

        self.assertIn("tool IDs must be unique", issues)
        self.assertIn("tool mail references unknown capability: mail.send", issues)
        self.assertIn("account personal references unknown tool: missing", issues)

    def test_mail_skill_defines_read_only_digest_mode(self):
        skill = (ROOT / ".agents" / "skills" / "skill-mail-management" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("/skill skill-mail-management digest", skill)
        self.assertIn("Keep digest mode read-only", skill)
        self.assertIn("Fetch metadata first", skill)

    def test_student_mail_provider_is_read_only(self):
        skill = (ROOT / ".agents" / "skills" / "skill-mail-management" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("registered `mail.read` and `mail.search` capabilities", skill)
        self.assertNotIn("himalaya_mail", skill)
        self.assertIn("Respect the registered tool's `read_only = true` boundary", skill)

    def test_cross_skill_handoff_contracts_preserve_boundaries(self):
        mail = (ROOT / ".agents" / "skills" / "skill-mail-management" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        chief_of_staff = (ROOT / ".agents" / "skills" / "skill-personal-chief-of-staff" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        routing = (ROOT / ".agents" / "skills" / "skill-personal-routing" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Use session-scoped IDs", mail)
        self.assertIn("never call another skill directly", mail)
        self.assertIn("Preview and confirm batch", chief_of_staff)
        self.assertIn("project acceptance and evidence requirements", routing)
        self.assertNotIn("acceptance evidence", routing)

    def test_content_update_contract_uses_provider_neutral_boundaries(self):
        registry = tomllib.loads((ROOT / "repo_config" / "tool_registry.toml").read_text(encoding="utf-8"))
        google_workspace = next(tool for tool in registry["tools"] if tool["id"] == "google-workspace")
        content_poller = next(tool for tool in registry["tools"] if tool["id"] == "content-poller")
        skill = (ROOT / ".agents" / "skills" / "skill-update-review" / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "operating_system" / "rules" / "content-update-contract.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("content.watch", registry["capabilities"])
        self.assertEqual(google_workspace["domains"], ["mail", "calendar"])
        self.assertEqual(content_poller["domains"], ["content"])
        self.assertEqual(content_poller["capabilities"], ["content.watch"])
        self.assertEqual(content_poller["status"], "runtime")
        self.assertTrue(content_poller["read_only"])
        self.assertNotIn("apify", {tool["id"] for tool in registry["tools"]})
        self.assertNotIn("rss-poller", {tool["id"] for tool in registry["tools"]})
        self.assertIn("content.update.v1", skill)
        self.assertIn("untrusted data", skill)
        self.assertIn("target_domain: project", skill)
        self.assertNotIn("target_domain: personal-routing", skill)
        self.assertIn("content.update.v1", contract)

    def test_protected_paths_cannot_be_tracked(self):
        manifest = json.loads(
            (ROOT / "repo_config" / "runtime_surface_manifest.json").read_text(encoding="utf-8")
        )

        issues = validator.protected_path_issues(manifest, ["README.md", "MEMORY.md", "memory/note.md"])

        self.assertEqual(issues, ["MEMORY.md", "memory/note.md"])

    def test_manifest_rejects_path_traversal(self):
        manifest = {
            "runtime": "openclaw",
            "generatedRoot": "generated_runtime/openclaw",
            "managedFiles": ["../MEMORY.md"],
            "managedDirectories": ["skills"],
            "protectedPaths": ["MEMORY.md"],
        }

        issues = validator.manifest_issues(manifest)

        self.assertIn("managedFiles contains unsafe path: ../MEMORY.md", issues)

    def test_manifest_cannot_remove_required_protected_paths(self):
        manifest = {
            "runtime": "openclaw",
            "generatedRoot": "generated_runtime/openclaw",
            "managedFiles": ["AGENTS.md"],
            "managedDirectories": ["skills"],
            "protectedPaths": ["MEMORY.md"],
        }

        issues = validator.manifest_issues(manifest)

        self.assertIn("manifest missing required protected path: USER.md", issues)

    def test_current_repo_contracts_pass(self):
        self.assertEqual(validator.validate_repo(ROOT), [])


if __name__ == "__main__":
    unittest.main()
