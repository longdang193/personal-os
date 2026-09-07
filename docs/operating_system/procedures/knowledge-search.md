# Knowledge Search

QMD provides read-only search over selected Obsidian folders. SearXNG provides
web discovery. Neither tool owns Personal OS policy, memory, or source data.

## Obsidian Collection

Keep vault path and QMD mask in ignored `.env`, never Git. Add local values:

```dotenv
OBSIDIAN_VAULT=<absolute vault path>
OBSIDIAN_QMD_MASK=<comma-separated allowlist>
```

Load required `.env` values into the current PowerShell session, then create or
update the allowlisted collection:

```powershell
. .\scripts\load_env.ps1 -Names OBSIDIAN_VAULT, OBSIDIAN_QMD_MASK

qmd collection show obsidian
qmd update
```

For first setup, replace `qmd collection show obsidian` with:

```powershell
qmd collection add $env:OBSIDIAN_VAULT --name obsidian --mask $env:OBSIDIAN_QMD_MASK
```

Do not index the whole vault. Exclude job files, CVs, letters, Telegram,
temporary files, `.git`, `.obsidian`, `.venv`, `.trash`, and other runtime data.

Run `qmd embed -c obsidian` when semantic retrieval is needed. Keep Obsidian
read-only until an explicit inbox-only capture contract exists.

## Tool Roles

- `knowledge.search` uses QMD over the allowlisted Obsidian collection.
- `web.search` uses the configured SearXNG provider.
- Runtime memory stores assistant facts and preferences, not vault copies.

Nanobot starts QMD through `scripts/start_qmd_mcp.ps1`. The launcher loads only
`OBSIDIAN_VAULT` and `OBSIDIAN_QMD_MASK` from `.env`; it does not pass unrelated
secrets to QMD.

## Nanobot Control

Run from repository root:

```powershell
.\scripts\start_nanobot.ps1
.\scripts\start_nanobot.ps1 restart
.\scripts\start_nanobot.ps1 stop
.\scripts\start_nanobot.ps1 status
.\scripts\start_nanobot.ps1 logs
.\scripts\start_nanobot.ps1 webui
```

Set `NANOBOT_TELEGRAM_BOT_TOKEN` and `OPENCLAW_TELEGRAM_BOT_TOKEN` in `.env`.
The launcher loads `NANOBOT_TELEGRAM_BOT_TOKEN` automatically. Use
`-Foreground` for local debugging. OpenClaw uses its token through
`scripts/start_openclaw.ps1`.
