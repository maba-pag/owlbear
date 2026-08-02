---
id: 588
title: Support 'archived' status in move_task MCP tool
status: archived
priority: medium
created: 2026-04-04 07:08:49.826519+02:00
updated: 2026-04-04 18:17:38.048799+02:00
started: 2026-04-04 18:17:38.048799+02:00
completed: 2026-04-04 18:17:38.048799+02:00
tags:
- scope:mcp
- type:build
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Allow `move_task` MCP tool to accept "archived" as a target status, using kanban-md's `archive` CLI command under the hood.

## Acceptance Criteria
- [ ] `move_task(task_id, status="archived")` archives the task (calls `kanban-md archive`)
- [ ] All other status values continue to use `kanban-md move` as before
- [ ] Error from `kanban-md archive` is surfaced via ToolError
- [ ] Unit tests cover the new archive path and the existing move paths still pass

## Context
Currently `move_task` only supports the 7 defined statuses (ideation through done). Archiving requires the separate `kanban-md archive` command. This gap means agents have no MCP tool to archive tasks — they must use `end_work(outcome="success")` repeatedly to advance through every status first, which is impractical for mass cleanup.

[[2026-04-04]] Sat 16:04
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_move_task_588.py
- Classes: TestFromAC_MoveTaskArchived
- Tests per category: happy 2, edge 1, error 2, boundary 1
- Total: 6 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| move_task(status="archived") calls kanban-md archive | test_archived_status_routes_to_archive_command, test_archived_status_does_not_invoke_move_command, test_archived_status_word_not_passed_as_cli_arg |
| All other statuses use kanban-md move | test_move_task_status_param_enum_includes_archived (schema boundary) |
| Error from archive surfaced via ToolError | test_archived_error_raises_tool_error, test_archived_error_message_from_stderr |

[[2026-04-04]] Sat 16:15
## Builder Notes
- Files changed: `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` (2 edits)
- `move_task`: branched on `status == "archived"` → calls `_run_kanban(app_ctx, "archive", task_id)`; errors surface as `ToolError`; existing `move` path unchanged
- `_patch_params("move_task", ...)`: status enum changed from `_STATUSES` to `[*_STATUSES, "archived"]`
- Tests: 6/6 passed (TestFromAC_MoveTaskArchived), 96 total passed in regression suite
- Ruff: clean
- Coverage: all AC paths covered by TestFromAC_MoveTaskArchived

[[2026-04-04]] Sat 16:50
## Review Evidence

### Tests
- Task tests (test_mcp_kanban_move_task_588.py): **6/6 passed**
- Package regression (test_server.py + test_tool_annotations_494.py): **69/69 passed**
- No failures, no warnings.

### Lint
- `ruff check packages/mcp-kanban/src/ tests/test_mcp_kanban_move_task_588.py` → **All checks passed!**

### Coverage
- Archive branch (lines 290–296): **covered** — happy path and rc!=0 error path
- Archive ValidationError path (lines 297–299): **uncovered** — untested defensive path, symmetric with pre-existing untested move path. Informational only.
- Move path (lines 299–308): covered by pre-existing `test_server.py::test_move_task_success_passes_args`

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `move_task(status="archived")` calls `kanban-md archive` | server.py:290–295 — branches on `"archived"`, calls `_run_kanban(app_ctx, "archive", task_id)` | `test_archived_status_routes_to_archive_command` + `test_archived_status_does_not_invoke_move_command` | PASS |
| `"archived"` not forwarded as CLI arg | server.py:291 — only `task_id` passed after `"archive"` | `test_archived_status_word_not_passed_as_cli_arg` | PASS |
| All other statuses use `kanban-md move` | server.py:299–302 — move path unchanged; `_patch_params` at line 510 `[*_STATUSES, "archived"]`; existing `test_move_task_success_passes_args` exercises move path | `test_move_task_status_param_enum_includes_archived` + pre-existing regression | PASS |
| Error from archive surfaced via ToolError | server.py:292–294 — `rc != 0` → `raise ToolError(stderr.strip())` | `test_archived_error_raises_tool_error` + `test_archived_error_message_from_stderr` | PASS |
| Unit tests cover archive path and move paths | 6/6 AC tests + 69/69 regression | implicit | PASS |

### Pass 1 Checks
- **5.0 AC-to-Test Coverage**: 4/4 AC lines mapped to tests that would fail on violation. COVERED.
- **5.1 Security**: `task_id` passed as positional arg to `asyncio.create_subprocess_exec` (no `shell=True`) — no injection risk. No secrets, no path traversal. CLEAN.
- **5.2 TestFromAC Integrity**: No modifications to `TestFromAC_MoveTaskArchived` detected (test file is new/untracked). PRESERVED.
- **5.3 Test Quality**: All tests ADEQUATE–STRONG. Assertions would fail on wrong behavior. STRONG.
- **5.4 Data Safety**: Single subprocess call, no shared state, no race conditions. CLEAN.
- **5.5 Implementation Path Gap**: ValidationError on archive path (lines 297–299) untested — defensive path, symmetric with pre-existing untested move path. INFORMATIONAL only.
- **5.7 Builder Process**: 1 build cycle, clean. CLEAN.

### Deductions
- −0.01 ValidationError branch on archive path (lines 297–299) uncovered (informational, not a FAIL)

### Verdict
Confidence: **0.95 → PASS**

[[2026-04-04]] Sat 17:15
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | `move_task` now accepts "archived"; `copilot-instructions.md` has no MCP tool parameter tables — no change needed. `h-mcp-kanban/SKILL.md` tool summary updated to reflect archive capability |
| 2 | Module docstrings | Yes | Updated | `server.py` `move_task` docstring updated to mention archive path; all other public functions untouched |
| 3 | External attribution | No | N/A | Builder notes reference no external patterns |
| 4 | CLI changes | No | N/A | No user-facing CLI commands changed |
| 5 | Research doc | No | N/A | No research doc produced for this task |

### Files Updated
- `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` — docstring only
- `.github/skills/h-mcp-kanban/SKILL.md` — tool summary row for `move_task`

### Commits
- `2b668ae` — feat: support archived status in move_task MCP tool (#588, builder) [belatedly committed]
- `e1206ca` — docs: update move_task docstring and skill summary for archive support (#588, doc-writer)

### Scratch Files
None found (`docs/scratch/588-*`).

[[2026-04-04]] Sat 18:17
@C:\Users\p362329\AppData\Local\Temp\1\588-audit.md

[[2026-04-04]] Sat 18:17
Audited: 4/4 AC lines PASS with test and code evidence. 96/96 mcp-kanban tests pass, no task-scope regressions in full suite. AC quality 4/5. Confidence .98.
