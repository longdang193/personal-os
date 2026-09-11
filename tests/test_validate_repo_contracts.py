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

    def test_tool_registry_validates_personal_cos_launch_contract(self):
        registry = {
            "version": 1,
            "capabilities": [],
            "tools": [{
                "id": "qmd",
                "domains": ["knowledge"],
                "capabilities": [],
                "expose_to": ["personal-cos"],
                "launch_kind": "command",
                "command": "qmd",
                "args": "mcp",
            }],
        }

        issues = validator.tool_registry_issues(registry)

        self.assertIn("tool qmd command launch args must be a list of strings", issues)

        registry["tools"][0]["args"] = ["mcp"]
        self.assertEqual(validator.tool_registry_issues(registry), [])

    def test_mail_skill_defines_read_only_digest_mode(self):
        skill = (ROOT / ".agents" / "skills" / "skill-mail-management" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("skill-mail-management` in digest mode", skill)
        self.assertIn("Keep digest mode read-only", skill)
        self.assertIn("Fetch metadata first", skill)

    def test_mail_auth_recovery_preserves_calendar_scope(self):
        skill = (ROOT / ".agents" / "skills" / "skill-mail-management" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Treat `mail.search` status `partial` as incomplete coverage", skill)
        self.assertIn("Never invent OAuth URLs, localhost ports, listener commands", skill)
        self.assertIn("this bot cannot restart provider authentication", skill)
        self.assertIn("registry-backed `scripts/check_google_auth.ps1` preflight", skill)
        self.assertIn("Do not invent provider login commands", skill)
        self.assertIn("registry-backed preflight locally", skill)
        self.assertNotIn("verified Gmail recovery command", skill)

    def test_bot_startup_uses_google_auth_preflight(self):
        helper = (ROOT / "scripts" / "check_google_auth.ps1").read_text(encoding="utf-8")
        for script_name in ("start_nanobot.ps1", "start_openclaw.ps1"):
            script = (ROOT / "scripts" / script_name).read_text(encoding="utf-8")
            self.assertIn("check_google_auth.ps1", script)
        self.assertIn("status_args", helper)
        self.assertIn("token_valid", helper)
        self.assertIn("read_google_auth_profile.py", helper)
        self.assertNotIn("gmail.readonly", helper)

    def test_auth_repair_guidance_separates_scopes(self):
        helper = (ROOT / "scripts" / "check_google_auth.ps1").read_text(encoding="utf-8")
        self.assertIn('Write-Output "  `$scopes = @("', helper)
        self.assertIn("foreach ($scope in @($profile.scopes))", helper)
        self.assertIn('Write-Output "    \'$scope\'"', helper)
        self.assertIn("--scopes (`$scopes -join ',')", helper)
        self.assertNotIn('$scopes = (@($profile.scopes) -join ",")', helper)

    def test_student_mail_provider_is_read_only(self):
        skill = (ROOT / ".agents" / "skills" / "skill-mail-management" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("The runtime tool exposes only `mail.search` and `mail.read`", skill)
        self.assertNotIn("himalaya_mail", skill)
        self.assertIn("Respect the registered tool's `read_only = true` boundary", skill)

    def test_frontend_registry_requires_edge_hook_and_known_roles(self):
        registry = {
            "version": 1,
            "transport": "local-process",
            "edge_protocol": "personal.edge.v1",
            "dispatch_protocol": "personal.dispatch.v1",
            "event_protocol": "personal.event.v1",
            "owner_principal": "owner",
            "frontends": [{
                "id": "nanobot",
                "runtime": "nanobot",
                "role": "edge-relay",
                "token_env": "NANOBOT_TELEGRAM_BOT_TOKEN",
            }],
        }
        issues = validator.frontend_registry_issues(registry)
        self.assertIn("frontend nanobot needs module:callable pre_agent_hook", issues)

    def test_project_registry_rejects_paths(self):
        registry = {
            "version": 1,
            "projects": [{
                "id": "demo",
                "root_env": "DEMO_ROOT",
                "root": "C:/secret",
                "access_modes": ["read"],
            }],
        }
        self.assertIn("project demo must not store root", validator.project_registry_issues(registry))

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
        self.assertEqual(google_workspace["domains"], ["calendar"])
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

    def test_knowledge_and_web_search_are_read_only_external_capabilities(self):
        registry = tomllib.loads((ROOT / "repo_config" / "tool_registry.toml").read_text(encoding="utf-8"))
        qmd = next(tool for tool in registry["tools"] if tool["id"] == "qmd")
        searxng = next(tool for tool in registry["tools"] if tool["id"] == "searxng")

        self.assertIn("knowledge.search", registry["capabilities"])
        self.assertIn("web.search", registry["capabilities"])
        self.assertEqual(qmd["capabilities"], ["knowledge.search"])
        self.assertEqual(qmd["status"], "external")
        self.assertTrue(qmd["read_only"])
        self.assertEqual(searxng["capabilities"], ["web.search"])
        self.assertEqual(searxng["status"], "external")
        self.assertTrue(searxng["read_only"])

    def test_protected_paths_cannot_be_tracked(self):
        manifest = json.loads(
            (ROOT / "repo_config" / "runtime_surface_manifest.json").read_text(encoding="utf-8")
        )

        issues = validator.protected_path_issues(manifest, ["README.md", "MEMORY.md", "memory/note.md"])

        self.assertEqual(issues, ["MEMORY.md", "memory/note.md"])

    def test_manifest_keeps_shared_state_ownership_central(self):
        manifest = json.loads(
            (ROOT / "repo_config" / "runtime_surface_manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["ownership"]["policy"], "personal-os")
        self.assertEqual(manifest["ownership"]["memory"], "runtime-local")
        self.assertEqual(manifest["ownership"]["scheduler"], "personal-os")
        self.assertEqual(manifest["ownership"]["sessions"], "runtime")
        self.assertEqual(manifest["ownership"]["credentials"], "provider")

    def test_manifest_rejects_path_traversal(self):
        manifest = {
            "version": 1,
            "protectedPaths": ["../MEMORY.md"],
        }

        issues = validator.manifest_issues(manifest)

        self.assertIn("protectedPaths contains unsafe path: ../MEMORY.md", issues)

    def test_manifest_cannot_remove_required_protected_paths(self):
        manifest = {
            "version": 1,
            "protectedPaths": ["MEMORY.md"],
        }

        issues = validator.manifest_issues(manifest)

        self.assertIn("manifest missing required protected path: USER.md", issues)

    def test_current_repo_contracts_pass(self):
        self.assertEqual(validator.validate_repo(ROOT), [])


if __name__ == "__main__":
    unittest.main()
