param(
    [ValidateSet("start", "restart", "stop", "status", "logs", "webui")]
    [string]$Command = "start",
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
if ($Command -in @("start", "restart", "webui")) {
    . (Join-Path $PSScriptRoot "load_env.ps1") -Names @("NANOBOT_TELEGRAM_BOT_TOKEN")
    $env:NANOBOT_PRE_AGENT_HOOK = "personal_edge_adapter:handle"
    $scriptRoot = (Resolve-Path $PSScriptRoot).Path
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$scriptRoot;$env:PYTHONPATH" } else { $scriptRoot }
}

$arguments = @("gateway")
if ($Command -eq "webui") {
    $arguments[0] = "webui"
}
switch ($Command) {
    "start" {
        if (-not $Foreground) {
            $arguments += "--background"
        }
    }
    default {
        if ($Command -ne "webui") {
            $arguments += $Command
        }
    }
}

& nanobot @arguments
exit $LASTEXITCODE
