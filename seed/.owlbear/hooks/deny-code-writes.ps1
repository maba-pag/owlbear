# deny-code-writes.ps1 — PreToolUse hook for the doc-writer agent.
# Deny-list path guard: blocks writes to source code and infrastructure directories.
# Reads VS Code hooks stdin JSON, checks paths for write tools, denies writes to denied dirs.
# Usage: invoked automatically by VS Code as a PreToolUse hook.
#
# MAINTENANCE: Update $denied_prefixes and $denied_exact when new source dirs are added.
#
# Denied directories (deny-list):
#   serve/            — MCP server source code
#   v1/               — v1 legacy source code
#   tests/            — test suite
#   setup/            — setup scripts
#   seed/             — seed data
#   store/            — runtime data store
#   share/agents/     — agent config (self-modification guard)
#   .git/             — git internals (privilege escalation vector)
#   .owlbear/hooks/   — hook scripts (self-modification guard)
#   .owlbear/scripts/ — automation scripts (self-modification guard)
#
# Denied exact paths:
#   conftest.py       — root pytest configuration
#
# Allowed (not in deny-list):
#   .github/          — copilot-instructions.md and workflow docs
#   share/skills/     — skill documentation (doc-writer's primary output)
#   share/instructions/ — instruction files
#   .owlbear/research/  — research and analysis documents
#   README*.md, SECURITY.md, and other root-level docs

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

$denied_prefixes = @(
    'serve/',
    'v1/',
    'tests/',
    'setup/',
    'seed/',
    'store/',
    'share/agents/',
    '.git/',
    '.owlbear/hooks/',
    '.owlbear/scripts/'
)

$denied_exact = @('conftest.py')

# Check each path against deny-list; deny entire call if any path is denied
foreach ($p in $paths) {
    # Normalize: backslashes to forward slashes, strip leading ./
    $normalized = $p -replace '\\', '/'
    if ($normalized.StartsWith('./')) {
        $normalized = $normalized.Substring(2)
    }

    $is_denied = $false

    foreach ($prefix in $denied_prefixes) {
        if ($normalized.StartsWith($prefix)) {
            $is_denied = $true
            break
        }
    }

    if (-not $is_denied) {
        foreach ($exact in $denied_exact) {
            if ($normalized -eq $exact) {
                $is_denied = $true
                break
            }
        }
    }

    if ($is_denied) {
        $response = @{
            hookSpecificOutput = @{
                permissionDecision       = 'deny'
                permissionDecisionReason = "doc-writer path guard: write target '$normalized' is in a denied directory. Doc-writer must not write to source code directories (deny-list: serve/, v1/, tests/, setup/, seed/, store/, share/agents/, .git/, .owlbear/hooks/, .owlbear/scripts/, conftest.py)."
            }
        }
        Write-Output ($response | ConvertTo-Json -Compress)
        exit 0
    }
}

Write-Output '{}'
