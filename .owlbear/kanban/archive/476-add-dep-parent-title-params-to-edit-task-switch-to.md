---
id: 476
title: Add dep/parent/title params to edit_task, switch to JSON output
status: archived
priority: medium
created: 2026-03-31 06:06:19.073728+02:00
updated: 2026-04-03 04:12:30.996049+02:00
started: 2026-04-03 04:11:19.471823+02:00
completed: 2026-04-03 04:11:19.471823+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] `add_dep: int = 0` parameter passes `--add-dep {value}` to `_run_kanban` when value > 0; omitted when 0 or default
- [ ] `remove_dep: int = 0` parameter passes `--remove-dep {value}` when > 0; omitted when 0
- [ ] `parent: int = 0` parameter passes `--parent {value}` when > 0; omitted when 0
- [ ] `title: str = ""` parameter passes `--title {value}` when non-empty; omitted when empty
- [ ] `edit_task` unconditionally appends `--json` to args and returns `KanbanTask` (Pydantic model via `model_validate_json`)
- [ ] `edit_task` ToolAnnotations include explicit `idempotentHint=False` (add_dep/remove_dep are non-idempotent)
- [ ] outputSchema for `edit_task` uses `KanbanTask.model_json_schema(by_alias=True)`
- [ ] Tests: each new param (add_dep, remove_dep, parent, title) has positive test (flag present when value set) and negative test (flag absent at default)
- [ ] Tests: `--json` is always present in edit_task args
- [ ] Tests: edit_task return type is `KanbanTask` instance
- [ ] Tests: `_FAKE_TASK_JSON` fixture includes `depends_on`, `parent`, `blocked`, `body` fields for realistic validation
- [ ] mcp-kanban SKILL.md documents all params including add_dep, remove_dep, parent, title

## Design Notes

- add_dep/remove_dep are single int per call (call multiple times for multiple deps) -- deliberate MCP convention for atomic operations
- Existing tags param stays as replace-all; no add_tag/remove_tag added
- parent: 0 sentinel means do not change -- there is no clear parent operation (kanban-md CLI limitation; follow-up if needed)
- Return type change from str to KanbanTask is non-breaking: MCP protocol serves both content (text) and structuredContent (typed JSON)
- Implementation already committed (a960d92) -- test-writer writes tests against existing code, builder verifies GREEN

## Architecture Patterns

- Follow show_task/move_task/pick_task precedent: --json + KanbanTask.model_validate_json + ToolError on failure
- outputSchema override pattern at module bottom (L507-515 in server.py) already includes edit_task

[[2026-04-03]] Fri 00:14
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- research classified T1 (mechanical, no design decisions, .90 confidence)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| add_dep: int=0, passes flag when > 0 | Precise, verifiable, matches CLI | Keep |
| remove_dep: int=0, passes flag when > 0 | Precise, verifiable | Keep |
| parent: int=0, passes flag when > 0 | Precise, verifiable | Keep |
| title: str="", passes flag when non-empty | Precise, verifiable | Keep |
| Unconditional json output, returns KanbanTask | Precise, follows show_task pattern | Keep |
| idempotentHint=False on ToolAnnotations | NEW from challenger | Added |
| outputSchema uses model_json_schema(by_alias=True) | Precise, already in code | Keep |
| Tests: positive + negative per new param | Expanded from vague original | Refined |
| Tests: json flag always present | Extracted from original AC6 | Refined |
| Tests: return type is KanbanTask | Extracted from original AC6 | Refined |
| Tests: fake fixture includes new fields | NEW from challenger | Added |
| SKILL.md documents all params | Already done, verifiable | Keep |

### Architecture Notes
Single-domain (scope:mcp). All changes confined to edit_task in mcp-kanban server.py + its tests.
Follows established patterns: show_task/move_task/pick_task already use json + KanbanTask + ToolError.
Implementation code already committed (a960d92): pipeline run will be test-writer RED then builder GREEN.
No new security surfaces: params are int/str values mapped to CLI flags via asyncio.create_subprocess_exec.
No dependency changes. No module layering violations.

### Changes Made
- Rewrote AC body: expanded vague "Tests cover" into 4 specific test AC lines
- Added idempotentHint=False AC line (challenger finding)
- Added fake fixture expansion AC line (challenger finding)
- Consolidated outputSchema addendum into main AC
- Removed duplicate Research sections from body

