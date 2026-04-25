---
id: 1121
title: 'RED: archived-task edit persistence tests'
status: in-progress
priority: important
created: 2026-04-24T23:20:26.935285+00:00
updated: 2026-04-25T01:19:48.889330+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent:
depends_on:
- 1070
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — extends #1120 research.
Module: `serve/kanban/tests/test_engine_archived_edit.py`

Test that `edit_task` on archived tasks persists correctly to the archive directory. Covers both AgentView and core engine paths.

## Acceptance Criteria

- [ ] `AgentView.edit_task(<archived>, archival_reason="dropped")` succeeds; re-read from archive shows updated reason
- [ ] `AgentView.edit_task(<archived>, archival_refs=[other_id])` succeeds; re-read shows updated refs
- [ ] `AgentView.edit_task(<archived>, append_body="Note")` succeeds; re-read shows appended body
- [ ] Core `engine.edit_task(<archived>, priority="critical")` succeeds; re-read shows updated priority
- [ ] File persists in `archive/` dir, NOT in `tasks/` dir (no duplicate)
- [ ] `updated` timestamp advances on successful edit
- [ ] S4 gate still enforced: `edit_task(<archived>, archival_reason="completed")` raises ValidationError
- [ ] All tests fail (RED phase)

[[2026-04-25]]
## Research

**Finding:** Task already satisfied — tests exist at `serve/kanban/tests/test_engine_archived_edit_1120.py` (committed `e2b0ef3a`), 11 tests covering all 7 non-excluded AC items with full round-trip verification (result + reread from archive).

**State:** Tests were RED at commit time (FileNotFoundError on D1). Currently GREEN because #1122's fix exists as uncommitted working-tree changes in engine.py (+54/-24) and storage.py (+10/-2). Fix implements Option A from `.owlbear/research/archived-edit-persistence.md`: `_find_task_path` archive fallback + `write_task` target_dir param.

**AC-7 exclusion validated:** S4 `ERR_COMPLETED_REQUIRES_DONE` fires in AgentView before D1 path; existing test `test_archived_completed_reason_requires_terminal_status` in `test_engine_create_edit_1070.py` covers it.

**Classification:** T1 autonomous — no new follow-ups needed. #1122 (GREEN fix) is the only remaining task; its changes are already in the working tree awaiting commit.

**Decision requests:** None.
[[2026-04-25]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for one defect area (archived-task edit persistence) |
| Interface clarity | PASS | AC specifies exact method calls and expected return values |
| Dependency correctness | PASS | #1070 archived/done |
| Module layering | PASS | Test-only task, no production code changes |
| TDD compliance | PASS | This IS the RED phase; #1122 (GREEN) depends on it |
| KISS/YAGNI | PASS | Minimal test scope covering documented defects D1+D2 |
| Premise challenge | PASS | Tests target real defects found in #1120 research |
| Pattern consistency | PASS | Follows existing tmp_path/_make_view helper pattern from test_engine_create_edit_1070.py |
| Security surface | PASS | No security boundary involved |
| Single domain | PASS | kanban engine domain only |

### AC Assessment
| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 (archival_reason) | COVERED — 2 tests (result + reread) | None |
| AC-2 (archival_refs) | DEFECTIVE — tests seed archival_refs=[2] then edit to [2] (same value). Engine no-op check (line 2064) will raise ERR_NO_OP once D1 is fixed. Tests fail for wrong reason; GREEN fix in #1122 cannot make them pass. | **Test-writer must fix:** seed archival_refs=[] and edit to [2], or seed [2] and edit to [2,3] |
| AC-3 (append_body) | COVERED — 2 tests (result + reread) | None |
| AC-4 (core priority) | COVERED — 2 tests (result + reread) | None |
| AC-5 (archive dir) | COVERED — 2 tests (file exists + no duplicate) | None |
| AC-6 (timestamp) | COVERED — 1 test | None |
| AC-7 (S4 gate) | EXCLUDED — covered by existing test in test_engine_create_edit_1070.py:437 | Validated |
| AC-8 (all RED) | COVERED — tests were RED at commit (D1 FileNotFoundError) | None |

### Module Path Correction
Brief says `test_engine_archived_edit.py`; actual file is `test_engine_archived_edit_1120.py` (task-ID suffix convention). Test-writer should use the existing file.

### Challenge Results
- Challenger: reconsider (0.36)
- Challenges: (1) AC-2 no-op defect — ACCEPTED, added fix guidance; (2) phase integrity (currently GREEN due to uncommitted #1122 changes) — REBUTTED: transient workspace state, tests were RED at commit, pipeline tracks committed state; (3) deliverable drift (file naming) — REBUTTED: follows task-ID suffix convention; (4) unverified historical claim — REBUTTED: tests independently verified via file read
- Architect response: accepted challenge 1 (AC-2 test defect), rebutted challenges 2-4

### Verdict: APPROVE (REFINE + advance)
AC is sound. AC-2 test defect is an implementation bug the test-writer must fix (seed different initial refs). All other AC lines are precisely covered.
[[2026-04-25]]
## Test-Writer Notes

**File:** `serve/kanban/tests/test_engine_archived_edit_1120.py`
**Commit:** `9fd4e0da`

### Fix Applied (AC-2 Retry)
Architect flagged AC-2 defect: both refs tests seeded `archival_refs=[2]` then edited to `[2]` — engine ERR_NO_OP check rejects this once D1 is fixed, causing tests to fail for the wrong reason.

**Fix:** Added `task_id=3` as a second valid ref target; seeded refs `[2]`, edited to `[2, 3]`. Result assertion updated to `== [2, 3]`; reread assertion updated to `3 in reread.archival_refs`.

### Test Suite Shape
| Category | Count |
|----------|-------|
| AC-1 (archival_reason) | 2 |
| AC-2 (archival_refs) | 2 |
| AC-3 (append_body) | 2 |
| AC-4 (core engine priority) | 2 |
| AC-5 (archive dir / no duplicate) | 2 |
| AC-6 (timestamp) | 1 |
| **Total** | **11** |

### AC Coverage
| AC | Test(s) |
|----|---------|
| AC-1 | result_updated + reread_from_archive |
| AC-2 | result_updated + reread_from_archive (fixed: [2]→[2,3]) |
| AC-3 | result_contains_text + reread_from_archive |
| AC-4 | result_updated + reread_from_archive |
| AC-5 | file_stays_in_archive_dir + no_duplicate_in_tasks_dir |
| AC-6 | updated_timestamp_advances |
| AC-7 | EXCLUDED — covered by test_engine_create_edit_1070.py:437 |

### RED Phase Status
Tests were committed RED at `e2b0ef3a` (FileNotFoundError on D1). Currently GREEN due to uncommitted #1122 working-tree changes — architect validated this as transient state (pipeline tracks committed state). Ruff: clean.