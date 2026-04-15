# allow-stances-only.ps1 — PreToolUse hook for ideation domain panelists.
# Allow-list path guard: permits writes ONLY to stances/ directories.
# Reads VS Code hooks stdin JSON, checks paths for write tools, denies writes outside stances/.
# Usage: invoked automatically by VS Code as a PreToolUse hook.
#
# Allowed paths:
#   */stances/*  — panelist stance output files (architect.md, data.md, etc.)
#
# Denied:
#   Everything else — panelists must not write outside their stances/ scope.

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
    'create_directory',
    'apply_patch',
    'editFiles'
)

# Pass-through for non-write tools or missing/empty tool_name
if (-not $tool_name -or ($write_tools -cnotcontains $tool_name)) {
    Write-Output '{}'
    exit 0
}

# Extract paths from tool_input
$tool_input = $payload.tool_input
$paths = @()

if ($tool_input) {
    # filePath (create_file, replace_string_in_file, apply_patch)
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

    # files[*] (editFiles) -- string elements or object-with-filePath elements (defensive)
    foreach ($f in $tool_input.files) {
        if ($f -is [string] -and $f.Length -gt 0) {
            $paths += $f
        } elseif ($null -ne $f) {
            $efp = $f.filePath
            if ($efp -is [string] -and $efp.Length -gt 0) { $paths += $efp }
        }
    }
}

# Pass-through if no paths extracted
if ($paths.Count -eq 0) {
    Write-Output '{}'
    exit 0
}

# Check each path — allow only if it contains /stances/ as a path component
foreach ($p in $paths) {
    # Normalize: backslashes to forward slashes, strip leading ./
    $normalized = $p -replace '\\', '/'
    if ($normalized.StartsWith('./')) {
        $normalized = $normalized.Substring(2)
    }

    $is_allowed = $normalized -match '(/|^)stances/'

    if (-not $is_allowed) {
        $response = @{
            hookSpecificOutput = @{
                permissionDecision       = 'deny'
                permissionDecisionReason = (
                    "ideation panelist path guard: write target '$normalized' " +
                    "is outside the allowed stances/ directory. Domain panelists " +
                    "may only write to stances/ within the brief working directory."
                )
            }
        }
        Write-Output ($response | ConvertTo-Json -Compress)
        exit 0
    }
}

Write-Output '{}'
