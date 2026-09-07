# Personal OS

Personal Chief of Staff policy and runtime projection source.

## Ownership

- `docs/operating_system/`: canonical policy and procedures
- `.agents/skills/`: canonical personal-agent skills
- `repo_config/`: machine-readable identity, runtime boundary, and tool registry
- `adapters/`: runtime-specific projections with no policy ownership
- `generated_runtime/`: generated, reviewable runtime surfaces
- `scripts/`: generation and validation tools

Private user data stays outside this repository:

- `USER.md`
- `MEMORY.md`
- `memory/`
- credentials, sessions, scheduler state

## Generate

```powershell
python scripts/generate_runtime_surface.py
python scripts/generate_runtime_surface.py --check
python scripts/validate_repo_contracts.py
```

Install one generated runtime surface without touching private
data:

```powershell
python scripts/generate_runtime_surface.py --runtime openclaw --install-dir "$HOME/.openclaw/workspace"
python scripts/generate_runtime_surface.py --runtime nanobot --install-dir "$HOME/.nanobot/workspace"
```

Edit canonical sources only. Never edit `generated_runtime/` directly.

Tool identities and capability mappings live in `repo_config/tool_registry.toml`;
credentials and provider runtime configuration stay outside Git.

Mail uses one read-only provider-neutral MCP bridge in both runtimes. It exposes
`mail.search` and `mail.read`, routes `personal` through Google Workspace and
`student` through Himalaya account `ovgu`, and loads the repository `.env` at
server startup. Add mail accounts or providers in `repo_config/tool_registry.toml`,
regenerate surfaces, then restart both gateways.

Nanobot control uses the shared `.env` loader:

```powershell
.\scripts\start_nanobot.ps1
.\scripts\start_nanobot.ps1 restart
.\scripts\start_nanobot.ps1 stop
.\scripts\start_nanobot.ps1 status
.\scripts\start_nanobot.ps1 webui
```

## Add Runtime

Add one `adapters/<runtime>/manifest.toml`, then regenerate all surfaces:

```powershell
python scripts/generate_runtime_surface.py
python scripts/validate_repo_contracts.py
```

Adapters map runtime syntax only. Policy, skills, tools, and schedules remain
single-source Personal OS data. Each runtime keeps separate private memory.
