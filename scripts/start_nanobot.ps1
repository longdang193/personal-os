param(
    [ValidateSet("start", "restart", "stop", "status", "logs", "webui")]
    [string]$Command = "start",
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
if ($Command -in @("start", "restart", "webui")) {
    . (Join-Path $PSScriptRoot "load_env.ps1") -Names @("NANOBOT_TELEGRAM_BOT_TOKEN")
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
