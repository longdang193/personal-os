import json
import shutil
import sys
import tempfile
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
            shutil.rmtree(copy_root / ".agents" / "skills" / "skill-mail-review")

            drift = generator.sync_repo(copy_root, check=True)

            stale_path = "generated_runtime/openclaw/skills/skill-mail-review/SKILL.md"
            self.assertIn(stale_path, drift)
            generator.sync_repo(copy_root, check=False)
            self.assertFalse((copy_root / stale_path).exists())

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
