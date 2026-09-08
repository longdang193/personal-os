"""Run one local Codex CoS turn for a Personal OS edge request."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_REGISTRY_PATH = ROOT / "repo_config" / "project_registry.toml"
TOOL_REGISTRY_PATH = ROOT / "repo_config" / "tool_registry.toml"
SKILL_ROOT = ROOT / ".agents" / "skills"
ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
ACCESS_MODES = {"read", "write"}


def load_env(path: Path = ROOT / ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ENV_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return values


def project_roots(registry_path: Path = PROJECT_REGISTRY_PATH) -> dict[str, tuple[str, set[str]]]:
    registry = tomllib.loads(registry_path.read_text(encoding="utf-8"))
    return {
        project["id"]: (project["root_env"], set(project["access_modes"]))
        for project in registry["projects"]
    }


def resolve_project_root(envelope: dict[str, Any]) -> tuple[str, Path]:
    project_id = envelope.get("repository_id") or "personal-os"
    if not isinstance(project_id, str):
        raise ValueError("repository_id must be a string")
    projects = project_roots()
    if project_id not in projects:
        raise ValueError(f"unknown repository_id: {project_id}")
    root_env, access_modes = projects[project_id]
    access_mode = envelope.get("access_mode", "read")
    if access_mode not in ACCESS_MODES or access_mode not in access_modes:
        raise ValueError(f"unsupported access_mode for {project_id}: {access_mode}")
    raw_root = os.environ.get(root_env, "").strip() or load_env().get(root_env, "").strip()
    if not raw_root:
        raise ValueError(f"{root_env} is not configured")
    root = Path(raw_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"configured repository root does not exist: {project_id}")
    return project_id, root


def event(request_id: str, sequence: int, event_type: str, text: str) -> dict[str, Any]:
    return {
        "version": "personal.event.v1",
        "request_id": request_id,
        "sequence": sequence,
        "type": event_type,
        "payload": {"text": text},
    }


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False), flush=True)


def codex_command(root: Path) -> list[str]:
    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--json",
        "-c",
        'model="combo-normal"',
        "-c",
        'model_reasoning_effort="low"',
    ]
    config_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    config_path = config_home / "config.toml"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        config = {}
    mcp_servers = config.get("mcp_servers", {})
    if isinstance(mcp_servers, dict):
        for name in mcp_servers:
            if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_-]+", name):
                command.extend(["-c", f"mcp_servers.{name}.enabled=false"])
    try:
        registry = tomllib.loads(TOOL_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        registry = {}
    for tool in registry.get("tools", []):
        tool_id = tool.get("id") if isinstance(tool, dict) else None
        tool_command = tool.get("command") if isinstance(tool, dict) else None
        if not isinstance(tool_id, str) or not tool_id.endswith("-runtime") or not isinstance(tool_command, str):
            continue
        parts = tool_command.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].endswith(".py"):
            continue
        server_name = tool_id.removesuffix("-runtime")
        script = (ROOT / parts[1]).resolve()
        mcp = (
            f"mcp_servers.{server_name}="
            f"{{command={json.dumps(sys.executable)},args=[\"-u\",{json.dumps(str(script))}],"
            f"cwd={json.dumps(str(ROOT))},enabled=true}}"
        )
        command.extend(["-c", mcp])
    command.extend(["--cd", str(root), "-"])
    return command


def codex_input(envelope: dict[str, Any]) -> str:
    return (
        "Personal CoS bootstrap:\n"
        f"- Canonical Personal OS skills live at {SKILL_ROOT}.\n"
        "- Read applicable skills from that path; do not probe user-global skill paths.\n\n"
        f"Edge request envelope:\n{json.dumps(envelope, ensure_ascii=False)}"
    )


def run(envelope: dict[str, Any]) -> int:
    request_id = envelope.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("request_id is required")
    if envelope.get("version") != "personal.edge.v1":
        raise ValueError("unsupported edge protocol")
    if not isinstance(envelope.get("text"), str):
        raise ValueError("text is required")

    project_id, root = resolve_project_root(envelope)
    sequence = 0
    emit(event(request_id, sequence, "accepted", f"CoS turn started in {project_id}"))
    sequence += 1
    process = subprocess.run(
        codex_command(root),
        input=codex_input(envelope),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=600,
        check=False,
    )
    final_text = None
    errors: list[str] = []
    for line in (process.stdout or "").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("type") == "turn.started":
            emit(event(request_id, sequence, "progress", "Codex CoS turn running"))
            sequence += 1
        if item.get("type") != "item.completed":
            continue
        completed_item = item.get("item")
        if not isinstance(completed_item, dict):
            continue
        item_type = completed_item.get("type")
        if item_type == "agent_message" and isinstance(completed_item.get("text"), str):
            final_text = completed_item["text"]
        elif item_type == "error" and isinstance(completed_item.get("message"), str):
            errors.append(completed_item["message"])

    if process.returncode != 0:
        detail = (process.stderr or "").strip() or "; ".join(errors) or f"codex exited with {process.returncode}"
        emit(event(request_id, sequence, "failed", detail))
        return 0
    if final_text is None:
        detail = "; ".join(errors) or "Codex CoS returned no agent message"
        emit(event(request_id, sequence, "failed", detail))
        return 0
    emit(event(request_id, sequence, "completed", final_text))
    return 0


def main() -> int:
    envelope: dict[str, Any] | None = None
    try:
        value = json.load(sys.stdin)
        if not isinstance(value, dict):
            raise ValueError("request must be an object")
        envelope = value
        return run(value)
    except (OSError, subprocess.SubprocessError, tomllib.TOMLDecodeError, ValueError, json.JSONDecodeError) as error:
        request_id = envelope.get("request_id") if isinstance(envelope, dict) else "unknown"
        emit(event(request_id, 0, "failed", str(error)))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
