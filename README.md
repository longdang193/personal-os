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

Calendar uses one provider-neutral MCP bridge backed by `gws` OAuth. It exposes
calendar read, search, free/busy, create, update, and cancel operations. OAuth
credentials stay in the local `gws` store; no calendar token belongs in `.env`.

Set separate Telegram tokens in `.env`:

```dotenv
NANOBOT_TELEGRAM_BOT_TOKEN=<Nanobot token>
OPENCLAW_TELEGRAM_BOT_TOKEN=<OpenClaw token>
```

Before starting either bot, check Google Workspace auth:

```powershell
gws auth status
```

If `token_valid` is not `true`, repair the shared mail/calendar token with
Gmail read-only and Calendar scopes:

```powershell
gws auth login --scopes 'https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar'
```

Do not use bare `gws auth login`; broad scope presets can fail for personal
Gmail accounts. Bot startup runs this check and warns without blocking
student-only mail access.

Nanobot control uses `NANOBOT_TELEGRAM_BOT_TOKEN` from shared `.env` loader:

```powershell
.\scripts\start_nanobot.ps1
.\scripts\start_nanobot.ps1 restart
.\scripts\start_nanobot.ps1 stop
.\scripts\start_nanobot.ps1 status
.\scripts\start_nanobot.ps1 webui
```

OpenClaw must use separate `OPENCLAW_TELEGRAM_BOT_TOKEN` through
`scripts/start_openclaw.ps1`.

Nanobot is relay-only: each Telegram request runs the local
`scripts/personal_cos_launcher.py`, which invokes
`codex exec --json --cd <registered-repo> -`. Nanobot does not select agents,
read Personal OS memory, access repositories, or call Herdr. No CoS URL or auth
token is configured; Herdr remains internal to CoS and Project OS.

Use `repository_id = personal-os` or `repository_id = job-project` when a
request targets a registered repository. Roots stay in ignored `.env` through
`PERSONAL_OS_ROOT` and `JOB_PROJECT_ROOT`.

## Add Runtime

Add one `adapters/<runtime>/manifest.toml`, then regenerate all surfaces:

```powershell
python scripts/generate_runtime_surface.py
python scripts/validate_repo_contracts.py
```

Adapters map runtime syntax only. Policy, skills, tools, and schedules remain
single-source Personal OS data. Each runtime keeps separate private memory.
