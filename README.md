# Personal OS

Personal Chief of Staff policy and runtime projection source.

## Ownership

- `docs/operating_system/`: canonical policy and procedures
- `.agents/skills/`: canonical personal-agent skills
- `repo_config/`: machine-readable identity, runtime boundary, and tool registry
- `generated_runtime/openclaw/`: generated, reviewable OpenClaw surface
- `scripts/`: generation and validation tools

Private user data stays outside this repository:

- `USER.md`
- `MEMORY.md`
- `memory/`
- credentials, sessions, scheduler state

## Generate

```powershell
python scripts/generate_openclaw_surface.py
python scripts/generate_openclaw_surface.py --check
python scripts/validate_repo_contracts.py
```

Install generated files into an OpenClaw workspace without touching private
data:

```powershell
python scripts/generate_openclaw_surface.py --install-dir "$HOME/.openclaw/workspace"
```

Edit canonical sources only. Never edit `generated_runtime/openclaw/` directly.

Tool identities and capability mappings live in `repo_config/tool_registry.toml`;
credentials and provider runtime configuration stay outside Git.
