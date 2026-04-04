# lint-changed.ps1 — PostToolUse hook for the builder agent.
# Reads VS Code hooks stdin JSON, runs ruff on edited files, reports lint errors.
# Usage: invoked automatically by VS Code as a PostToolUse hook.

$input_text = [Console]::In.ReadToEnd()
try {
    $payload = $input_text | ConvertFrom-Json -ErrorAction Stop
} catch {
    Write-Output '{}'
    exit 0
}

$tool_name = $payload.tool_name

$edit_tools = @(
    'create_file',
    'replace_string_in_file',
    'multi_replace_string_in_file'
)

if (-not ($tool_name -and ($edit_tools -contains $tool_name))) {
    Write-Output '{}'
    exit 0
}

# Extract unique file paths based on tool name
$file_paths = [System.Collections.Generic.List[string]]::new()
$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
try {
    if ($tool_name -eq 'multi_replace_string_in_file') {
        foreach ($replacement in $payload.tool_input.replacements) {
            if ($replacement.filePath -and $seen.Add($replacement.filePath)) {
                $file_paths.Add($replacement.filePath)
            }
        }
    } else {
        $fp = $payload.tool_input.filePath
        if ($fp) {
            $file_paths.Add($fp)
        }
    }
} catch {
    Write-Output '{}'
    exit 0
}

if ($file_paths.Count -eq 0) {
    Write-Output '{}'
    exit 0
}

# Only lint files that exist on disk (missing paths → {} not an error)
$existing_paths = @($file_paths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
if ($existing_paths.Count -eq 0) {
    Write-Output '{}'
    exit 0
}

# Run ruff check; ignore INP001 (implicit namespace package) to avoid false positives
# on files outside a Python package directory (e.g. temp files in tests).
try {
    $ruff_result = & ruff check --ignore INP001 @existing_paths 2>&1
    $ruff_exit = $LASTEXITCODE
} catch {
    Write-Output '{}'
    exit 0
}

if ($ruff_exit -eq 1) {
    # Lint errors found — report via systemMessage (user-facing) and additionalContext (model-facing)
    $ruff_output = ($ruff_result | ForEach-Object { "$_" }) -join "`n"
    $response = @{
        systemMessage      = $ruff_output
        hookSpecificOutput = @{
            hookEventName    = 'PostToolUse'
            additionalContext = $ruff_output
        }
    }
    Write-Output ($response | ConvertTo-Json -Compress -Depth 3)
} else {
    # Exit code 0 (clean) or 2+ (error, e.g., file not found) -> return {}
    Write-Output '{}'
}
exit 0
