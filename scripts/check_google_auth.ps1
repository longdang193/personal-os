$ErrorActionPreference = "Continue"

$helper = Join-Path $PSScriptRoot "read_google_auth_profile.py"
$profileJson = (& python $helper 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Google Workspace auth unavailable; personal mail and calendar may fail."
    return
}
try {
    $envelope = $profileJson | ConvertFrom-Json
    if (@($envelope.PSObject.Properties.Name) -join "," -ne "ok,profile") { throw "invalid envelope" }
    $profile = $envelope.profile
    $keys = @($profile.PSObject.Properties.Name)
    $expected = @("id", "provider", "command", "status_args", "login_args", "scopes")
    if ($envelope.ok -ne $true -or $keys.Count -ne $expected.Count -or ($expected | Where-Object { $_ -notin $keys }).Count -gt 0) {
        throw "invalid profile"
    }
    if ($profile.id -ne "google-workspace" -or $profile.provider -ne "google-workspace" -or $profile.command -isnot [string] -or @($profile.status_args).Count -eq 0 -or @($profile.login_args).Count -eq 0 -or @($profile.scopes).Count -ne 2) {
        throw "invalid profile"
    }
} catch {
    Write-Warning "Google Workspace auth unavailable; personal mail and calendar may fail."
    return
}

$gws = Get-Command ($profile.command + ".ps1") -ErrorAction SilentlyContinue
if (-not $gws) { $gws = Get-Command $profile.command -ErrorAction SilentlyContinue }
$state = "missing"
if ($gws) {
    $statusArgs = @($profile.status_args)
    $output = (& $gws.Source @statusArgs 2>&1 | Out-String)
    $exitCode = $LASTEXITCODE
    $state = "provider_unavailable"
    $json = [regex]::Match($output, "(?s)\{.*\}\s*$")
    if ($exitCode -eq 0 -and $json.Success) {
        try {
            $status = $json.Value | ConvertFrom-Json
            if ($status.token_valid -is [bool]) { $state = if ($status.token_valid) { "ready" } else { "expired" } }
        } catch {}
    }
    if ($state -eq "provider_unavailable") {
        $normalized = [regex]::Replace($output, "`e\[[0-9;]*[A-Za-z]", "").ToLowerInvariant()
        if ($normalized -match "invalid_scope|invalid scope|scope name is invalid|unsupported scope|outside the domain of this legacy api") {
            $state = "invalid_scope"
        } elseif ($normalized -match "token expired|invalid_grant|authentication failed|auth required|credentials?\s+(?:expired|invalid|missing)|permission denied") {
            $state = "expired"
        }
    }
}

if ($state -eq "ready") {
    Write-Host "Google Workspace auth ready."
} elseif ($state -eq "missing") {
    Write-Warning "Google Workspace CLI not found; personal mail and calendar may fail."
} else {
    Write-Warning "Google Workspace auth unavailable; personal mail and calendar may fail."
    Write-Output "Repair with:"
    Write-Output "  `$scopes = @("
    foreach ($scope in @($profile.scopes)) {
        Write-Output "    '$scope'"
    }
    Write-Output "  )"
    $login = @($profile.login_args) -join " "
    Write-Output "  $($profile.command) $login --scopes (`$scopes -join ',')"
}
