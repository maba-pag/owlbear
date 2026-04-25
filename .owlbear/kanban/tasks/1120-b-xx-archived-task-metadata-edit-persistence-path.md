---
id: 1120
title: 'B-XX: Archived-task metadata edit persistence path'
status: in-progress
priority: important
created: 2026-04-24T23:12:27.011812+00:00
updated: 2026-04-25T01:23:17.086937+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-24]]
Placeholder — created by architect during #1070 review. Needs edit_task to populate body, tags, deps, status.
[[2026-04-24]]
## Research
- Research doc: .owlbear/research/archived-edit-persistence.md
- Sources: 7 studied, 5 high-relevance (all internal codebase and brief authority)
- Recommendation: Option A -- _find_task_path archive fallback + write_task target_dir param (confidence: 0.85)
- Follow-up tasks created: #1121 (RED tests), #1122 (GREEN fix) at research
- Decision requests: none (T1 autonomous -- persistence bug fix, no arch change)

## Challenge Results
- Challenger: FALLBACK -- trivial persistence bug fix, no architecture alternatives to challenge

## Key Findings
Two independent defects block archived-task edit persistence:
1. Core edit_task calls _find_task_path(task_id, self._tasks_dir) which only searches tasks/, not archive/
2. write_task in storage.py always writes to tasks/, never archive/
Both MCP server and Cockpit consumers are affected. Validation paths work correctly (26 tests GREEN), only the success path is broken. D7 vs R5 scope tension resolved in favor of R5 (full edit access on archived tasks subject to S4).
[[2026-04-24]]
## Acceptance Criteria

- [x] Research doc `.owlbear/research/archived-edit-persistence.md` complete with failure chain analysis, scope decision (R5 over D7), and implementation recommendation (Option A)
- [x] Follow-up tasks #1121 (RED) and #1122 (GREEN) created with verifiable AC at research status
- [x] Defects D1 (`_find_task_path` tasks-only lookup) and D2 (`write_task` tasks-only target) documented with root cause

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research-only task; implementation split into #1121 (RED) and #1122 (GREEN) |
| Interface clarity | PASS | AC added above; research deliverables clearly defined |
| Dependency correctness | PASS | No deps on #1120; follow-ups depend correctly (#1121→#1070, #1122→#1121) |
| Module layering | PASS | Research task, no code changes |
| TDD compliance | PASS | Follow-ups have proper RED/GREEN split |
| KISS/YAGNI | PASS | Minimal scope — bug fix with two atomic tasks |
| Premise challenge | PASS | Both defects D1 and D2 verified in engine.py L975 and storage.py L373 |
| Pattern consistency | PASS | Option A follows existing show_task archive fallback pattern |
| Security surface | PASS | No new boundaries; write_task already has validate_path_containment |
| Single domain | PASS | kanban engine domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| edit_task on archived task | _find_task_path misses archive/ | FileNotFoundError | No (D1) | Edit fails silently |
| write_task after archived edit | Writes to tasks/ instead of archive/ | N/A (wrong dir) | No (D2) | Duplicate file created |
| edit_task rollback on archived task | rollback write_task also targets tasks/ | N/A | No (D2) | Rollback creates orphan in tasks/ |

Note: rollback path (engine.py L1019-1024) also needs archive-aware target_dir — covered by #1122 AC "written to archive/ dir, not tasks/" but builder should verify rollback uses same target_dir.

### Challenge Results
- Challenger: FALLBACK — trivial persistence bug fix, no architecture alternatives to challenge; research already noted FALLBACK
- Architect response: accepted — verified both defects directly in codebase; Option A is minimal KISS-aligned fix

