"""Validate Personal OS repository contracts."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import generate_openclaw_surface as generator


REQUIRED_MANIFEST_FIELDS = {
    "runtime",
    "generatedRoot",
    "managedFiles",
    "managedDirectories",
    "protectedPaths",
}
REQUIRED_PROTECTED_PATHS = {
    "USER.md",
    "MEMORY.md",
    "memory",
    "credentials",
    "sessions",
    "scheduler",
}


def manifest_issues(manifest: object) -> list[str]:
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    issues = [
        f"manifest missing field: {field}"
        for field in sorted(REQUIRED_MANIFEST_FIELDS - manifest.keys())
    ]
    for field in ("generatedRoot",):
        if field in manifest and not generator.is_safe_manifest_path(manifest[field]):
            issues.append(f"{field} contains unsafe path: {manifest[field]}")
    for field in ("managedFiles", "managedDirectories", "protectedPaths"):
        values = manifest.get(field)
        if not isinstance(values, list):
            issues.append(f"{field} must be a list")
            continue
        for value in values:
            if not generator.is_safe_manifest_path(value):
                issues.append(f"{field} contains unsafe path: {value}")
    protected_paths = manifest.get("protectedPaths")
    if isinstance(protected_paths, list):
        missing = REQUIRED_PROTECTED_PATHS - {path for path in protected_paths if isinstance(path, str)}
        issues.extend(f"manifest missing required protected path: {path}" for path in sorted(missing))
    if (
        isinstance(manifest.get("managedFiles"), list)
        and isinstance(manifest.get("managedDirectories"), list)
        and all(isinstance(value, str) for value in manifest["managedFiles"] + manifest["managedDirectories"])
    ):
        managed = manifest["managedFiles"] + manifest["managedDirectories"]
        if len(managed) != len(set(managed)):
            issues.append("managed files and directories must be unique")
    if (
        isinstance(manifest.get("managedFiles"), list)
        and isinstance(manifest.get("managedDirectories"), list)
        and isinstance(manifest.get("protectedPaths"), list)
        and all(isinstance(value, str) for value in manifest["managedFiles"] + manifest["managedDirectories"] + manifest["protectedPaths"])
    ):
        managed = manifest["managedFiles"] + manifest["managedDirectories"]
        protected = manifest["protectedPaths"]
        issues.extend(
            f"managed path conflicts with protected path: {path}"
            for path in managed
            if any(path == item or path.startswith(f"{item}/") for item in protected)
        )
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
