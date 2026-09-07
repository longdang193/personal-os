$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "load_env.ps1") -Names @("OBSIDIAN_VAULT", "OBSIDIAN_QMD_MASK")

& qmd mcp
exit $LASTEXITCODE
