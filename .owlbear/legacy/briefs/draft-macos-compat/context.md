# Ideation Context — macOS Compatibility

<!-- Incremental: updated after each moment -->

## Problem Statement

OwlBear has been developed and used exclusively on Windows. The codebase has deep Windows assumptions baked into its hook system, agent definitions, browser discovery, and test suite. The user has cloned the dev repo to macOS and needs two workflows functional:

1. **Dev workflow on macOS** — develop on `dev` branch: run tests, lint, use MCP servers, operate the kanban pipeline, run agents.
2. **Consumer workflow on macOS** — use the `main` branch in other projects via `setup/init.py`, exactly as done on Windows.

Secondary goals: Docker compatibility (~30% priority), Linux (~10%).

### Root causes (inventory)

| Category | Count | Impact |
|----------|-------|--------|
| PowerShell hook scripts (.ps1) | 13 files | **CRITICAL** — entire hook system is Windows-only |
| Agent .agent.md `command:` fields referencing `powershell` | 14+ agents | **CRITICAL** — agents can't load hooks on macOS |
| VS Code terminal config (pwsh paths, env vars) | 1 file | MEDIUM |
| Browser discovery (LOCALAPPDATA, Edge .exe paths) | 2 locations | MEDIUM |
| kanban-md binary (.exe reference) | 1+ locations | MEDIUM |
| Test skip decorators (Windows-only) | 10+ tests | LOW — correctly skip, but coverage gap |
| File locking (msvcrt vs fcntl) | 1 location | Already cross-platform ✓ |

### What works already
- kanban MCP server starts (uses `uv run`, platform-agnostic)
- `init.py` uses `pathlib` and `os.path.relpath` — mostly cross-platform
- MCP config (`mcp.json`) uses `uv`/`uvx` commands — no Windows dependency
- File locking in `engine.py` already has `sys.platform` branching
- kanban-md Go binary is legacy — Python `owlbear_kanban` engine replaced it

### Clarifications (from Critic + user)
- **No PowerShell on macOS.** Hooks must work with bash/zsh natively.
- **Browser features stay Windows-only for now.** Playwright launcher, Chrome extension discovery are deferred.
- **kanban-md.exe references are legacy.** The Python engine is the active path. Old .exe references need cleanup, not a new build.
- **Seeded consumer config** (`seed/.vscode/settings.json`) inherits Windows bias (pwsh terminal profiles). Must be platform-aware.
- **Test parity matters.** Hook tests are Windows-only today. macOS needs equivalent test coverage to validate the port.

### Blockers (revised priority)
1. **CRITICAL — Hook system:** 13 .ps1 scripts need bash equivalents; 14+ agent `command:` fields need platform-aware invocation
2. **HIGH — Seeded consumer config:** seed/.vscode/settings.json bakes in Windows terminal profiles
3. **HIGH — Test parity:** Hook tests only run on Windows; macOS needs equivalent coverage
4. **MEDIUM — Legacy .exe references:** kanban-md.exe in tests/orchestrator need cleanup
5. **DEFERRED — Browser discovery:** stays Windows-only

## Outcomes

All outcomes are Essential. Shell target: **bash** (POSIX-compatible, available on macOS by default).

**O1 — Cross-platform hook system:** Every .ps1 hook has a bash (.sh) equivalent that produces the same behavior (same exit codes, same file-filtering logic). Every .agent.md file's `command:` field invokes the correct hook for the current platform. Covers ALL agents (pipeline, ideation, utility).
- *Acceptance test:* For each .ps1/.sh pair, a parameterized test invokes the script with the same inputs and asserts the same outputs. On macOS the bash variant runs; on Windows the PowerShell variant runs. Zero `powershell` references remain in agent command fields on macOS.

**O2 — Consumer setup produces a working macOS workspace:** `python ../owlbear/setup/init.py` on macOS produces a `.vscode/settings.json` without Windows-only terminal profiles, and a `.vscode/mcp.json` with working server commands. Seeded hook files include bash variants. Setup/sharing documentation covers macOS.
- *Acceptance test:* init.py integration test on macOS asserts: no `pwsh.exe` path in settings, hook files include .sh variants, MCP server entries use `uv` (already platform-agnostic). Documentation mentions macOS setup steps.

**O3 — Dev workflow passes on macOS:** `uv run ruff check` and `uv run pytest` succeed on macOS. Legacy .exe references in orchestrator/tests don't block execution (skipped or cleaned up). Browser code paths that hit Windows-only APIs fail gracefully (not crash) on macOS.
- *Acceptance test:* CI-equivalent commands (`uv run ruff check .`, `uv run pytest`) exit 0 on macOS. No import errors, no unguarded platform calls.

## Landscape

### Hook System Architecture (current)
- **7 unique PowerShell scripts** with identical I/O pattern: read JSON from stdin via `[Console]::In.ReadToEnd()`, process with `ConvertFrom-Json`, output JSON via `Write-Output`/`ConvertTo-Json`
- **19 agent files** hardcode `powershell -NoProfile -NonInteractive -File .owlbear/hooks/{script}.ps1`
- **VS Code agent `command:` field is a literal string** — no platform conditional, no env var substitution, no `when:` directive
- Hook types: PreToolUse (permission guards), PostToolUse (lint feedback), SessionStart (git context)

### Hook Script Inventory
| Script | Type | Logic |
|--------|------|-------|
| allow-stances-only.ps1 | PreToolUse | Allow writes only to `/stances/` paths |
| deny-code-writes.ps1 | PreToolUse | Block writes to source/infra directories |
| deny-scratch-only-writes.ps1 | PreToolUse | Allow only `.owlbear/scratch/` writes |
| deny-src-writes.ps1 | PreToolUse | Allow only `tests/` writes |
| deny-writes.ps1 | PreToolUse | Deny all writes (read-only agents) |
| lint-changed.ps1 | PostToolUse | Run ruff on edited files |
| session-context.ps1 | SessionStart | Gather git branch/commit context |

### What Already Works Cross-Platform
- MCP config uses `uv run` commands — no changes needed
- Settings paths use `/` notation — OK
- Git commands work on all platforms
- File locking has sys.platform branching
- init.py uses pathlib — mostly OK

### Key Design Constraint
VS Code's agent YAML does NOT support platform-conditional commands. A single `command:` string must work on both platforms, OR agent files must be generated per-platform, OR a platform-agnostic command must be used.

### Approach Options (for panelist deliberation)
**A. Python hooks** — Rewrite all 7 scripts as Python. Agent command: `python .owlbear/hooks/deny-writes.py`. Works everywhere. Python is already a prerequisite.
**B. Bash + PowerShell dual** — Keep .ps1 for Windows, add .sh for macOS. Use a thin dispatcher (Python or shell) in the command field.
**C. Python dispatcher** — Single `python .owlbear/hooks/dispatch.py deny-writes` that delegates to .ps1 or .sh based on platform.
