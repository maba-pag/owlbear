---
id: 620
title: 'Test: pick_tasks MCP tool gate logic and output format'
status: archived
priority: medium
created: 2026-04-05T01:30:52.3984607+02:00
updated: 2026-04-05T17:25:20.3856593+02:00
started: 2026-04-05T17:25:20.3856593+02:00
completed: 2026-04-05T17:25:20.3856593+02:00
tags:
    - scope:mcp
    - phase-2
    - test
parent: 619
class: standard
---

## Acceptance Criteria

- Tests cover `pick_tasks` MCP tool in owlbear-kanban server
- Test cases validate:
  - Basic pick: tasks in various statuses returned with task_id and status
  - Gate filtering: tasks failing atomicity/TDD/clarity gates are excluded
  - Limit: `limit=5` caps output at 5 entries
  - Default limit is 25
  - Sort order: critical+done-adjacent tasks appear before someday+ideation tasks
  - Empty board: returns empty dispatch list
  - Archived tasks excluded
  - Blocked/claimed tasks excluded (unblocked + unclaimed board read)
- Tests use the existing test patterns for MCP kanban tools (mock _run_kanban or use subprocess fixtures)
- Tests live in tests/test_pick_tasks_{task_id}.py

[[2026-04-05]] Sun 10:33
## Research
- Research doc: .owlbear/research/pick-tasks-test-design.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Mock _run_kanban pattern with 7 test classes covering all AC items (confidence: .90)
- Follow-up tasks created: none (all subtasks exist under #619)
- Decision requests: none

## Challenge Results
- Challenger: N/A — trivial T1 test task, no recommendation to challenge
- Tier: T1 (autonomous) — standard TDD RED test writing

## Key Findings for Test-Writer
- Mock pattern: `patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=(json_str, "", 0)))`
- pick_tasks calls _run_kanban once with: list --json --unblocked --not-blocked --unclaimed
- Gate logic migrated from planner/gates.py: atomicity (word-boundary "and"), TDD (## Test-Writer Notes), clarity (bullet AC for active statuses)
- Sort: (PRIORITY_RANK, STATUS_RANK) ascending — critical+done first, someday+ideation last
- Output: {"dispatch": [{"task_id": int, "status": str}]}
- 7 test classes: Signature, BasicPick, GateFiltering, Limit, SortOrder, EdgeCases, BoardFlags

[[2026-04-05]] Sun 11:07
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task: write failing tests for pick_tasks MCP tool |
| Interface clarity | PASS | AC enumerates 8 test scenarios with specific values (limit=5, default=25, sort order). Research doc supplements with mock pattern and JSON structure |
| Dependency correctness | PASS | No deps. #621 correctly depends on this task. Parent #619 is design doc (not blocker) |
| Module layering | PASS | Tests in tests/test_pick_tasks_620.py — follows test_mcp_kanban_list_tasks_472.py pattern |
| TDD compliance | PASS | This IS the TDD RED phase |
| KISS/YAGNI | PASS | 7 test classes mapped 1:1 to AC items |
| Premise challenge | PASS | Required for TDD pipeline — #621 depends on these tests |
| Pattern consistency | PASS | Mock pattern matches test_start_work_470.py and test_mcp_kanban_list_tasks_472.py |
| Security surface | PASS | Test-only task, no new system boundaries |
| Single domain | PASS | scope:mcp only |

### Codebase Evidence
- Mock: serve/mcp-kanban/tests/test_start_work_470.py L59-61 — AsyncMock + patch("owlbear_mcp_kanban.server._run_kanban")
- Gates: serve/orchestrator/src/owlbear/planner/gates.py — _AND_PATTERN, _AC_PATTERN, _CLARITY_STATUSES, check_gates()
- Sort: serve/orchestrator/src/owlbear/planner/selector.py — PRIORITY_RANK, STATUS_RANK, (prank,srank) ascending
- #621 AC specifies all 3 CLI flags: --unblocked --not-blocked --unclaimed

### AC Notes
- "Blocked/claimed tasks excluded" — test-writer should verify all 3 flags from #621: --unblocked, --not-blocked, --unclaimed
- "Archived tasks excluded" — verify absence of --archived flag (default excludes archived)
- Research edge cases (rc!=0, malformed JSON, all-gates-fail) are good boundary test additions

### Challenge Results
- Challenger: FALLBACK — challenger agent not in workspace agent roster
- Architect response: Proceed — T1 test task, established patterns, no design risk

### Verdict: APPROVE
### Action: backlog -> todo

[[2026-04-05]] Sun 12:38
## Test-Writer Notes
- Test file: `tests/test_pick_tasks_620.py`
- Classes: TestFromAC_PickTasksSignature (3), TestFromAC_PickTasksBasicPick (5), TestFromAC_PickTasksGateFiltering (8), TestFromAC_PickTasksLimit (4), TestFromAC_PickTasksSortOrder (3), TestFromAC_PickTasksEdgeCases (4), TestFromAC_PickTasksBoardFlags (6)
- Total: 33 tests, all FAIL (ImportError: cannot import name 'pick_tasks' from owlbear_mcp_kanban.server)
- Ruff: clean
- AC coverage: all 8 AC items covered (basic pick, gate filtering, limit=5, default=25, sort order, empty board, archived exclusion, blocked/claimed exclusion via flags)
- Mock pattern: `patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=(json_str, "", 0)))`
- Board flags verified: --unblocked, --not-blocked, --unclaimed present; --archived absent

[[2026-04-05]] Sun 12:57
## Builder Notes\n- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (1 file)\n- Changes: added `import re`, `pick_tasks` to `__all__`, gate constants + `_check_pick_gates()`, `@mcp.tool pick_tasks()` function\n- Test results: 33 passed, 0 failed\n- Lint: ruff clean (fixed SIM103 inline condition)\n- Coverage: pick_tasks lines fully covered (not in missing list); overall server.py at 31% because remaining tools have their own test files\n- Evidence: all 7 TestFromAC_* classes pass — Signature (3), BasicPick (5), GateFiltering (8), Limit (4), SortOrder (3), EdgeCases (4), BoardFlags (6)\n- No builder-discovered tests needed — AC coverage was exhaustive\n- No new dependencies added

[[2026-04-05]] Sun 15:09
## Review Evidence
### Test Results
- pytest: 33 passed, 0 failed (self-run via runTests, not builder self-report)

### Lint: clean (ruff check on server.py + test_pick_tasks_620.py — 0 errors)

### Coverage: pick_tasks code block (server.py lines ~509–566) fully covered; overall server.py 24.7% expected (other tools have their own test files)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Tests cover pick_tasks MCP tool | All 7 TestFromAC_* classes import pick_tasks | Yes — ImportError | COVERED |
| Basic pick: task_id and status in dispatch | test_dispatch_entries_have_task_id_and_status | Yes — value assertion 42 / "todo" | COVERED |
| Gate filtering: atomicity/TDD/clarity | TestFromAC_PickTasksGateFiltering (8 tests) | Yes — inclusion/exclusion assertions | COVERED |
| limit=5 caps output at 5 | test_limit_5_returns_exactly_5_when_available | Yes — == 5 | COVERED |
| Default limit is 25 | test_default_limit_is_25 + test_default_limit_caps_at_25 | Yes — signature default + count == 25 | COVERED |
| Sort order: critical/done before someday/ideation | TestFromAC_PickTasksSortOrder (3 tests) | Yes — ids.index comparison | COVERED |
| Empty board returns empty dispatch | test_empty_board_returns_empty_dispatch | Yes — result == {"dispatch": []} | COVERED |
| Archived excluded | test_does_not_pass_archived_flag | Yes — "--archived" not in call args | COVERED |
| Blocked/claimed excluded | test_passes_unblocked_flag, test_passes_not_blocked_flag, test_passes_unclaimed_flag | Yes — flag presence assertions | COVERED |

#### Security Review
- No hardcoded secrets
- _run_kanban uses subprocess with list args (no shell=True) — injection-safe
- json.loads only — no unsafe deserialization
- No new dependencies added
- No issues

#### TestFromAC Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 33 TestFromAC_* tests | None — test-writer's classes, names, assertions identical | PRESERVED |

#### Test Quality
- Assertion specificity: STRONG (value-level assertions: task_id==42, len()==5, len()==25, ids.index(2)<ids.index(1), result=={"dispatch":[]}, set(keys)=={"task_id","status"})
- Error-path coverage: STRONG (rc!=0, malformed JSON, all-gates-fail)
- Mutation resistance: STRONG (each gate branch, each flag, each limit boundary individually tested)
- Test independence: STRONG (each test patches _run_kanban independently, no shared mutable state)
- Test names: STRONG (descriptive docstrings on every method)

#### Data Safety: No issues

#### Implementation-Aware Gap Analysis
- All 3 gate branches (_PICK_AND_PATTERN, TDD, clarity) individually exercised
- Word-boundary false-positive for "and" tested (test_atomicity_gate_passes_word_boundary_false_positive)
- Clarity-gate status exemption (ideation) tested
- All 3 CLI exclusion flags + json flag covered
- Sort key (priority_rank, status_rank) tuple tested with combined scenario
- Limit slice boundary tested (exactly 5 of 10, exactly 25 of 30)
- Minor informational: no test for in-progress task where TDD gate passes but clarity gate fails (prose-only Test-Writer Notes section). Not reachable in practice since all Test-Writer Notes include bullet counts. Not flagging as a defect.

#### Builder Process: CLEAN — 1 builder iteration, clean first pass

### Verdict
Confidence: .97 → PASS

## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | pick_tasks added to kanban server. Updated h-mcp-kanban SKILL.md: count 7to8, added tool row. copilot-instructions.md has no tool registry. |
| 2 | Module docstrings | Yes | Verified | pick_tasks docstring accurate. _check_pick_gates docstring accurate. |
| 3 | External attribution | No | N/A | Gate logic from internal planner/gates.py only. |
| 4 | CLI changes | No | N/A | MCP tool only. README references mcp-kanban generically. |
| 5 | Research doc | Yes | Verified | .owlbear/research/pick-tasks-test-design.md exists and linked in task body. |

### Files Updated
- share/skills/h-mcp-kanban/SKILL.md - tool count 7to8 added pick_tasks row

### Commit
9baff38 docs: update h-mcp-kanban skill with pick_tasks tool (#620, doc-writer)

[[2026-04-05]] Sun 15:19
Docs gate passed. Updated h-mcp-kanban SKILL.md: pick_tasks added to tool table, count 7→8. Docstrings verified accurate. Research doc exists and linked. No scratch files. Commit: 9baff38.

## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Tests cover pick_tasks MCP tool | 7 TestFromAC_* classes in test_pick_tasks_620.py, 33 tests | PASS |
| Basic pick: task_id and status | TestFromAC_PickTasksBasicPick (5 tests) | PASS |
| Gate filtering: atomicity/TDD/clarity excluded | TestFromAC_PickTasksGateFiltering (8 tests) | PASS |
| limit=5 caps output | test_limit_5_returns_exactly_5_when_available | PASS |
| Default limit is 25 | test_default_limit_is_25 + test_default_limit_caps_at_25 | PASS |
| Sort order: critical+done before someday+ideation | TestFromAC_PickTasksSortOrder (3 tests) | PASS |
| Empty board: empty dispatch list | test_empty_board_returns_empty_dispatch | PASS |
| Archived tasks excluded | test_does_not_pass_archived_flag | PASS |
| Blocked/claimed excluded | test_passes_unblocked_flag, _not_blocked_flag, _unclaimed_flag | PASS |
| Test patterns: mock _run_kanban | All tests use patch(owlbear_mcp_kanban.server._run_kanban) | PASS |
| Test file: tests/test_pick_tasks_620.py | File exists, 484 lines | PASS |

### Test Results
- pytest (task-scoped): 33 passed, 0 failed
- pytest (full suite): 2878 passed, 432 failed (pre-existing systemic), 18 skipped - 0 failures in task scope
- ruff: All checks passed (server.py + test_pick_tasks_620.py)

### Architect Quality: 5/5
AC enumerates 8 test scenarios with concrete values (limit=5, default=25, sort order). Research doc supplements with mock pattern, JSON structure, and gate logic sources. Clean implementation path, no improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (all 11 PASS)
- Lint violations: 0
- AC quality: 5/5 (no deduction)
- Reviewer evidence: present, detailed, .97 PASS
- Full-suite failures in task scope: 0
- Note: test-writer + builder left deliverables uncommitted; committed by auditor (bf789e3, 3fcb62c)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| bf789e3 | test | tests/test_pick_tasks_620.py | #620 |
| 3fcb62c | feat | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | #620 |
| 9baff38 | docs | share/skills/h-mcp-kanban/SKILL.md | #620 |

[[2026-04-05]] Sun 17:25
Audited: all 11 AC lines verified with PASS, 33/33 tests pass, full suite clean in task scope, ruff clean, AC quality 5/5. Committed test-writer (bf789e3) and builder (3fcb62c) leftovers.
