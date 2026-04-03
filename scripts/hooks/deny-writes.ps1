# deny-writes.ps1 — PreToolUse hook for the reviewer agent.
# Reads VS Code hooks stdin JSON, denies write tool calls, passes through all others.
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
    'apply_patch',
    'create_directory'
)

if ($tool_name -and ($write_tools -contains $tool_name)) {
    $response = @{
        hookSpecificOutput = @{
            permissionDecision       = 'deny'
            permissionDecisionReason = 'The reviewer agent is read-only. File writes are not permitted during review.'
        }
    }
    Write-Output ($response | ConvertTo-Json -Compress)
} else {
    Write-Output '{}'
}
