import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_openclaw_surface as generator


class GenerateOpenClawSurfaceTests(unittest.TestCase):
    def test_generated_surface_is_current(self):
        self.assertEqual(generator.sync_repo(ROOT, check=True), [])

    def test_private_paths_are_not_managed(self):
        manifest = json.loads((ROOT / "repo_config" / "runtime_surface_manifest.json").read_text())
        managed = set(manifest["managedFiles"]) | set(manifest["managedDirectories"])
        self.assertTrue(set(manifest["protectedPaths"]).isdisjoint(managed))

    def test_runtime_registry_is_projected(self):
        registry = (ROOT / "generated_runtime" / "openclaw" / "TOOL_REGISTRY.toml").read_text()
        self.assertIn('id = "himalaya"', registry)
        self.assertIn('status = "runtime"', registry)
        self.assertIn('read_only = true', registry)


if __name__ == "__main__":
    unittest.main()
