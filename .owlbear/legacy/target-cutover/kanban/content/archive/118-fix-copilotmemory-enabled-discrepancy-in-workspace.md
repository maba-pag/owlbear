---
id: 118
title: Fix copilotMemory.enabled discrepancy in workspace settings
status: archived
priority: medium
created: 2026-03-29 03:24:19.255426+02:00
updated: 2026-03-29 05:59:38.074258+02:00
started: 2026-03-29 05:59:33.263940+02:00
completed: 2026-03-29 05:59:33.263940+02:00
tags:
- config
- phase-1
- scope:copilot
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] .vscode/settings.json contains github.copilot.chat.copilotMemory.enabled: false
- [ ] File remains valid JSON after the change
- [ ] No other settings are modified

## Context

Regression from commit 53cf529 (#7 monorepo skeleton) which rewrote settings.json and flipped the value back to 	rue, overwriting alse set in ea1621f (#48). See docs/research/copilot-memory-setting-discrepancy.md for full root-cause analysis.

[[2026-03-29]] Sun 04:06
## Architecture Review
**Verdict:** Approve

### AC Assessment
All 3 AC lines are precise and mechanically verifiable. No vague criteria remain.

### Architecture Notes
Config-only fix. No code, no interfaces, no module layering concerns. Research doc (docs/research/copilot-memory-setting-discrepancy.md) traces the regression to commit 53cf529. copilot-instructions.md line 65 already documents the intended state. No TDD test task needed (JSON config change, not application code).

### Changes Made
- Rewrote task body with precise AC (3 verifiable lines)
- Approved to todo

### Dependencies
- None. Original task #48 is archived. No downstream tasks depend on this.

## Test-Writer Notes
- Test file: tests/test_copilot_memory_setting.py
- Classes: TestFromAC_CopilotMemorySetting
- Tests per category: happy 3, edge 0, error 0, boundary 1
- Total: 4 tests, all FAIL
- ruff: clean
- AC coverage:
  - AC1 (copilotMemory.enabled: false): test_copilot_memory_enabled_is_false [happy]
  - AC1+AC2 (valid JSON + disabled): test_settings_file_is_valid_json_and_memory_disabled [happy]
  - AC3+AC1 (key count = 68): test_no_settings_removed_after_fix [boundary]
  - AC3+AC1 (specific values): test_non_memory_settings_values_unchanged [happy]

[[2026-03-29]] Sun 05:10
## Builder Notes
- Files changed: .vscode/settings.json
- Tests: 4 passed, coverage N/A (config-only change, no Python modules)
- Lint: ruff clean on tests/test_copilot_memory_setting.py
- Evidence: github.copilot.chat.copilotMemory.enabled changed from true to false; json.loads confirmed 68 keys; 4/4 TestFromAC_CopilotMemorySetting passed
- Fixes applied: PS 5.1 Set-Content adds UTF-8 BOM; used [IO.File]::WriteAllText with UTF8Encoding(false) to write without BOM

[[2026-03-29]] Sun 05:32

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Line 65 already documents the intended state accurately — no update needed |
| 2 | Docstrings | No | N/A | Config-only fix (.vscode/settings.json), no Python modules created or changed |
| 3 | docs/sources/overview.md | No | N/A | Regression fix, no external patterns or inspirations used |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | Yes | Pass | docs/research/copilot-memory-setting-discrepancy.md exists and is linked from task body |

No docs impact. Config-only regression fix; copilot-instructions.md was already accurate before this task.

### Files Updated

- None

### Scratch Files Cleaned

- None (no docs/scratch/118-* files found)

[[2026-03-29]] Sun 05:59
## Audit
### AC Verification
| AC Line | Evidence | Status |
| AC1: copilotMemory.enabled false | Terminal: ConvertFrom-Json confirms False | PASS |
| AC2: Valid JSON | Parsed successfully, 68 NoteProperty keys | PASS |
| AC3: No other settings modified | Key count 68, test_non_memory_settings_values_unchanged PASS | PASS |

### Test Results
- pytest (task): 4/4 passed (test_copilot_memory_setting.py)
- pytest (full): 647 passed, 71 failed (all failures in mcp-project RED-phase tests for #74, unrelated)
- ruff: clean

### Upstream Commits
- bf4fca1 test: add failing tests for copilotMemory.enabled fix (#118, test-writer)
- 5b04227 fix: set copilotMemory.enabled to false in workspace settings (#118, builder)

### AC Quality: 5/5
Specific, complete, mechanically verifiable. Three clear lines, no ambiguity.

### Quality Gaps
- No Review Evidence section from reviewer (minor for config-only task)

### Confidence: .97
### Action: archive
