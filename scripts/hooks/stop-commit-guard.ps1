# stop-commit-guard.ps1
# VS Code Stop hook: blocks session end if uncommitted work exists.

$inputJson = [Console]::In.ReadToEnd()

$context = $null
if ($inputJson -and $inputJson.Trim() -ne '') {
    try {
        $context = $inputJson | ConvertFrom-Json -ErrorAction Stop
    } catch {
        # Malformed JSON — treated as empty context.
    }
}

# Loop prevention: return immediately when stop_hook_active is true.
if ($context -and $context.stop_hook_active -eq $true) {
    Write-Output '{}'
    exit 0
}

# Detect uncommitted changes via git status --short.
$gitStatus = git status --short 2>&1

if ($gitStatus) {
    $block = [pscustomobject]@{
        decision = 'block'
        reason   = 'Uncommitted changes detected. Commit your work before ending the session.'
    } | ConvertTo-Json -Compress
    Write-Output $block
} else {
    Write-Output '{}'
}
