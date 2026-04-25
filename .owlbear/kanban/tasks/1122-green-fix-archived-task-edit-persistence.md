---
id: 1122
title: 'GREEN: fix archived-task edit persistence'
status: in-progress
priority: important
created: 2026-04-24T23:20:30.734062+00:00
updated: 2026-04-25T12:02:38.770476+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent:
depends_on:
- 1121
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — extends #1120 research.
Module: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`

Fix the archived-task edit persistence path so edits to tasks in `archive/` are read from and written back to the archive directory.

## Acceptance Criteria

- [ ] Core `edit_task` finds archived task files via `_find_task_path` archive fallback
- [ ] `write_task` accepts optional `target_dir` param (defaults to `tasks/` for backwards compat)
- [ ] Edited archived task file is written to `archive/` dir, not `tasks/`
- [ ] No duplicate file created in `tasks/`
- [ ] All tests from RED task pass (GREEN phase)
- [ ] Existing tests in `test_engine_create_edit_1070.py` still pass (regression)
- [ ] ruff clean on changed files

[[2026-04-25]]
## Research
- Research doc: .owlbear/research/archived-edit-persistence.md (existing, from #1120)
- Sources: 3 studied (engine.py, storage.py, test file), all high-relevance internal codebase
- Recommendation: No action needed — GREEN implementation already complete from #1120 builder cycles (confidence: 0.95)
- Follow-up tasks created: none (implementation is done)
- Decision requests: none (T1 autonomous — persistence bug fix already shipped)

## Challenge Results
- Challenger: FALLBACK — implementation already complete, nothing to challenge

## Key Findings
All 7 AC items verified against current codebase:
1. `_find_task_path` uses `include_archive_fallback=True` in `edit_task` (engine.py L982)
2. `write_task` accepts `target_dir` param with backwards-compat default (storage.py L355)
3. `target_dir = task_path.parent` routes writes to originating directory (engine.py L983)
4. Rollback path also uses `target_dir` (engine.py L1040)
5. 16/16 RED tests GREEN, 31/31 regression tests GREEN, ruff clean
6. Implementation was completed during #1120 builder cycles — no new code changes needed for #1122

Note: the test file currently has 16 tests (core AC proof). The supplementary coverage tests (27 storage + 92 engine) documented in #1120's later test-writer notes were not persisted to disk. The architect/builder should decide whether to restore them.
[[2026-04-25]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Archive edit persistence only |
| Interface clarity | PASS | AC maps to specific function params and behavior |
| Dependency correctness | PASS | #1121 (RED tests) is archived/done |
| Module layering | PASS | engine.py → storage.py, correct direction |
| TDD compliance | PASS | #1121 RED tests exist and are done |
| KISS/YAGNI | PASS | Minimal fix to existing path, no new features |
| Premise challenge | PASS | Bug fix for real persistence path issue |
| Pattern consistency | PASS | Uses existing `_find_task_path` fallback and `write_task` patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | `scope:kanban` only |

### Codebase Evidence
- `edit_task` at engine.py L982: `_find_task_path(task_id, self._tasks_dir, include_archive_fallback=True)`
- `target_dir = task_path.parent` at engine.py L983 routes writes to originating directory
- `write_task` at storage.py L355 accepts `target_dir` with backwards-compat default `None`
- Rollback path at engine.py L1040 also uses `target_dir`
- `_find_task_path` (L1546-1584) archive fallback globs `_archive_dir`
- RED tests: `serve/kanban/tests/test_engine_archived_edit_1120.py` (16+ AC-mapped tests)
- Regression tests: `serve/kanban/tests/test_engine_create_edit_1070.py` (31 tests)

### AC Refinement
AC-6 corrected: "Existing 26 tests" → "Existing tests" — live file has 31, count was stale. Operative criterion is "still pass," not exact count.

### Challenge Results
- Challenger: reconsider (0.58)
- Architect response: rebutted on 3 of 4 concerns, accepted AC count fix
  - Evidence drift: accepted — refined AC-6 to remove stale count
  - Phase routing: rebutted — GREEN task is the execution evidence gate; builder runs quality-runner to produce independent verification
  - Verification gap: rebutted — architect verifies AC/architecture, not test outcomes; execution evidence is builder's job
  - History blindside: rebutted — #1122 has independent AC; #1120 gate history is irrelevant

### Verdict: APPROVE (with AC-6 refinement)
### Action Taken: Refined AC-6, advanced to todo
[[2026-04-25]]
## Test-Writer Notes
- Non-impl pass-through: `tdd:green` builder task — test-writer's RED phase was completed in #1121.
- RED test file: `serve/kanban/tests/test_engine_archived_edit_1120.py` — 52 tests, all PASS (verified live).
- AC coverage: all 6 AC lines covered by `TestFromAC_ArchivedTaskEditPersistence` (16 core tests) plus `TestFromAC_StorageCoveragePaths` (36 supplementary storage/engine tests). Contrary to the task body note, supplementary tests ARE present on disk.
- No new tests written — any tests targeting the already-implemented interfaces would immediately pass, violating RED-phase requirements.
- Passing through to in-progress for builder quality verification.
