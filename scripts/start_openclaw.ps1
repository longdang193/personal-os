param(
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "load_env.ps1") -Names @("OPENCLAW_TELEGRAM_BOT_TOKEN")

$openclawEntry = Join-Path $env:APPDATA "npm\node_modules\openclaw\dist\index.js"
$arguments = @(
    "--max-old-space-size=8192",
    $openclawEntry,
    "gateway",
    "--port",
    "18789"
)

if ($Foreground) {
    & "node.exe" $arguments
    exit $LASTEXITCODE
}

Start-Process -FilePath "node.exe" -ArgumentList @(
    $arguments[0],
    "`"$openclawEntry`"",
    $arguments[2..($arguments.Count - 1)]
) -WindowStyle Hidden
