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
    $output = (& $gws.Source @($profile.status_args) 2>&1 | Out-String)
    $exitCode = $LASTEXITCODE
    $normalized = [regex]::Replace($output, "`e\[[0-9;]*[A-Za-z]", "").ToLowerInvariant()
    $state = "provider_unavailable"
    if ($normalized -match "invalid_scope|invalid scope|scope name is invalid|unsupported scope|outside the domain of this legacy api") {
        $state = "invalid_scope"
    } elseif ($normalized -match "token expired|invalid_grant|authentication failed|auth required|credential|permission denied") {
        $state = "expired"
    } elseif ($exitCode -eq 0) {
        try {
            $status = $output | ConvertFrom-Json
            if ($output -match '"token_valid"\s*:') {
                if ($status.token_valid -is [bool]) { $state = if ($status.token_valid) { "ready" } else { "expired" } }
            }
        } catch {}
    }
}

if ($state -eq "ready") {
    Write-Host "Google Workspace auth ready."
} elseif ($state -eq "missing") {
    Write-Warning "Google Workspace CLI not found; personal mail and calendar may fail."
} else {
    Write-Warning "Google Workspace auth unavailable; personal mail and calendar may fail."
    $scopes = (@($profile.scopes) -join ",")
    $repair = (@($profile.login_args) + @("--scopes", $scopes)) -join " "
    Write-Warning "Repair with: $($profile.command) $repair"
}
