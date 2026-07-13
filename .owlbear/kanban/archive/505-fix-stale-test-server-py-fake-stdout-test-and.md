---
id: 505
title: Fix stale test_server.py _FAKE_STDOUT test and output_schema underspec
status: archived
priority: medium
created: 2026-03-31 22:15:57.237239+02:00
updated: 2026-04-02 07:01:51.462365+02:00
started: 2026-04-02 07:01:51.003773+02:00
completed: 2026-04-02 07:01:51.003773+02:00
tags:
- scope:mcp
- test
- quality
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] test_list_tasks_success_passes_args in test_server.py passes a valid JSON list (e.g. [{id:1,title:T,status: archived,priority:important,tags:[],class:standard}]) to _patch_run(stdout=...) as a local override, NOT by changing the global _FAKE_STDOUT constant (which other tool tests depend on). The test asserts on the lean JSON success path output (stripped fields absent) instead of raw stdout equality.
- [ ] output_schema for list_tasks includes an items definition that enumerates the fields present in the lean output (all KanbanTask fields minus the strip set: body, file, created, updated). At minimum items must be {type: object, properties: {...}} with the lean field names -- not just {type: object}.
- [ ] Add edge-case test: list_tasks with empty JSON array [] from kanban-md returns [] (empty JSON array string).
- [ ] Add explicit test for the JSONDecodeError fallback path: when kanban-md stdout is non-JSON (e.g. plain text), list_tasks returns the raw stdout string unchanged. This prevents branch coverage regression from AC1.

## Context

Identified during #479 architecture review (challenger C2, C3, C5). The _FAKE_STDOUT = 'board output' string triggers JSONDecodeError fallback since #478 switched to --json parsing. The output_schema monkey-patch uses private FastMCP internals (mcp._tool_manager._tools) with no public API guarantee.

