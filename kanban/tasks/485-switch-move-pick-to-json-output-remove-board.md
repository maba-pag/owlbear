---
id: 485
title: Switch move/pick to JSON output, remove board_context — tests
status: todo
priority: needed
created: 2026-03-31T06:21:02.7216362+02:00
updated: 2026-03-31T07:16:58.8359399+02:00
tags:
    - scope:mcp
    - type:test
    - phase-2
class: standard
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
