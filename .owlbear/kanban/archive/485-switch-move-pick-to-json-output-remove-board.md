---
id: 485
title: Switch move/pick to JSON output, remove board_context — tests
status: archived
priority: medium
created: 2026-03-31 06:21:02.721636+02:00
updated: 2026-03-31 13:50:10.869919+02:00
started: 2026-03-31 13:49:52.496269+02:00
completed: 2026-03-31 13:49:52.496269+02:00
tags:
- scope:mcp
- type:test
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Add `--json` assertion to move_task success test (test_move_task_success_passes_args)
- [ ] Add `--json` assertion to pick_task success test (test_pick_task_success_passes_args)
- [ ] Remove board_context import and success test (test_board_context_success_no_extra_args)
- [ ] Remove board_context from parametrized error test (test_all_tools_return_error_string_on_non_zero_rc)
- [ ] move_task and pick_task --json assertion tests fail (expected RED until #489 implements)
- [ ] All other mcp-kanban tests pass (board_context removal is clean, no breakage)

## Context
TDD RED phase for #477. Pattern: show_task test already asserts --json in args.

## File Reference
- File: packages/mcp-kanban/tests/test_server.py
- show_task --json assertion pattern: ~L210
- board_context import: L30
- move_task success test: ~L249
- pick_task success test: ~L427
- board_context success test: ~L450
- board_context parametrized error entry: ~L483

[[2026-03-31]] Tue 07:16
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- not research-driven (T1 trivial change, .95 confidence, single approach)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add --json assertion to move_task test | Clear, verifiable, follows show_task pattern at ~L210 | Kept |
| Add --json assertion to pick_task test | Clear, verifiable, same pattern | Kept |
| Remove board_context import and success test | Clear, specific test named | Kept |
| Remove board_context from parametrized error test | Clear, specific fixture identified | Kept |
| All mcp-kanban tests pass (original) | Contradicts TDD RED -- 2 tests must fail until #489 | Rewritten: split into RED expectation + clean removal check |

### Architecture Notes
Single-file change in test_server.py. Follows established show_task --json assertion pattern. board_context removal is clean (zero consumers confirmed by research). TDD pairing correct: #485 (RED) precedes #489 (GREEN, depends_on: [485]).

### Changes Made
- Refined AC item 5: split into explicit RED failure expectation + clean removal verification
- Added file reference section with line numbers for test-writer

### Dependencies
- Verified: #489 (GREEN impl) depends_on [485] -- correct TDD ordering
- Verified: #477 (parent) is the owning task

[[2026-03-31]] Tue 11:40
## Builder Notes
- Files changed: packages/mcp-kanban/tests/test_server.py (committed by test-writer, no further changes needed)
- Tests: 27 passed, 2 failed (expected RED: test_move_task_success_passes_args, test_pick_task_success_passes_args)
- Evidence: RED state confirmed -- --json assertions for move_task and pick_task fail; board_context removal clean (27 pass)
- Fixes applied: None -- test-writer deliverable already committed and in correct state per AC

[[2026-03-31]] Tue 13:50
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Add --json to move_task test | L251: assert --json in args_used | PASS |
| Add --json to pick_task test | L439: assert --json in args_used | PASS |
| Remove board_context import+test | Import L28-36 clean, no board_context test | PASS |
| Remove board_context from error parametrize | 6 entries only (no board_context) | PASS |
| move/pick --json tests fail (RED) | 2 failed exactly as expected | PASS |
| All other mcp-kanban tests pass | 27 passed, 0 unexpected failures | PASS |

### Test Results
- pytest (scoped): 27 passed, 2 failed (expected RED)
- pytest (full suite): 1998 passed, 294 failed (all pre-existing RED from other tasks)
- ruff: All checks passed

### Architect Quality
AC quality score: 5 -- specific test names, line numbers, file ref, clear RED expectation

### Deduction breakdown: none -- all AC verified with evidence, lint clean, commit exists
### Confidence: 1.0
### Action: archive

## Commits
Deliverable committed upstream by test-writer:
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6f9fb9c | test | packages/mcp-kanban/tests/test_server.py | #485 |
