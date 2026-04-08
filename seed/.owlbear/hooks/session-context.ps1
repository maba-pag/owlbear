# session-context.ps1 — SessionStart hook for pipeline agents.
# Reads stdin JSON, runs git branch/log, outputs SessionStart additionalContext.
# Returns {} on any failure (non-blocking).

$input_text = [Console]::In.ReadToEnd()

# Return {} on empty stdin
if (-not $input_text.Trim()) {
    Write-Output '{}'
    exit 0
}

# Return {} on malformed JSON
try {
    $null = $input_text | ConvertFrom-Json -ErrorAction Stop
} catch {
    Write-Output '{}'
    exit 0
}

# Get current branch — return {} if not in a git repo
$branch = git branch --show-current 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Output '{}'
    exit 0
}
if (-not $branch) {
    $branch = 'HEAD'
}
$branch = $branch.Trim()

# Get recent commits — return {} on git failure
$log_lines = @(git log --oneline -3 --no-decorate 2>$null)
if ($LASTEXITCODE -ne 0) {
    Write-Output '{}'
    exit 0
}
$commit_parts = @($log_lines | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() })
$commits_str = $commit_parts -join ' | '

$additional_context = "Branch: $branch | Commits: $commits_str"

$output = @{
    hookSpecificOutput = @{
        hookEventName     = 'SessionStart'
        additionalContext = $additional_context
    }
}

$output | ConvertTo-Json -Compress -Depth 3
