# Knowledge Search

QMD provides read-only search over selected Obsidian folders. SearXNG provides
web discovery. Neither tool owns Personal OS policy, memory, or source data.

## Obsidian Collection

Keep the vault path and QMD index outside Git. Set the local vault path, then
create the allowlisted collection:

```powershell
$env:OBSIDIAN_VAULT = "$HOME\OneDrive\OBSIDIAN 24 09 01\24 09 01 obsidian-go-obsidian_v.0.3.1"
$mask = "DE/**/*.md,German_New_Words/**/*.md,German_Speaking/**/*.md,ORBA/**/*.md,AI-102/**/*.md,ACT/**/*.md"
qmd collection add $env:OBSIDIAN_VAULT --name obsidian --mask $mask
qmd update
```

Do not index the whole vault. Exclude job files, CVs, letters, Telegram,
temporary files, `.git`, `.obsidian`, `.venv`, `.trash`, and other runtime data.

Run `qmd embed -c obsidian` when semantic retrieval is needed. Keep Obsidian
read-only until an explicit inbox-only capture contract exists.

## Tool Roles

- `knowledge.search` uses QMD over the allowlisted Obsidian collection.
- `web.search` uses the configured SearXNG provider.
- Native OpenClaw memory stores assistant facts and preferences, not vault copies.