[[2026-04-01]] Wed 08:38
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** N/A -- not research-driven (originated from #479 challenger findings)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: test uses valid JSON via local override | Precise, verifiable -- specifies local override to avoid cascade | Kept |
| AC2: output_schema items definition | Refined -- must enumerate lean field names, not just type:object | Refined |
| AC3: empty array edge case | Verifiable edge case for JSON parsing path | Kept |
| AC4: JSONDecodeError fallback test (NEW) | Added to prevent branch coverage regression from AC1 fix | Added |

### Architecture Notes
- Single domain: mcp-kanban (test_server.py + server.py output_schema)
- Follows existing pattern: _FAKE_TASK_JSON already demonstrates valid JSON fixture approach in test_server.py
- The lean output strips {body, file, created, updated} from full KanbanTask -- items schema must reflect this subset
- Private API usage (mcp._tool_manager._tools) is pre-existing tech debt, not in scope here
- TDD flow: test-writer handles AC1/AC3/AC4 (test changes) + writes failing test for AC2; builder adds items to output_schema (AC2)
- Tags test + quality are correct non-impl pass-through tags

### Changes Made
- Refined AC1: specified local override approach (not global _FAKE_STDOUT change)
- Refined AC2: specified items must enumerate lean field names, not just type:object
- Added AC4: explicit JSONDecodeError fallback test to maintain branch coverage
- Moving to todo

### Dependencies
- No depends_on needed (standalone quality fix)
- Verified: no upstream blockers

### Challenge Results
- Challenger: reconsider (confidence 0.62)
- Key challenges: C1 (FAKE_STDOUT blast radius), C2 (items underspec), C3 (fallback coverage regression)
- Architect response: Accepted C1/C2/C3 -- refined AC1 with local override guidance, refined AC2 with field enumeration requirement, added AC4 for fallback coverage. Rebutted C4 (empty array redundancy) -- edge cases provide documentation value. Rebutted Alternative A (LeanTask model) -- YAGNI, hand-crafted dict sufficient.

[[2026-04-01]] Wed 14:39
## Test-Writer Notes
- Non-implementation task (tagged test, quality) -- no new tests applicable.
- Architect confirmed tags test + quality are correct non-impl pass-through tags.
- AC1/AC3/AC4 are test file modifications (test_server.py); AC2 is output_schema source fix (server.py).
- Builder handles all AC directly per architect TDD flow note.
- Passing through to builder.

[[2026-04-02]] Thu 04:42
## Builder Notes
- Files changed: packages/mcp-kanban/tests/test_server.py, packages/mcp-kanban/src/owlbear_mcp_kanban/server.py
- AC1: Fixed test_list_tasks_success_passes_args to use local _FAKE_LIST_JSON override; asserts lean output (created/updated stripped)
- AC2: output_schema updated with items.properties enumerating 17 lean field names
- AC3: Added test_list_tasks_empty_array_returns_empty_json in TestBuilderDiscovered
- AC4: Added test_list_tasks_non_json_stdout_returns_raw_stdout in TestBuilderDiscovered
- AC2 test: Added test_list_tasks_output_schema_has_items_with_lean_fields in TestBuilderDiscovered
- Tests: 58 passed (was 55, +3 new), coverage 88% on server.py (pre-existing gaps unrelated to this task)
- Lint: ruff clean

[[2026-04-02]] Thu 04:49
## Review Evidence

### Test Results
- pytest: 58 passed, 0 failed
- Scope: packages/mcp-kanban/tests/test_server.py

### Lint Results
- ruff on server.py + test_server.py: All checks passed

### Coverage
- server.py: 88% (pre-existing gaps from #472/#473/#497)
- AC1-4 paths are all covered

### TestFromAC Comparison
test_list_tasks_success_passes_args: STRENGTHENED (uses _FAKE_LIST_JSON, lean JSON asserts)

### AC Compliance
AC1: test uses _FAKE_LIST_JSON local override, asserts created/updated absent -- PASS
AC2: output_schema items.properties has 17 lean fields, no created/updated -- PASS
AC3: empty array test asserts result == '[]' -- PASS
AC4: non-JSON test asserts raw stdout returned -- PASS

### Verdict: PASS (.92)

-t

[[2026-04-02]] Thu 04:49
## Review Evidence

pytest: 58 passed, 0 failed
ruff (server.py + test_server.py): All checks passed
coverage server.py: 88% (pre-existing gaps, AC1-4 paths covered)

TestFromAC Comparison:
- test_list_tasks_success_passes_args: STRENGTHENED (uses _FAKE_LIST_JSON local override, lean JSON asserts; global _FAKE_STDOUT unchanged)

AC Compliance:
- AC1: test uses _FAKE_LIST_JSON local override, asserts created/updated absent from lean JSON -- PASS
- AC2: output_schema items.properties has 17 lean field names (id/title/status/priority/class/tags/blocked etc), created/updated absent; test_list_tasks_output_schema_has_items_with_lean_fields verifies -- PASS
- AC3: test_list_tasks_empty_array_returns_empty_json patches stdout='[]', asserts result == '[]' -- PASS
- AC4: test_list_tasks_non_json_stdout_returns_raw_stdout patches plain text, asserts raw stdout returned -- PASS

Security: No issues. No injection risks, no hardcoded secrets.

Verdict: PASS confidence .92

[[2026-04-02]] Thu 07:01
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: test uses local _FAKE_LIST_JSON override | test_server.py L228: _patch_run(stdout=_FAKE_LIST_JSON), lean asserts (created/updated absent); global _FAKE_STDOUT unchanged | PASS |
| AC2: output_schema items with lean fields | server.py L196: 17 properties (id,title,...); body/file/created/updated excluded. Test at L1105 verifies | PASS |
| AC3: empty array edge case | test_server.py L1122: patches stdout='[]', asserts result == '[]' | PASS |
| AC4: JSONDecodeError fallback test | test_server.py L1133: patches plain text stdout, asserts raw return | PASS |

### Test Results
- pytest (scoped): 58 passed, 0 failed
- pytest (full suite): 42 failures in test_quality_runner_wiring*.py (unrelated in-progress task, not #505)
- ruff: clean

### AC Quality Score: 5/5
AC was precise (local override approach, lean field enumeration, edge cases, regression prevention via AC4). No builder improvisation needed.

### Deduction breakdown: none -- all AC verified with specific evidence, lint clean, reviewer evidence present
### Confidence: 1.0
### Action: archive
