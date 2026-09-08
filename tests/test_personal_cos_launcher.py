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
        command = run.call_args.args[0]
        self.assertEqual(
            command[:8],
            [
                "codex",
                "exec",
                "--ephemeral",
                "--json",
                "-c",
                'model="combo-normal"',
                "-c",
                'model_reasoning_effort="low"',
            ],
        )
        self.assertEqual(command[-1], "-")
        self.assertIn(str(ROOT), command)
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")

    def test_codex_command_disables_configured_mcp_servers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_home = Path(temp_dir)
            (config_home / "config.toml").write_text(
                '[mcp_servers.mail]\ncommand = "mail"\n\n[mcp_servers.chrome-devtools]\ncommand = "chrome"\n',
                encoding="utf-8",
            )
            tool_registry = config_home / "tool_registry.toml"
            tool_registry.write_text(
                '[[tools]]\nid = "mail-runtime"\nstatus = "runtime"\ncommand = "python scripts/mail_mcp_server.py"\n',
                encoding="utf-8",
            )
            with patch.dict(launcher.os.environ, {"CODEX_HOME": str(config_home)}, clear=False):
                with patch.object(launcher, "TOOL_REGISTRY_PATH", tool_registry):
                    command = launcher.codex_command(ROOT)
        self.assertEqual(
            command[:8],
            [
                "codex",
                "exec",
                "--ephemeral",
                "--json",
                "-c",
                'model="combo-normal"',
                "-c",
                'model_reasoning_effort="low"',
            ],
        )
        self.assertIn("mcp_servers.mail.enabled=false", command)
        self.assertIn(
            f'mcp_servers.mail={{command={json.dumps(sys.executable)},args=["-u",{json.dumps(str((ROOT / "scripts/mail_mcp_server.py").resolve()))}],cwd={json.dumps(str(ROOT))},enabled=true}}',
            command,
        )
        self.assertEqual(command[-3:], ["--cd", str(ROOT), "-"])

    def test_codex_input_points_to_canonical_skill_root(self):
        envelope = {"version": "personal.edge.v1", "request_id": "request-1", "text": "hello"}
        with patch.object(launcher, "load_env", return_value={"OBSIDIAN_VAULT": str(ROOT)}):
            value = launcher.codex_input(envelope)
        self.assertIn(str(launcher.SKILL_ROOT), value)
        self.assertIn("do not probe user-global skill paths", value)
        self.assertIn(f"Obsidian vault root for planner writes is exactly {ROOT}", value)
        self.assertIn("never use repository root, current working directory, active file path", value)
        self.assertIn("create only `<vault>\\Planner`", value)
        self.assertIn('"request_id": "request-1"', value)

    def test_codex_input_disables_planner_writes_without_vault(self):
        envelope = {"version": "personal.edge.v1", "request_id": "request-1", "text": "Add to my plan"}
        with patch.dict(launcher.os.environ, {"OBSIDIAN_VAULT": ""}, clear=False), patch.object(launcher, "load_env", return_value={}):
            value = launcher.codex_input(envelope)
        self.assertIn("Obsidian vault root is unavailable; planner must not write files.", value)

    def test_run_passes_configured_obsidian_vault_to_cos(self):
        process = SimpleNamespace(returncode=0, stdout='{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}\n', stderr="")
        envelope = {
            "version": "personal.edge.v1",
            "request_id": "request-1",
            "text": "Add to my plan",
            "repository_id": "demo",
            "access_mode": "read",
        }
        vault = ROOT
        with (
            patch.object(launcher, "project_roots", return_value={"demo": ("DEMO_ROOT", {"read"})}),
            patch.dict(launcher.os.environ, {"DEMO_ROOT": str(ROOT)}, clear=False),
            patch.object(launcher, "load_env", return_value={"OBSIDIAN_VAULT": str(vault)}),
            patch.object(launcher.subprocess, "run", return_value=process) as run,
        ):
            with patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(launcher.run(envelope), 0)
        self.assertEqual(run.call_args.kwargs["env"]["OBSIDIAN_VAULT"], str(vault))

    def test_run_reports_failure_when_codex_output_is_unavailable(self):
        process = SimpleNamespace(returncode=1, stdout=None, stderr=None)
        envelope = {
            "version": "personal.edge.v1",
            "request_id": "request-1",
            "text": "inspect",
            "repository_id": "demo",
            "access_mode": "read",
        }
        with patch.object(launcher, "project_roots", return_value={"demo": ("DEMO_ROOT", {"read"})}), patch.dict(launcher.os.environ, {"DEMO_ROOT": str(ROOT)}, clear=False), patch.object(launcher.subprocess, "run", return_value=process):
            with patch("sys.stdout", new_callable=io.StringIO) as output:
                self.assertEqual(launcher.run(envelope), 0)
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(events[-1]["type"], "failed")
        self.assertEqual(events[-1]["payload"]["text"], "codex exited with 1")

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
