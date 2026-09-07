"""Compatibility wrapper for the OpenClaw runtime surface generator."""

from __future__ import annotations

from pathlib import Path

from generate_runtime_surface import (
    install as _install,
    is_safe_manifest_path,
    load_manifest,
    output_files as _output_files,
    repo_root,
    sync_repo as _sync_repo,
)


def output_files(root: Path) -> dict[Path, bytes]:
    return _output_files(root, runtime="openclaw")


def sync_repo(root: Path, check: bool) -> list[str]:
    return _sync_repo(root, check, runtime="openclaw")


def install(root: Path, install_dir: Path) -> None:
    _install(root, install_dir, runtime="openclaw")


if __name__ == "__main__":
    from generate_runtime_surface import main

    raise SystemExit(main())
