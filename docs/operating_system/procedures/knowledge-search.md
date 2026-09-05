# Knowledge Search

QMD provides read-only search over selected Obsidian folders. SearXNG provides
web discovery. Neither tool owns Personal OS policy, memory, or source data.

## Obsidian Collection

Keep vault path and QMD mask in ignored `.env`, never Git. Add local values:

```dotenv
OBSIDIAN_VAULT=<absolute vault path>
OBSIDIAN_QMD_MASK=<comma-separated allowlist>
```

Load `.env` into the current PowerShell session, then create or update the
allowlisted collection:

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([^#=]+)\s*=\s*(.*)\s*$') {
    $value = $matches[2].Trim().Trim('"').Trim("'")
    Set-Item "Env:$($matches[1].Trim())" $value
  }
}

if (-not $env:OBSIDIAN_VAULT -or -not $env:OBSIDIAN_QMD_MASK) {
  throw "Set OBSIDIAN_VAULT and OBSIDIAN_QMD_MASK in .env."
}

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
- Native OpenClaw memory stores assistant facts and preferences, not vault copies.
