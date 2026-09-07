param(
    [string[]]$Names = @(),
    [string[]]$OptionalNames = @()
)

$ErrorActionPreference = "Stop"

$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env file: $envFile"
}

$requested = @($Names + $OptionalNames | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique)
Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
        $name = $matches[1]
        if ($requested.Count -eq 0 -or $requested -contains $name) {
            $value = $matches[2].Trim().Trim('"').Trim("'")
            Set-Item "Env:$name" $value
        }
    }
}

foreach ($name in $requested) {
    if ($OptionalNames -contains $name) {
        continue
    }
    if (-not [Environment]::GetEnvironmentVariable($name)) {
        throw "Set $name in .env."
    }
}
