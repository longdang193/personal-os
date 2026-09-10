$ErrorActionPreference = "Continue"

$gws = Get-Command gws.ps1 -ErrorAction SilentlyContinue
if (-not $gws) {
    $gws = Get-Command gws -ErrorAction SilentlyContinue
}
if (-not $gws) {
    Write-Warning "Google Workspace CLI not found; personal mail and calendar may fail."
    return
}

$output = (& $gws.Source auth status 2>&1 | Out-String)
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0 -or $output -notmatch '"token_valid"\s*:\s*true') {
    Write-Warning "Google Workspace auth unavailable; personal mail and calendar may fail."
    Write-Warning "Repair with: gws auth login --scopes 'https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar'"
    return
}

Write-Host "Google Workspace auth ready."
