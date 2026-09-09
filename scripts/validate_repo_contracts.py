"""Validate Personal OS repository contracts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path

import generate_runtime_surface as generator


REQUIRED_MANIFEST_FIELDS = {
    "version",
    "protectedPaths",
}
REQUIRED_PROTECTED_PATHS = {
    "USER.md",
    "MEMORY.md",
    "memory",
    "credentials",
    "sessions",
    "scheduler",
    "cron",
}
REQUIRED_OWNERSHIP = {
    "policy": "personal-os",
    "memory": "runtime-local",
    "scheduler": "personal-os",
    "sessions": "runtime",
    "credentials": "provider",
}
TOOL_REGISTRY_PATH = "repo_config/tool_registry.toml"
FRONTEND_REGISTRY_PATH = "repo_config/frontend_registry.toml"
PROJECT_REGISTRY_PATH = "repo_config/project_registry.toml"
CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9_-]*$")
ENV_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
FRONTEND_ROLES = {"edge-relay", "personal-cos"}
ACCESS_MODES = {"read", "write"}


def manifest_issues(manifest: object) -> list[str]:
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    issues = [
        f"manifest missing field: {field}"
        for field in sorted(REQUIRED_MANIFEST_FIELDS - manifest.keys())
    ]
    ownership = manifest.get("ownership")
    if not isinstance(ownership, dict):
        issues.append("ownership must be an object")
    else:
        for key, expected_owner in REQUIRED_OWNERSHIP.items():
            if ownership.get(key) != expected_owner:
                issues.append(f"ownership {key} must be {expected_owner}")
    protected_values = manifest.get("protectedPaths")
    if not isinstance(protected_values, list):
        issues.append("protectedPaths must be a list")
    else:
        for value in protected_values:
            if not generator.is_safe_manifest_path(value):
                issues.append(f"protectedPaths contains unsafe path: {value}")
    if isinstance(protected_values, list):
        missing = REQUIRED_PROTECTED_PATHS - {path for path in protected_values if isinstance(path, str)}
        issues.extend(f"manifest missing required protected path: {path}" for path in sorted(missing))
    return issues


def protected_path_issues(manifest: dict, tracked_paths: list[str]) -> list[str]:
    protected_paths = manifest.get("protectedPaths", [])
    if not isinstance(protected_paths, list):
        return []
    protected = [
        path.replace("\\", "/").strip("/")
        for path in set(protected_paths) | REQUIRED_PROTECTED_PATHS
        if isinstance(path, str)
    ]
    return sorted(
        path
        for path in tracked_paths
        if any(path == item or path.startswith(f"{item}/") for item in protected)
    )


def tracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "-z"],
        check=True,
        capture_output=True,
    )
    return [path for path in result.stdout.decode().split("\0") if path]


def skill_issues(root: Path) -> list[str]:
    skills_root = root / ".agents" / "skills"
    issues: list[str] = []
    for entry in sorted(skills_root.iterdir()):
        if not entry.is_dir():
            issues.append(f"skill source is not a directory: {entry.name}")
            continue
        skill_file = entry / "SKILL.md"
        if not skill_file.is_file():
            issues.append(f"skill missing SKILL.md: {entry.name}")
            continue
        lines = skill_file.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            issues.append(f"skill missing frontmatter: {entry.name}")
            continue
        try:
            end = lines.index("---", 1)
        except ValueError:
            issues.append(f"skill has unterminated frontmatter: {entry.name}")
            continue
        fields = {
            key.strip(): value.strip()
            for key, value in (line.split(":", 1) for line in lines[1:end] if ":" in line)
        }
        for field in ("name", "description"):
            if not fields.get(field):
                issues.append(f"skill missing {field}: {entry.name}")
        if fields.get("name") and fields["name"] != entry.name:
            issues.append(f"skill name does not match directory: {entry.name}")
    return issues


def tool_registry_issues(registry: object) -> list[str]:
    if not isinstance(registry, dict):
        return ["tool registry must be an object"]
    issues: list[str] = []
    catalog = registry.get("capabilities")
    if not isinstance(catalog, list) or not all(isinstance(value, str) for value in catalog):
        issues.append("tool registry capabilities must be a list of strings")
        catalog = []
    if len(catalog) != len(set(catalog)):
        issues.append("tool registry capabilities must be unique")
    for capability in catalog:
        if not CAPABILITY_PATTERN.fullmatch(capability):
            issues.append(f"tool registry contains invalid capability: {capability}")

    tools = registry.get("tools")
    if not isinstance(tools, list):
        return issues + ["tool registry tools must be a list"]
    tool_ids: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict):
            issues.append("tool registry tool entries must be objects")
            continue
        tool_id = tool.get("id")
        if not isinstance(tool_id, str) or not tool_id:
            issues.append("tool registry tool is missing id")
            continue
        tool_ids.append(tool_id)
        if "runtime" in tool:
            issues.append(f"tool {tool_id} must not declare runtime in canonical registry")
        for field in ("domains", "capabilities"):
            values = tool.get(field)
            if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
                issues.append(f"tool {tool_id} {field} must be a list of strings")
        capabilities = tool.get("capabilities", [])
        if isinstance(capabilities, list):
            for capability in capabilities:
                if capability not in catalog:
                    issues.append(f"tool {tool_id} references unknown capability: {capability}")
        expose_to = tool.get("expose_to", [])
        if not isinstance(expose_to, list) or not all(isinstance(value, str) and value for value in expose_to):
            issues.append(f"tool {tool_id} expose_to must be a list of strings")
            expose_to = []
        if "personal-cos" in expose_to:
            launch_kind = tool.get("launch_kind")
            if launch_kind not in {"python-script", "command"}:
                issues.append(f"tool {tool_id} has unsupported launch_kind")
            elif launch_kind == "python-script":
                script = tool.get("script")
                if not isinstance(script, str) or not generator.is_safe_manifest_path(script) or not script.endswith(".py"):
                    issues.append(f"tool {tool_id} python-script needs safe .py script")
            elif launch_kind == "command":
                command = tool.get("command")
                args = tool.get("args", [])
                if not isinstance(command, str) or not command:
                    issues.append(f"tool {tool_id} command launch needs command")
                if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
                    issues.append(f"tool {tool_id} command launch args must be a list of strings")
    if len(tool_ids) != len(set(tool_ids)):
        issues.append("tool IDs must be unique")

    accounts = registry.get("accounts", [])
    if not isinstance(accounts, list):
        return issues + ["tool registry accounts must be a list"]
    account_ids: list[str] = []
    for account in accounts:
        if not isinstance(account, dict):
            issues.append("tool registry account entries must be objects")
            continue
        account_id = account.get("id")
        if not isinstance(account_id, str) or not account_id:
            issues.append("tool registry account is missing id")
            continue
        account_ids.append(account_id)
        tool_id = account.get("tool")
        if tool_id not in tool_ids:
            issues.append(f"account {account_id} references unknown tool: {tool_id}")
    if len(account_ids) != len(set(account_ids)):
        issues.append("account IDs must be unique")
    return issues


def tool_registry_file_issues(root: Path) -> list[str]:
    path = root / TOOL_REGISTRY_PATH
    try:
        registry = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [f"cannot read tool registry: {error}"]
    return tool_registry_issues(registry)


def frontend_registry_issues(registry: object) -> list[str]:
    if not isinstance(registry, dict):
        return ["frontend registry must be an object"]
    issues: list[str] = []
    if registry.get("version") != 1:
        issues.append("frontend registry version must be 1")
    if registry.get("transport") != "local-process":
        issues.append("frontend registry transport must be local-process")
    for field in ("edge_protocol", "dispatch_protocol", "event_protocol", "owner_principal"):
        if not isinstance(registry.get(field), str) or not registry[field]:
            issues.append(f"frontend registry missing {field}")
    entries = registry.get("frontends")
    if not isinstance(entries, list) or not entries:
        return issues + ["frontend registry frontends must be a non-empty list"]
    ids: list[str] = []
    runtimes: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            issues.append("frontend registry entries must be objects")
            continue
        frontend_id = entry.get("id")
        if not isinstance(frontend_id, str) or not frontend_id:
            issues.append("frontend registry entry is missing id")
            continue
        ids.append(frontend_id)
        runtime = entry.get("runtime")
        if not isinstance(runtime, str) or not runtime:
            issues.append(f"frontend {frontend_id} is missing runtime")
        else:
            runtimes.append(runtime)
        if entry.get("role") not in FRONTEND_ROLES:
            issues.append(f"frontend {frontend_id} has unsupported role")
        token_env = entry.get("token_env")
        if not isinstance(token_env, str) or not ENV_NAME_PATTERN.fullmatch(token_env):
            issues.append(f"frontend {frontend_id} has invalid token environment")
        if entry.get("role") == "edge-relay":
            hook = entry.get("pre_agent_hook")
            if not isinstance(hook, str) or hook.count(":") != 1:
                issues.append(f"frontend {frontend_id} needs module:callable pre_agent_hook")
            runner = entry.get("transport_runner")
            if not isinstance(runner, str) or not runner:
                issues.append(f"frontend {frontend_id} needs transport_runner")
    if len(ids) != len(set(ids)):
        issues.append("frontend IDs must be unique")
    if len(runtimes) != len(set(runtimes)):
        issues.append("frontend runtimes must be unique")
    return issues


def project_registry_issues(registry: object) -> list[str]:
    if not isinstance(registry, dict):
        return ["project registry must be an object"]
    issues: list[str] = []
    if registry.get("version") != 1:
        issues.append("project registry version must be 1")
    projects = registry.get("projects")
    if not isinstance(projects, list) or not projects:
        return issues + ["project registry projects must be a non-empty list"]
    ids: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            issues.append("project registry entries must be objects")
            continue
        project_id = project.get("id")
        if not isinstance(project_id, str) or not project_id:
            issues.append("project registry entry is missing id")
            continue
        ids.append(project_id)
        root_env = project.get("root_env")
        if not isinstance(root_env, str) or not ENV_NAME_PATTERN.fullmatch(root_env):
            issues.append(f"project {project_id} has invalid root_env")
        modes = project.get("access_modes")
        if not isinstance(modes, list) or not modes or not set(modes).issubset(ACCESS_MODES):
            issues.append(f"project {project_id} has invalid access_modes")
        for field in ("root", "path", "absolute_path"):
            if field in project:
                issues.append(f"project {project_id} must not store {field}")
    if len(ids) != len(set(ids)):
        issues.append("project IDs must be unique")
    return issues


def _toml_file_issues(root: Path, relative_path: str, validator) -> list[str]:
    path = root / relative_path
    try:
        registry = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [f"cannot read {relative_path}: {error}"]
    return validator(registry)


def validate_repo(root: Path) -> list[str]:
    issues: list[str] = []
    manifest_path = root / "repo_config" / "runtime_surface_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read manifest: {error}"]
    issues.extend(manifest_issues(manifest))
    if isinstance(manifest, dict):
        try:
            issues.extend(protected_path_issues(manifest, tracked_paths(root)))
        except (OSError, subprocess.CalledProcessError) as error:
            issues.append(f"cannot inspect tracked paths: {error}")
    try:
        issues.extend(skill_issues(root))
        issues.extend(tool_registry_file_issues(root))
        issues.extend(_toml_file_issues(root, FRONTEND_REGISTRY_PATH, frontend_registry_issues))
        issues.extend(_toml_file_issues(root, PROJECT_REGISTRY_PATH, project_registry_issues))
        issues.extend(generator.sync_repo(root, check=True))
    except (OSError, ValueError) as error:
        issues.append(f"cannot validate generated surface: {error}")
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    issues = validate_repo(args.repo_root.resolve())
    if issues:
        print("Repository contract validation failed:")
        print("\n".join(f"- {issue}" for issue in issues))
        return 1
    print("Repository contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
