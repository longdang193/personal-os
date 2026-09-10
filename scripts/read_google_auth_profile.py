"""Expose validated, non-secret Google Workspace auth profile."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

PROFILE_KEYS = ("id", "provider", "command", "status_args", "login_args", "scopes")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]
REGISTRY_PATH = Path(__file__).resolve().parents[1] / "repo_config" / "tool_registry.toml"


def load_profile(registry_path: Path = REGISTRY_PATH) -> dict[str, Any]:
    registry = tomllib.loads(registry_path.read_text(encoding="utf-8"))
    profiles = registry.get("auth_profiles")
    if not isinstance(profiles, list) or len(profiles) != 1:
        raise ValueError("invalid profile")
    profile = profiles[0]
    if not isinstance(profile, dict) or set(profile) != set(PROFILE_KEYS) | {"redact_output"}:
        raise ValueError("invalid profile")
    if (
        profile.get("id") != "google-workspace"
        or profile.get("provider") != "google-workspace"
        or not isinstance(profile.get("command"), str)
        or not profile["command"]
        or profile.get("status_args") != ["auth", "status"]
        or profile.get("login_args") != ["auth", "login"]
        or profile.get("scopes") != SCOPES
        or profile.get("redact_output") is not True
    ):
        raise ValueError("invalid profile")
    return {key: profile[key] for key in PROFILE_KEYS}


def main() -> int:
    try:
        profile = load_profile()
    except tomllib.TOMLDecodeError:
        print(json.dumps({"ok": False, "error": "invalid_profile"}, separators=(",", ":")))
        return 2
    except OSError:
        print(json.dumps({"ok": False, "error": "profile_unavailable"}, separators=(",", ":")))
        return 3
    except (TypeError, ValueError, KeyError):
        print(json.dumps({"ok": False, "error": "invalid_profile"}, separators=(",", ":")))
        return 2
    print(json.dumps({"ok": True, "profile": profile}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
