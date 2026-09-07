import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_repo_contracts as validator


class FrontendRegistryTests(unittest.TestCase):
    def test_repository_registries_are_valid(self):
        self.assertEqual(validator._toml_file_issues(ROOT, validator.FRONTEND_REGISTRY_PATH, validator.frontend_registry_issues), [])
        self.assertEqual(validator._toml_file_issues(ROOT, validator.PROJECT_REGISTRY_PATH, validator.project_registry_issues), [])


if __name__ == "__main__":
    unittest.main()
