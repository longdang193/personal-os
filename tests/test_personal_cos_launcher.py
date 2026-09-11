import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import personal_cos_launcher as launcher


class PersonalCosLauncherTests(unittest.TestCase):
    def test_content_watch_context_preserves_events(self):
        event = {"schema": "content.update.v1", "source_id": "instagram-ispofficeovgu"}
        process = SimpleNamespace(returncode=0, stdout=json.dumps(event) + "\n", stderr="")
        with patch.object(launcher.subprocess, "run", return_value=process) as run:
            context = launcher.content_watch_context("Give updates from tracked profiles")

        self.assertIn('"status": "fresh"', context)
        self.assertIn("instagram-ispofficeovgu", context)
        self.assertEqual(run.call_args.kwargs["cwd"], launcher.ROOT)
        self.assertEqual(run.call_args.kwargs["timeout"], launcher.CONTENT_POLLER_TIMEOUT)

    def test_content_watch_context_reports_partial_failure_with_events(self):
        event = {"schema": "content.update.v1", "source_id": "ovgu-fww-news"}
        process = SimpleNamespace(returncode=1, stdout=json.dumps(event) + "\n", stderr="Instagram failed")
        with patch.object(launcher.subprocess, "run", return_value=process):
            context = launcher.content_watch_context("Give social updates from tracked websites")

        self.assertIn('"status": "failed"', context)
        self.assertIn("ovgu-fww-news", context)
        self.assertIn("Instagram failed", context)

    def test_session_context_uses_versioned_ttl_and_atomic_json(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher, "SESSION_DIR", Path(directory)):
            launcher.save_session_context("telegram:7", "hello", "world", now=now)
            path = launcher._session_path("telegram:7")
            self.assertIsNotNone(path)
            document = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(document["version"], launcher.SESSION_FORMAT_VERSION)
            self.assertEqual(document["turns"], [{"user": "hello", "assistant": "world"}])
            self.assertEqual(launcher.load_session_context("telegram:7", now=now + launcher.SESSION_TTL), document["turns"])
            self.assertEqual(launcher.load_session_context("telegram:7", now=now + launcher.SESSION_TTL + timedelta(seconds=1)), [])
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_session_context_rejects_invalid_and_far_future_timestamps(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher, "SESSION_DIR", Path(directory)):
            path = launcher._session_path("telegram:7")
            path.parent.mkdir(parents=True, exist_ok=True)
            for updated_at in ("invalid", (now + launcher.SESSION_FUTURE_TOLERANCE + timedelta(seconds=1)).isoformat()):
                path.write_text(
                    json.dumps({"version": launcher.SESSION_FORMAT_VERSION, "updated_at": updated_at, "turns": []}),
                    encoding="utf-8",
                )
                self.assertEqual(launcher.load_session_context("telegram:7", now=now), [])

    def test_legacy_session_context_uses_file_time_and_migrates_on_save(self):
        now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher, "SESSION_DIR", Path(directory)):
            path = launcher._session_path("telegram:7")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps([{"user": "old", "assistant": "reply"}]), encoding="utf-8")
            timestamp = (now - launcher.SESSION_TTL).timestamp()
            os.utime(path, (timestamp, timestamp))
            self.assertEqual(launcher.load_session_context("telegram:7", now=now), [{"user": "old", "assistant": "reply"}])

            launcher.save_session_context("telegram:7", "new", "answer", now=now)
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["version"], launcher.SESSION_FORMAT_VERSION)
            self.assertEqual(document["turns"][-1], {"user": "new", "assistant": "answer"})

    def test_session_context_cleans_temp_file_when_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher, "SESSION_DIR", Path(directory)):
            with patch.object(launcher.os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    launcher.save_session_context("telegram:7", "hello", "world")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

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

    def test_emit_keeps_unicode_safe_across_windows_console_transport(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        with patch.object(launcher.sys, "stdout", stream):
            launcher.emit(launcher.event("request-1", 2, "completed", "Today – focus 📅"))
            stream.flush()

        wire = raw.getvalue().decode("utf-8")
        self.assertEqual(json.loads(wire)["payload"]["text"], "Today – focus 📅")


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
        self.assertIn("--sandbox", command)
        self.assertIn("read-only", command)
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")

    def test_run_injects_fresh_content_context_before_cos_turn(self):
        process = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}),
            stderr="",
        )
        envelope = {
            "version": "personal.edge.v1",
            "request_id": "request-1",
            "text": "Give updates from tracked profiles",
            "repository_id": "demo",
            "access_mode": "read",
        }
        with (
            patch.object(launcher, "project_roots", return_value={"demo": ("DEMO_ROOT", {"read"})}),
            patch.dict(launcher.os.environ, {"DEMO_ROOT": str(ROOT)}, clear=False),
            patch.object(launcher, "content_watch_context", return_value="fresh source evidence"),
            patch.object(launcher.subprocess, "run", return_value=process) as run,
        ):
            with patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(launcher.run(envelope), 0)

        self.assertIn("fresh source evidence", run.call_args.kwargs["input"])

    def test_codex_command_disables_configured_mcp_servers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_home = Path(temp_dir)
            (config_home / "config.toml").write_text(
                '[mcp_servers.mail]\ncommand = "mail"\n\n[mcp_servers.chrome-devtools]\ncommand = "chrome"\n',
                encoding="utf-8",
            )
            tool_registry = config_home / "tool_registry.toml"
            tool_registry.write_text(
                '[[tools]]\nid = "mail-runtime"\nstatus = "runtime"\nexpose_to = ["personal-cos"]\nlaunch_kind = "python-script"\nscript = "scripts/mail_mcp_server.py"\n',
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
            f'mcp_servers.mail={{command={json.dumps(sys.executable)},args={json.dumps(["-u", str((ROOT / "scripts/mail_mcp_server.py").resolve())])},cwd={json.dumps(str(ROOT))},enabled=true}}',
            command,
        )
        self.assertEqual(command[-3:], ["--cd", str(ROOT), "-"])

    def test_codex_command_exposes_structured_qmd_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "tool_registry.toml"
            registry.write_text(
                '[[tools]]\nid = "qmd"\nexpose_to = ["personal-cos"]\nlaunch_kind = "command"\ncommand = "qmd"\nargs = ["mcp"]\n',
                encoding="utf-8",
            )
            with patch.object(launcher, "TOOL_REGISTRY_PATH", registry):
                command = launcher.codex_command(ROOT)
        self.assertIn(
            f'mcp_servers.qmd={{command="qmd",args=["mcp"],cwd={json.dumps(str(ROOT))},enabled=true}}',
            command,
        )

    def test_codex_command_ignores_undeclared_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "tool_registry.toml"
            registry.write_text(
                '[[tools]]\nid = "qmd"\nlaunch_kind = "command"\ncommand = "qmd"\nargs = ["mcp"]\n',
                encoding="utf-8",
            )
            with patch.object(launcher, "TOOL_REGISTRY_PATH", registry):
                command = launcher.codex_command(ROOT)
        self.assertFalse(any("mcp_servers.qmd=" in value for value in command))

    def test_codex_command_read_access_disables_writes(self):
        with patch.object(launcher, "configured_obsidian_vault", return_value=Path("C:/vault")):
            command = launcher.codex_command(ROOT, access_mode="read")
        sandbox_index = command.index("--sandbox")
        self.assertEqual(command[sandbox_index + 1], "read-only")
        self.assertNotIn("--add-dir", command)

    def test_runtime_skill_is_injected_only_when_explicitly_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_dir = Path(temp_dir) / "new-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("runtime skill contract", encoding="utf-8")
            envelope = {"version": "personal.edge.v1", "request_id": "request-1", "text": "Do you have skill new-skill?"}
            with patch.dict(launcher.os.environ, {launcher.RUNTIME_SKILL_ROOT_ENV: temp_dir}, clear=False):
                value = launcher.codex_input(envelope)
                command = launcher.codex_command(ROOT, access_mode="read", runtime_skill_dir=launcher.requested_runtime_skill_path(envelope["text"]))

        self.assertIn("runtime skill contract", value)
        self.assertIn(str(skill_dir), value)
        self.assertEqual(command[command.index("--add-dir") + 1], str(skill_dir))

    def test_runtime_skill_request_supports_slash_commands(self):
        self.assertEqual(launcher.requested_runtime_skill_name("/new-skill AI"), "new-skill")
        self.assertIsNone(launcher.requested_runtime_skill_name("research last 30 days"))

    def test_codex_input_points_to_canonical_skill_root(self):
        envelope = {"version": "personal.edge.v1", "request_id": "request-1", "text": "hello"}
        with patch.object(launcher, "load_env", return_value={"OBSIDIAN_VAULT": str(ROOT)}):
            value = launcher.codex_input(envelope)
        self.assertIn(str(launcher.SKILL_ROOT), value)
        self.assertIn("do not probe user-global skill paths", value)
        self.assertIn(f"Obsidian vault root for planner writes is exactly {ROOT}", value)
        self.assertIn("never use repository root, current working directory, active file path", value)
        self.assertIn("create only `<vault>\\Daily`", value)
        self.assertIn("<vault>\\Daily\\YYYY-MM-DD.md` for captured tasks", value)
        self.assertIn('"request_id": "request-1"', value)

    def test_codex_input_includes_canonical_daily_planner_skill(self):
        envelope = {"version": "personal.edge.v1", "request_id": "request-1", "text": "Add to my plan"}
        with patch.object(launcher, "load_env", return_value={}):
            value = launcher.codex_input(envelope)
        skill = (ROOT / ".agents" / "skills" / "skill-daily-planner" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Mandatory applicable skill: skill-daily-planner", value)
        self.assertIn(skill, value)
        self.assertIn("Location reporting boundary: never report a path from prior context", value)
        self.assertIn("Daily/YYYY-MM-DD.md` for captured tasks", value)
        self.assertIn("canonical capture or daily-plan paths only as references", value)

    def test_codex_input_includes_runtime_conversation_context(self):
        envelope = {
            "version": "personal.edge.v1",
            "request_id": "request-1",
            "conversation_id": "telegram:7",
            "text": "Google calendar",
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher, "SESSION_DIR", Path(directory)):
            launcher.save_session_context(
                "telegram:7",
                "This task: need to learn German 📅 2026-09-08",
                "Need calendar details.",
            )
            value = launcher.codex_input(envelope)

        self.assertIn("This task: need to learn German 📅 2026-09-08", value)
        self.assertIn("Need calendar details.", value)

    def test_run_persists_completed_context_for_follow_up(self):
        stdout = json.dumps({
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "Need calendar details."},
        })
        process = SimpleNamespace(returncode=0, stdout=stdout, stderr="")
        envelope = {
            "version": "personal.edge.v1",
            "request_id": "request-1",
            "conversation_id": "telegram:7",
            "text": "This task: need to learn German 📅 2026-09-08",
            "repository_id": "demo",
            "access_mode": "write",
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(
            launcher, "SESSION_DIR", Path(directory)
        ), patch.object(
            launcher, "project_roots", return_value={"demo": ("DEMO_ROOT", {"write"})}
        ), patch.dict(
            launcher.os.environ, {"DEMO_ROOT": str(ROOT)}, clear=False
        ), patch.object(launcher.subprocess, "run", return_value=process):
            with patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(launcher.run(envelope), 0)

            context = launcher.load_session_context("telegram:7")

        self.assertEqual(context[-1]["user"], envelope["text"])
        self.assertEqual(context[-1]["assistant"], "Need calendar details.")

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

    def test_failed_write_turn_does_not_persist_session_context(self):
        process = SimpleNamespace(returncode=1, stdout=None, stderr="failed")
        envelope = {
            "version": "personal.edge.v1",
            "request_id": "request-1",
            "conversation_id": "telegram:7",
            "text": "write",
            "repository_id": "demo",
            "access_mode": "write",
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(
            launcher, "SESSION_DIR", Path(directory)
        ), patch.object(
            launcher, "project_roots", return_value={"demo": ("DEMO_ROOT", {"write"})}
        ), patch.dict(
            launcher.os.environ, {"DEMO_ROOT": str(ROOT)}, clear=False
        ), patch.object(launcher.subprocess, "run", return_value=process):
            with patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(launcher.run(envelope), 0)
            self.assertEqual(launcher.load_session_context("telegram:7"), [])

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
