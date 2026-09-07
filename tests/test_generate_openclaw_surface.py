import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_openclaw_surface as generator
import generate_runtime_surface as runtime_generator


class GenerateOpenClawSurfaceTests(unittest.TestCase):
    def test_generated_surface_is_current(self):
        self.assertEqual(generator.sync_repo(ROOT, check=True), [])

    def test_private_paths_are_not_managed(self):
        manifest = json.loads((ROOT / "repo_config" / "runtime_surface_manifest.json").read_text())
        managed = {
            path
            for adapter in runtime_generator.load_adapters(ROOT)
            for path in adapter["managedFiles"] + adapter["managedDirectories"]
        }
        self.assertTrue(set(manifest["protectedPaths"]).isdisjoint(managed))

    def test_all_runtime_surfaces_are_projected_symmetrically(self):
        outputs = runtime_generator.output_files(ROOT)
        self.assertTrue(any("generated_runtime/openclaw/" in path.as_posix() for path in outputs))
        self.assertTrue(any("generated_runtime/nanobot/" in path.as_posix() for path in outputs))
        for name in ("AGENTS.md", "SOUL.md", "IDENTITY.md", "TOOL_REGISTRY.toml"):
            self.assertIn(ROOT / "generated_runtime" / "openclaw" / name, outputs)
            self.assertIn(ROOT / "generated_runtime" / "nanobot" / name, outputs)

    def test_runtime_registry_is_projected(self):
        registry = (ROOT / "generated_runtime" / "openclaw" / "TOOL_REGISTRY.toml").read_text()
        self.assertIn('id = "himalaya"', registry)
        self.assertIn('status = "runtime"', registry)
        self.assertIn('read_only = true', registry)

    def test_nanobot_is_projected_as_edge_only(self):
        identity = (ROOT / "generated_runtime" / "nanobot" / "IDENTITY.md").read_text(encoding="utf-8")
        registry = (ROOT / "generated_runtime" / "nanobot" / "TOOL_REGISTRY.toml").read_text(encoding="utf-8")
        self.assertIn("role: edge-relay", identity)
        self.assertNotIn("Personal CoS", identity)
        self.assertIn("capabilities = []", registry)
        self.assertFalse((ROOT / "generated_runtime" / "nanobot" / "skills").exists())

    def test_memory_routing_policy_stays_with_personal_cos(self):
        expected = (
            "For personal facts, search runtime durable memory and relevant history before `USER.md`.",
            "Treat “I told you before” as an explicit history-search trigger.",
            "Prefer explicit confirmed facts over inferred or template text; report source and confidence when memory is used.",
        )
        soul = (ROOT / "generated_runtime" / "openclaw" / "SOUL.md").read_text(encoding="utf-8")
        for rule in expected:
            self.assertIn(rule, soul)


if __name__ == "__main__":
    unittest.main()