### Verdict: APPROVE
### Action Taken: Advanced #1120 to todo. TAG NEEDED: `research` (pass-through for test-writer). edit_task MCP tool unavailable to architect — orchestrator must add tag before test-writer dispatch.
[[2026-04-24]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_archived_edit_1120.py
- Classes: TestFromAC_ArchivedTaskEditPersistence
- Tests per category: happy 8, edge 0, error 0, boundary 3
- Total: 11 tests, all FAIL (FileNotFoundError at engine._find_task_path — D1)
- ruff: clean

**AC coverage (from #1121 spec):**
| AC | Tests | Status |
|----|-------|--------|
| AC-1 archival_reason update | test_..._result_updated, test_..._reread_from_archive | FAIL (D1) |
| AC-2 archival_refs update | test_..._result_updated, test_..._reread_from_archive | FAIL (D1) |
| AC-3 append_body | test_..._result_contains_text, test_..._reread_from_archive | FAIL (D1) |
| AC-4 engine.edit_task priority | test_core_engine_..._result_updated, test_core_engine_..._reread_from_archive | FAIL (D1) |
| AC-5 file location | test_..._stays_in_archive_dir, test_..._no_duplicate_in_tasks_dir | FAIL (D1) |
| AC-6 timestamp advances | test_..._updated_timestamp_advances | FAIL (D1) |
| AC-7 S4 gate | EXCLUDED — validation fires in AgentView before D1; ERR_COMPLETED_REQUIRES_DONE already GREEN in existing suites |

**Note on task scope:** #1120 is a research/architecture task (all AC checked). Tag `research` was not added (architect note: edit_task unavailable). Tests were written using #1121's AC specification as the task-writer was dispatched here directly. #1121 remains at `research` status — orchestrator should either close it or advance it to `todo` for any additional coverage gaps the builder identifies.
[[2026-04-25]]
## Builder Notes
- Implementation: added archive fallback option in `_find_task_path` and used it in `KanbanEngine.edit_task`; added `target_dir` support to `write_task`; persisted edit/rollback writes to the originating directory (`tasks/` or `archive/`).
- Implementation files: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`.
- Tests: 11/11 `TestFromAC_ArchivedTaskEditPersistence` passed (`serve/kanban/tests/test_engine_archived_edit_1120.py`).
- Coverage: not measured in this scoped run (pytest + lint verification only).
- Ruff: clean on touched source files and task test file.
- Evidence summary: D1 fixed by archive fallback lookup in edit path; D2 fixed by directory-targeted write path so archived edits stay in `archive/` and do not create duplicate files in `tasks/`.
[[2026-04-25]]
## Review Evidence
Scope note: task #1120 is a research shell, but implementation and TestFromAC work were routed here directly. For behavior review, I anchored the contract to the implementation AC in sibling tasks #1121 and #1122.

### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_engine_archived_edit_1120.py` and `serve/kanban/tests/test_engine_create_edit_1070.py`: 42 passed, 0 failed, 0 skipped

### Lint
- ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/tests/test_engine_archived_edit_1120.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`

### Coverage
- overall: 36%
- `owlbear_kanban.engine`: 34%
- `owlbear_kanban.storage`: 61%
- Gate result: FAIL (<90% on both touched modules)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-1 archival_reason round-trip | `test_agentview_edit_archived_archival_reason_result_updated`, `test_agentview_edit_archived_archival_reason_reread_from_archive` (`serve/kanban/tests/test_engine_archived_edit_1120.py:157-199`) | Yes | COVERED |
| AC-2 archival_refs round-trip | `test_agentview_edit_archived_archival_refs_result_updated`, `test_agentview_edit_archived_archival_refs_reread_from_archive` (`serve/kanban/tests/test_engine_archived_edit_1120.py:205-250`) | No. Tests seed `[2]`, re-apply `[2]`, then only assert equality / membership at `serve/kanban/tests/test_engine_archived_edit_1120.py:226` and `serve/kanban/tests/test_engine_archived_edit_1120.py:250` | LAX |
| AC-3 append_body round-trip | `test_agentview_edit_archived_append_body_result_contains_text`, `test_agentview_edit_archived_append_body_reread_from_archive` (`serve/kanban/tests/test_engine_archived_edit_1120.py:256-298`) | Yes | COVERED |
| AC-4 core priority round-trip | `test_core_engine_edit_archived_priority_result_updated`, `test_core_engine_edit_archived_priority_reread_from_archive` (`serve/kanban/tests/test_engine_archived_edit_1120.py:303-345`) | Yes | COVERED |
| AC-5 archive placement / no duplicate | `test_edit_archived_file_stays_in_archive_dir`, `test_edit_archived_no_duplicate_created_in_tasks_dir` (`serve/kanban/tests/test_engine_archived_edit_1120.py:351-397`) | Yes | COVERED |
| AC-6 updated timestamp advances | `test_edit_archived_updated_timestamp_advances` (`serve/kanban/tests/test_engine_archived_edit_1120.py:403-424`) | Partially. The test checks only the returned Task, not a reread from `archive/` | LAX |
| AC-7 S4 gate | `test_archived_completed_reason_requires_terminal_status` (`serve/kanban/tests/test_engine_create_edit_1070.py:437-452`) | Yes; exact `ERR_COMPLETED_REQUIRES_DONE` code is asserted | COVERED |
| AC-8 archive fallback after cache population | No task-owned test pre-populates `_id_to_filename` before calling `edit_task`; cache is populated at `serve/kanban/src/owlbear_kanban/engine.py:730` and `_find_task_path` short-circuits at `serve/kanban/src/owlbear_kanban/engine.py:1535-1541` before fallback at `serve/kanban/src/owlbear_kanban/engine.py:1547-1550` | No | MISSING |
| AC-9 backwards-compatible `write_task(..., target_dir=None)` default | No scoped test exercises omitted `target_dir`; implementation is only read from code at `serve/kanban/src/owlbear_kanban/storage.py:355-372` | No | MISSING |

#### Security Review
- No issues found. The change adds no subprocess, eval, deserialization, or new dependency surface, and `write_task` still validates path containment before writing (`serve/kanban/src/owlbear_kanban/storage.py:355-408`).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ArchivedTaskEditPersistence::*` | Builder notes list only source-file changes (`.owlbear/kanban/tasks/1120-b-xx-archived-task-metadata-edit-persistence-path.md:96-101`); no weakened or removed assertions detected in the current TestFromAC file | PRESERVED |
| `test_agentview_edit_archived_archival_refs_*` | No builder weakening detected, but the RED-phase assertions remain lax (`serve/kanban/tests/test_engine_archived_edit_1120.py:205-250`) | PRESERVED (LAX FROM RED) |
| `test_archived_completed_reason_requires_terminal_status` | Exact error-code assertion still present (`serve/kanban/tests/test_engine_create_edit_1070.py:437-452`) | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC-2 reread test only checks membership (`serve/kanban/tests/test_engine_archived_edit_1120.py:250`) after reusing the same seeded value |
| Negative / error-path coverage | WEAK | Task-owned archived-edit suite is success-path only; rollback of archived edits is not exercised (`serve/kanban/tests/test_engine_archived_edit_1120.py:145-424`) |
| Manual mutation resistance | WEAK | Removing `record.archival_refs = list(archival_refs)` at `serve/kanban/src/owlbear_kanban/engine.py:1021-1024` would still leave AC-2 tests green |
| Test independence | STRONG | Each test uses a fresh tmp-path board |
| Descriptive names | STRONG | Test names encode condition and expected behavior clearly |

#### Data Safety
- No observed data-safety defect in the shipped code path. The residual issue is proof: the archived-edit rollback branch exists at `serve/kanban/src/owlbear_kanban/engine.py:1031-1034`, but no task-owned test demonstrates it.

#### Implementation-Aware Gaps
- Remaining implementation miss: `_find_task_path()` returns `self._tasks_dir / self._id_to_filename[int_id]` when the ID cache is populated (`serve/kanban/src/owlbear_kanban/engine.py:1535-1541`), which bypasses archive fallback (`serve/kanban/src/owlbear_kanban/engine.py:1547-1550`). `show_task()` already contains stale-cache recovery for the same condition (`serve/kanban/src/owlbear_kanban/engine.py:809-824`). Result: warm-cache / long-lived engine instances can still fail to edit archived tasks after the cache is populated. AC-8 is not fully satisfied.
- Archived-edit rollback proof is missing. `edit_task()` now writes and rolls back to `target_dir` at `serve/kanban/src/owlbear_kanban/engine.py:1028` and `serve/kanban/src/owlbear_kanban/engine.py:1034`, but existing atomicity tests only prove live-task edit rollback (`serve/kanban/tests/test_engine_atomicity_1104.py:155-186`, `serve/kanban/tests/test_engine_atomicity_1104.py:448-465`).
- Backwards-compatible default `write_task(..., target_dir=None)` behavior is untested. The default is implemented at `serve/kanban/src/owlbear_kanban/storage.py:355-372`, and unchanged callers still omit the parameter at `serve/kanban/src/owlbear_kanban/engine.py:912`, `serve/kanban/src/owlbear_kanban/engine.py:1069`, `serve/kanban/src/owlbear_kanban/engine.py:1077`, `serve/kanban/src/owlbear_kanban/engine.py:1085`, `serve/kanban/src/owlbear_kanban/engine.py:1127`, `serve/kanban/src/owlbear_kanban/engine.py:1138`, `serve/kanban/src/owlbear_kanban/engine.py:1164`, `serve/kanban/src/owlbear_kanban/engine.py:1169`, `serve/kanban/src/owlbear_kanban/engine.py:1287`, `serve/kanban/src/owlbear_kanban/engine.py:1308`, `serve/kanban/src/owlbear_kanban/engine.py:1355`, and `serve/kanban/src/owlbear_kanban/engine.py:1362`, but the task-owned suite does not prove the default path.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Prior Review Evidence sections | 0 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Archive lookup policy is duplicated between `show_task()` stale-cache recovery (`serve/kanban/src/owlbear_kanban/engine.py:809-824`) and `_find_task_path()` (`serve/kanban/src/owlbear_kanban/engine.py:1523-1552`). That divergence is what left the warm-cache gap.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `AgentView.edit_task(<archived>, archival_reason="dropped")` succeeds; re-read shows updated reason | quality-runner green run + round-trip assertions at `serve/kanban/tests/test_engine_archived_edit_1120.py:157-199` | `test_agentview_edit_archived_archival_reason_result_updated`, `..._reread_from_archive` | PASS |
| `AgentView.edit_task(<archived>, archival_refs=[other_id])` succeeds; re-read shows updated refs | implementation sets `record.archival_refs = list(archival_refs)` at `serve/kanban/src/owlbear_kanban/engine.py:1021-1024`; tests pass, but proof is weak because they reuse `[2]` (`serve/kanban/tests/test_engine_archived_edit_1120.py:205-250`) | `test_agentview_edit_archived_archival_refs_result_updated`, `..._reread_from_archive` | PASS |
| `AgentView.edit_task(<archived>, append_body="Note")` succeeds; re-read shows appended body | green round-trip tests at `serve/kanban/tests/test_engine_archived_edit_1120.py:256-298` | `test_agentview_edit_archived_append_body_result_contains_text`, `..._reread_from_archive` | PASS |
| Core `engine.edit_task(<archived>, priority="critical")` succeeds; re-read shows updated priority | green round-trip tests at `serve/kanban/tests/test_engine_archived_edit_1120.py:303-345` | `test_core_engine_edit_archived_priority_result_updated`, `..._reread_from_archive` | PASS |
| File persists in `archive/` dir, NOT in `tasks/` dir | explicit file-placement assertions at `serve/kanban/tests/test_engine_archived_edit_1120.py:351-397` | `test_edit_archived_file_stays_in_archive_dir`, `test_edit_archived_no_duplicate_created_in_tasks_dir` | PASS |
| `updated` timestamp advances on successful edit | returned Task `updated` changes at `serve/kanban/tests/test_engine_archived_edit_1120.py:403-424`; persistence proof is partial | `test_edit_archived_updated_timestamp_advances` | PASS |
| S4 gate still enforced for `archival_reason="completed"` | exact `ERR_COMPLETED_REQUIRES_DONE` assertion at `serve/kanban/tests/test_engine_create_edit_1070.py:437-452` | `test_archived_completed_reason_requires_terminal_status` | PASS |
| Core `edit_task` finds archived task files via `_find_task_path` archive fallback | cold-engine path works, but warm-cache path remains broken because `_find_task_path()` returns stale cached tasks path before archive fallback (`serve/kanban/src/owlbear_kanban/engine.py:1535-1541`, `1547-1550`) while `show_task()` handles that case (`serve/kanban/src/owlbear_kanban/engine.py:809-824`) | no task-owned stale-cache test | FAIL |
| `write_task` accepts optional `target_dir` param (defaults to `tasks/` for backwards compat) | signature and default at `serve/kanban/src/owlbear_kanban/storage.py:355-372`; unchanged callers still omit the parameter | no task-owned default-path test | PASS |
| Edited archived task file is written to `archive/` dir, not `tasks/` | explicit archive-path proof at `serve/kanban/tests/test_engine_archived_edit_1120.py:351-371` | `test_edit_archived_file_stays_in_archive_dir` | PASS |
| No duplicate file created in `tasks/` | explicit negative placement proof at `serve/kanban/tests/test_engine_archived_edit_1120.py:374-397` | `test_edit_archived_no_duplicate_created_in_tasks_dir` | PASS |
| All tests from RED task pass | quality-runner scoped run: 42 passed, 0 failed, 0 skipped | task-owned RED file included in scoped run | PASS |
| Existing `test_engine_create_edit_1070.py` regression tests still pass | quality-runner scoped run included `serve/kanban/tests/test_engine_create_edit_1070.py` with zero failures | regression file included in scoped run | PASS |
| ruff clean on changed files | quality-runner lint section: clean | changed files + scoped test files linted | PASS |

### Deductions
- -0.22: AC-8 remains incomplete on the warm-cache path because `_find_task_path()` short-circuits on `_id_to_filename` before archive fallback.
- -0.08: AC-2 proof is lax; the task-owned tests would stay green if the archival-refs assignment were removed.
- -0.05: archived-edit rollback path is unproven.
- -0.05: backwards-compatible `write_task(..., target_dir=None)` behavior is untested.
- -0.08: coverage gate failed (`owlbear_kanban.engine` 34%, `owlbear_kanban.storage` 61%).

### Confidence: 0.52
### Verdict: FAIL
### Action
Reject to `in-progress`. Builder should fix the warm-cache `_find_task_path()` short-circuit and add non-weakened proof for the stale-cache fallback, archived-edit rollback, and default `write_task(..., target_dir=None)` path without weakening existing TestFromAC assertions.
[[2026-04-25]]
## Builder Notes
- Implementation: updated archive-aware path resolution in `serve/kanban/src/owlbear_kanban/engine.py` so stale `_id_to_filename` cache entries do not bypass archive fallback; explicit archived-task `archival_reason`/`archival_refs` edits are accepted in AgentView no-op gating.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`.
- Tests: quality-runner scoped pass, 48 passed / 0 failed (`serve/kanban/tests/test_engine_archived_edit_1120.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`, `tests/test_engine_create_edit_1072.py`).
- ruff: clean on touched source and scoped test files.
- Coverage (quality-runner): `owlbear_kanban.engine` 36%, `owlbear_kanban.storage` 61% (below 90% gate).
- Evidence summary: warm-cache archive fallback defect in `_find_task_path` is fixed; archived-edit regression tests are green; however pipeline coverage gate is not met.
- Reject reason to test-writer: add targeted coverage that raises touched-module coverage to gate level, especially stale-cache archive fallback behavior and archived-edit persistence edge cases not currently represented strongly enough in module coverage accounting.
[[2026-04-25]]
## Test-Writer Notes

**Test file:** `serve/kanban/tests/test_engine_archived_edit_1120.py`
**Class:** `TestFromAC_ArchivedTaskEditPersistence`

**6 supplementary tests added** (17 total in file, all PASS):

| Category | Tests | Purpose |
|----------|-------|---------|
| AC-2 strict proof | 2 | Change refs from [2] → [3]; exact equality asserted — would fail if `record.archival_refs = list(archival_refs)` were removed |
| AC-6 on-disk proof | 1 | Re-reads timestamp from archive/ (not just return value) |
| AC-8 warm-cache | 1 | Warms `_id_to_filename` via `list_tasks()`, then moves file to archive/ without engine; `edit_task` must still succeed via fallback |
| Rollback | 1 | `activity_log=True` engine; patches `append_activity_event` → OSError; verifies original content restored in `archive/`, no duplicate in `tasks/` |
| write_task default path | 1 | `write_task(task, kanban_dir)` without `target_dir` must write to `tasks/` (backwards compat) |

**AC coverage gaps addressed:**
- AC-2: lax proof (seed=[2], edit=[2]) → replaced by strict change-value test
- AC-6: return-only proof → added on-disk reread proof
- AC-8: warm-cache bypass → now tested
- Rollback: archive-targeted rollback write — now tested
- Backwards-compat default path — now tested

**Note on RED/GREEN phase:** All 6 new tests are GREEN against the already-fixed implementation (builder round 2). These are supplementary proof tests added post-implementation per reviewer and builder request. ruff: clean. Regression suite (78 tests): all pass.