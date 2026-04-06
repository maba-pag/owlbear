# deny-src-writes.ps1 — PreToolUse hook for the test-writer agent.
# Allow-list path guard: only writes to tests/ are permitted.
# Reads VS Code hooks stdin JSON, checks paths for write tools, denies writes outside tests/.
# Usage: invoked automatically by VS Code as a PreToolUse hook.

$input_text = [Console]::In.ReadToEnd()
try {
    $payload = $input_text | ConvertFrom-Json -ErrorAction Stop
} catch {
    Write-Output '{}'
    exit 0
}

$tool_name = $payload.tool_name

$write_tools = @(
    'create_file',
    'replace_string_in_file',
    'multi_replace_string_in_file',
    'create_directory'
)

# Pass-through for non-write tools or missing/empty tool_name
if (-not $tool_name -or ($write_tools -notcontains $tool_name)) {
    Write-Output '{}'
    exit 0
}

# Extract paths from tool_input
$tool_input = $payload.tool_input
$paths = @()

if ($tool_input) {
    # filePath (create_file, replace_string_in_file)
    $fp = $tool_input.filePath
    if ($fp -is [string] -and $fp.Length -gt 0) { $paths += $fp }

    # dirPath (create_directory)
    $dp = $tool_input.dirPath
    if ($dp -is [string] -and $dp.Length -gt 0) { $paths += $dp }

    # replacements[*].filePath (multi_replace_string_in_file)
    foreach ($r in $tool_input.replacements) {
        $rfp = $r.filePath
        if ($rfp -is [string] -and $rfp.Length -gt 0) { $paths += $rfp }
    }
}

# Pass-through if no paths extracted
if ($paths.Count -eq 0) {
    Write-Output '{}'
    exit 0
}

# Check each path against allow-list (tests/ prefix only)
foreach ($p in $paths) {
    # Normalize backslashes to forward slashes
    $normalized = $p -replace '\\', '/'
    $isInTests = $normalized -match '(^|/)tests/'
    if (-not $isInTests) {
        $response = @{
            hookSpecificOutput = @{
                permissionDecision       = 'deny'
                permissionDecisionReason = "test-writer path guard: write target '$normalized' is outside the allowed directory (tests/). Only writes to tests/ are permitted."
            }
        }
        Write-Output ($response | ConvertTo-Json -Compress)
        exit 0
    }
}

Write-Output '{}'