### Dependencies
- None listed, none needed. Task is self-contained within mcp-kanban package.

### Challenge Results
- Challenger: reconsider (confidence .62)
- Key challenges: (1) AC6 unmet tests, (2) missing idempotentHint, (3) parent:0 one-way limitation, (4) fake fixture missing fields
- Architect response: Accepted 2 and 4 (added to AC). Challenge 1 rebutted: test coverage is test-writer scope, not architect gate. Challenge 3 noted as follow-up, not in scope. Confidence recovered to .85 after refinements.

[[2026-04-03]] Fri 01:39
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_edit_task_476.py
- Classes (new): TestFromAC_EditTaskIdempotentHint, TestFromAC_JsonFlagAlwaysPresent, TestFromAC_FakeTaskJsonFixture
- Tests per category (new only): happy 8, edge 3, error 0, boundary 3
- Total: 40 tests (29 pre-existing PASS, 2 new FAIL, 9 new PASS)
- ruff: clean
- Failing tests: TestFromAC_EditTaskIdempotentHint (AC6 -- idempotentHint=None, not False)
- AC coverage:
  AC1 add_dep flag: TestFromAC_EditTaskFlagMapping (pre-existing)
  AC2 remove_dep flag: TestFromAC_EditTaskFlagMapping (pre-existing)
  AC3 parent flag: TestFromAC_EditTaskFlagMapping (pre-existing)
  AC4 title flag: TestFromAC_EditTaskFlagMapping (pre-existing)
  AC5 json + KanbanTask return: TestFromAC_EditTaskReturnsKanbanTask (pre-existing)
  AC6 idempotentHint=False: TestFromAC_EditTaskIdempotentHint (NEW -- 2 FAIL)
  AC7 outputSchema: TestFromAC_EditTaskOutputSchema (pre-existing)
  AC8 pos+neg per param: TestFromAC_EditTaskFlagMapping (pre-existing)
  AC9 json always present: TestFromAC_JsonFlagAlwaysPresent (NEW -- 4 PASS, impl committed)
  AC10 return type KanbanTask: TestFromAC_EditTaskReturnsKanbanTask (pre-existing)
  AC11 FAKE_TASK_JSON fixture: TestFromAC_FakeTaskJsonFixture (NEW -- 5 PASS, impl committed)
  AC12 SKILL.md params: TestFromAC_EditTaskSkillMdErrorGroup (pre-existing)

[[2026-04-03]] Fri 02:25
## Builder Notes
- Files changed: packages/mcp-kanban/src/owlbear_mcp_kanban/server.py (1 line)
- Change: added idempotentHint=False to edit_task ToolAnnotations decorator
- Tests: 40 passed, coverage 42% on server.py (scoped to task test file)
- Lint: ruff clean
- Evidence: test_idempotent_hint_is_explicitly_false + test_idempotent_hint_is_not_none now GREEN
- Fixes applied: ToolAnnotations(destructiveHint=False) -> ToolAnnotations(destructiveHint=False, idempotentHint=False)

[[2026-04-03]] Fri 03:15
## Review Evidence
**Reviewer:** reviewer | **Date:** 2026-04-03 | **Confidence:** .94

### Test Results
- pytest tests/test_mcp_kanban_edit_task_476.py: 40 passed, 0 failed

### Lint Results
- ruff check packages/mcp-kanban/ tests/test_mcp_kanban_edit_task_476.py: All checks passed!

### Coverage
- server.py overall 27% (task-scoped test file; pre-existing paths for append_body/unblock/release/timestamp tested in packages/mcp-kanban/tests/test_server.py)
- All edit_task branches introduced by this task (add_dep, remove_dep, parent, title, --json, idempotentHint) are fully covered

