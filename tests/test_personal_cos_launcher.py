import io
import json
import os
import tempfile
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import personal_cos_launcher as launcher


class PersonalCosLauncherTests(unittest.TestCase):
    def test_load_env_does_not_mutate_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("UNRELATED_SECRET=secret\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("UNRELATED_SECRET", None)
                values = launcher.load_env(env_path)
                self.assertEqual(values["UNRELATED_SECRET"], "secret")
                self.assertNotIn("UNRELATED_SECRET", os.environ)

    def test_event_shape(self):
        result = launcher.event("request-1", 2, "progress", "running")
        self.assertEqual(result["version"], "personal.event.v1")
        self.assertEqual(result["request_id"], "request-1")
        self.assertEqual(result["sequence"], 2)
        self.assertEqual(result["payload"], {"text": "running"})


    def test_run_emits_events_and_pins_registered_cwd(self):
        stdout = "\n".join([
            json.dumps({"type": "turn.started"}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}),
        ])
        completed = SimpleNamespace(returncode=0, stdout=stdout, stderr="")
        envelope = {
            "version": "personal.edge.v1",
            "request_id": "request-1",
            "text": "inspect",
            "repository_id": "demo",
            "access_mode": "read",
        }
        with patch.object(launcher, "project_roots", return_value={"demo": ("DEMO_ROOT", {"read"})}), patch.dict(launcher.os.environ, {"DEMO_ROOT": str(ROOT)}, clear=False), patch.object(launcher.subprocess, "run", return_value=completed) as run:
            with patch("sys.stdout", new_callable=io.StringIO) as output:
                self.assertEqual(launcher.run(envelope), 0)
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([event["type"] for event in events], ["accepted", "progress", "completed"])
        self.assertEqual(run.call_args.args[0][:4], ["codex", "exec", "--json", "--cd"])
        self.assertEqual(run.call_args.args[0][-1], "-")
        self.assertIn(str(ROOT), run.call_args.args[0])

    def test_resolve_project_root_uses_registry_id_and_rejects_unknown(self):
        with self.subTest("registered"):
            with patch.object(launcher, "project_roots", return_value={"demo": ("DEMO_ROOT", {"read"})}), patch.dict(launcher.os.environ, {"DEMO_ROOT": str(ROOT)}, clear=False):
                project_id, root = launcher.resolve_project_root({"repository_id": "demo", "access_mode": "read"})
            self.assertEqual(project_id, "demo")
            self.assertEqual(root, ROOT.resolve())
        with self.subTest("unknown"):
            with patch.object(launcher, "project_roots", return_value={}):
                with self.assertRaisesRegex(ValueError, "unknown repository_id"):
                    launcher.resolve_project_root({"repository_id": "missing"})


if __name__ == "__main__":
    unittest.main()
