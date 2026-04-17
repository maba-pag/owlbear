# Update seed/ with .py Hooks and Clean Settings

> **Owning task:** #898 — Update seed/ with .py hooks and clean settings
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #898 (step 4 of the macOS compatibility brief) requires updating `seed/` to replace PowerShell hooks with Python equivalents and remove Windows-only VS Code settings. The question: what is the exact scope of changes and are there blockers?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `.owlbear/hooks/*.py` (7 files) | Codebase | 1.0 — source of truth for .py hooks |
| `seed/.owlbear/hooks/*.ps1` (6 files) | Codebase | 1.0 — files to replace |
| `seed/.vscode/settings.json` | Codebase | 1.0 — contains Windows-only settings |
| `.owlbear/briefs/draft-macos-compat/brief.md` | Codebase | 0.9 — defines approach and decisions |
| `tests/test_*hook*` (12 files) | Codebase | 0.7 — confirms .py hooks are tested |

## 3. Analysis

### Current State

| Directory | .ps1 count | .py count | Expected .py |
|-----------|-----------|-----------|-------------|
| `.owlbear/hooks/` | 7 | 7 | 7 ✓ |
| `seed/.owlbear/hooks/` | 6 | 0 | 7 (drift: missing `deny-scratch-only-writes`) |

### Settings.json — 3 Windows-Only Blocks to Remove

| Block | Lines | Content |
|-------|-------|---------|
| `[powershell]` formatter | 18–20 | `editor.defaultFormatter: ms-vscode.powershell` |
| Default Windows profile | ~152 | `terminal.integrated.defaultProfile.windows: pwsh` |
| Windows terminal profiles | ~154–158 | Custom `pwsh.exe` path |

### Dependency Status

| Dep ID | Exists on board? | Prerequisite met? |
|--------|-----------------|-------------------|
| #894 | **No** | .py hooks exist in `.owlbear/hooks/` ✓ |
| #895 | **No** | 12 hook test files exist ✓ |
| #896 | **No** | Agent files still use .ps1 (task #897 pending) |

Dependencies #894–896 and parent #890 are absent from the board — likely stale references from an incomplete decomposition. The actual prerequisites (hooks ported, tests written) are met. Agent file updates (#897) are independent of seed updates.

### `grep` Audit

- `grep -r ".ps1" seed/` → 6 hits (all in `seed/.owlbear/hooks/`)
- `grep -r "powershell" seed/` → 3 hits (all in `seed/.vscode/settings.json`)

## 4. Recommendation (confidence: 0.92)

**Proceed as T1 — straightforward config task.** Implementation:
1. Copy 7 `.py` files from `.owlbear/hooks/` to `seed/.owlbear/hooks/`
2. Delete 6 `.ps1` files from `seed/.owlbear/hooks/`
3. Remove 3 Windows-only blocks from `seed/.vscode/settings.json`
4. Verify: `grep -r ".ps1" seed/` and `grep -r "powershell" seed/` return no results

Challenge: skipped — trivial config/cleanup, no design decision.

Risk: Low. Seed is a template, not production code. Changes are reversible.

## 5. Follow-up Tasks

No new tasks needed — #898 itself is the actionable work item, ready for backlog.