### Test-Writer AC Coverage
| AC | Mapped Tests | LAX? | Verdict |
|---|---|---|---|
| AC1 add_dep flag | TestFromAC_EditTaskFlagMapping::test_add_dep_passes/omitted | No | COVERED |
| AC2 remove_dep flag | TestFromAC_EditTaskFlagMapping::test_remove_dep_passes/omitted | No | COVERED |
| AC3 parent flag | TestFromAC_EditTaskFlagMapping::test_parent_passes/omitted | No | COVERED |
| AC4 title flag | TestFromAC_EditTaskFlagMapping::test_title_passes/omitted | No | COVERED |
| AC5 --json + KanbanTask return | TestFromAC_JsonFlagAlwaysPresent (4), TestFromAC_EditTaskReturnsKanbanTask (5) | No | COVERED |
| AC6 idempotentHint=False | TestFromAC_EditTaskIdempotentHint (2) | No | COVERED |
| AC7 outputSchema model_json_schema | TestFromAC_EditTaskOutputSchema (2) | No | COVERED |
| AC8 pos+neg per new param | Included in AC1-4 | No | COVERED |
| AC9 --json always present | TestFromAC_JsonFlagAlwaysPresent (4 tests) | No | COVERED |
| AC10 return type KanbanTask | TestFromAC_EditTaskReturnsKanbanTask (5) | No | COVERED |
| AC11 FAKE_TASK_JSON fixture | TestFromAC_FakeTaskJsonFixture (5) | No | COVERED |
| AC12 SKILL.md params | TestFromAC_EditTaskSkillMdErrorGroup::test_skill_md_edit_task_row_includes_new_params | No | COVERED |

### TestFromAC Comparison
Builder changed 1 line in server.py only (idempotentHint=False). Test file unchanged by builder.
| Class | Change | Assessment |
|---|---|---|
| TestFromAC_EditTaskIdempotentHint (2 tests) | Not modified by builder | PRESERVED |
| All other TestFromAC_ classes (38 tests) | Not modified by builder | PRESERVED |

### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | argv index checks, is False (not truthy), exact value matching |
| Error-path coverage | STRONG | 3 ToolError scenarios + ValidationError paths |
| Mutation resistance | STRONG | test_add_dep_omitted_when_zero catches > vs >= bugs |
| Test independence | STRONG | Fresh mocks per test |
| Descriptive names | STRONG | test_add_dep_passes_flag_and_value_when_positive |

### Security
- int params to CLI via asyncio.create_subprocess_exec (no shell=True): no injection risk
- str params as positional args: no injection risk
- No secrets, no path traversal, no deserialization risk

### Implementation-Aware Gap Analysis
Builder change is 1 line (adds idempotentHint=False). No new code paths introduced beyond what the AC mandates. All existing edit_task paths pre-tested in packages/mcp-kanban/tests/test_server.py.

### Verdict: PASS

[[2026-04-03]] Fri 03:23
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | edit_task return-type follows existing show_task/move_task pattern; SKILL.md has all new params per AC12 |
| 2 | Docstrings | Yes | Pass | edit_task docstring accurate and covers new params. No update needed. |
| 3 | docs/sources/overview.md | No | N/A | T1 mechanical task; no external patterns adopted |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | No | N/A | T1 classification -- no research phase |
| 6 | Scratch files | No | N/A | No docs/scratch/476-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-04-03]] Fri 04:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 add_dep flag | server.py L341-342: conditional flag pass | PASS |
| AC2 remove_dep flag | server.py L343-344: conditional flag pass | PASS |
| AC3 parent flag | server.py L345-346: conditional flag pass | PASS |
| AC4 title flag | server.py L324: in str_flags list | PASS |
| AC5 json + KanbanTask return | server.py L347 + L350 | PASS |
| AC6 idempotentHint=False | server.py L295 | PASS |
| AC7 outputSchema | server.py L512 loop includes edit_task | PASS |
| AC8-11 Tests | 40/40 pass: pos/neg per param, json always, return type, fixture | PASS |
| AC12 SKILL.md | SKILL.md L23: all params documented | PASS |

### Test Results
- pytest (task-scoped): 40 passed, 0 failed
- pytest (full suite): 3132 passed, 261 failed (all pre-existing, zero in task scope)
- ruff: clean for task scope (2 pre-existing violations in unrelated file)

### Upstream Commits Verified
- 575aa35 fix: set idempotentHint=False on edit_task ToolAnnotations (#476, builder)
- c8dfb62 test: add failing tests for edit_task AC gaps (#476, test-writer)
- 9eabb10 test: add flag-mapping tests for edit_task new params (#476, test-writer)
- a960d92 feat: edit_task returns KanbanTask and raises ToolError (#476, builder)
- 81d973e test: replace stale tests with revised-AC failing tests (#476, test-writer)

### AC Quality Score: 5/5
Specific, complete, led to clean implementation. Challenger gaps incorporated.

### Deduction breakdown: none
### Confidence: 1.00
### Action: archive

[[2026-04-03]] Fri 04:12
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c2b2ed8 | chore | kanban/tasks/476-*.md | #476 |
