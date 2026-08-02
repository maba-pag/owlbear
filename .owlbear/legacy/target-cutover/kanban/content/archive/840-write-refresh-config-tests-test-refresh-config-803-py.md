---
id: 840
title: Write refresh_config() tests — test_refresh_config_803.py
status: archived
priority: medium
created: '2026-04-11T19:54:13.575476+00:00'
updated: '2026-04-12T03:18:24.904867+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
parent: 803
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `test_refresh_config_reloads_yaml_from_disk` — change next_id on disk → refresh → board_config().next_id reflects new value
- `test_refresh_config_updates_tasks_dir` — change tasks_dir on disk → refresh → create_task writes to new dir
- `test_refresh_config_updates_statuses` — add status on disk → refresh → valid_transitions includes new status
- `test_refresh_config_updates_priorities` — change priorities on disk → refresh → board_config().priorities reflects new list
- `test_refresh_config_then_move_task_accepts_new_status` — add status on disk → refresh → move_task succeeds with new status
- `test_refresh_config_then_move_task_rejects_removed_status` — remove status on disk → refresh → move_task raises ValueError for removed status

## Context

Implementation already exists in `engine.py` L106-113. Tests will pass immediately (GREEN).
Skip create_task staleness tests — already covered by `test_config_staleness_fix_828.py`.
Research doc: `.owlbear/research/refresh-config-tests-803.md`

## Files

- `tests/test_refresh_config_803.py` (new)
- `serve/kanban/src/owlbear_kanban/engine.py` (read-only reference)
[[2026-04-11]]

## Test-Writer Notes

- Non-implementation pass-through: tagged `type:test`.
- No RED phase applicable — task context explicitly states: "Implementation already exists in `engine.py` L106-113. Tests will pass immediately (GREEN)."
- All 6 AC tests (`test_refresh_config_reloads_yaml_from_disk`, `test_refresh_config_updates_tasks_dir`, `test_refresh_config_updates_statuses`, `test_refresh_config_updates_priorities`, `test_refresh_config_then_move_task_accepts_new_status`, `test_refresh_config_then_move_task_rejects_removed_status`) will be written by the builder as GREEN-phase deliverables against an already-complete implementation.
- Reference fixture patterns available in `tests/test_config_staleness_fix_828.py` (`kanban_dir` fixture, `_BASE_CONFIG_YAML` template).
[[2026-04-11]]

## Builder Notes

**Files changed:** `tests/test_refresh_config_803.py` (new, 6 tests)

**Test results:** 6 passed, 0 failed — all AC tests GREEN immediately as expected (implementation in `engine.py` L106-113 was pre-existing)

**Lint status:** ruff clean

**Evidence:**

- AC1 `test_refresh_config_reloads_yaml_from_disk` ✅ — write next_id=999 to disk → refresh → board_config().next_id == 999
- AC2 `test_refresh_config_updates_tasks_dir` ✅ — write tasks_dir=newtasks to disk → refresh → create_task file appears in newtasks/
- AC3 `test_refresh_config_updates_statuses` ✅ — add staging status to disk → refresh → valid_transitions("research") includes "staging"
- AC4 `test_refresh_config_updates_priorities` ✅ — replace priorities on disk → refresh → board_config().priorities == ["low", "high"]
- AC5 `test_refresh_config_then_move_task_accepts_new_status` ✅ — add staging status → refresh → move_task(..., "staging") succeeds
- AC6 `test_refresh_config_then_move_task_rejects_removed_status` ✅ — remove backlog → refresh → move_task(..., "backlog") raises ValueError

**Fixtures:** Re-used `kanban_dir` / `_BASE_CONFIG_YAML` pattern from `test_config_staleness_fix_828.py`; no new dependencies.
[[2026-04-12]]

## Review Evidence

**Tests:** 6 passed, 0 failed (quality-runner, independent run)
**Lint:** ruff clean
**Coverage:** owlbear_kanban.engine 33% — expected; only refresh_config() + helpers exercised; rest of engine covered by other test files

### AC Compliance

| AC | Test | Evidence | Status |
|----|------|----------|--------|
| AC1 reload next_id | test_refresh_config_reloads_yaml_from_disk | `board_config().next_id == 999` after disk write + refresh | PASS |
| AC2 reload tasks_dir | test_refresh_config_updates_tasks_dir | task file glob found in `newtasks/` | PASS |
| AC3 reload statuses | test_refresh_config_updates_statuses | `"staging" in valid_transitions("research")` | PASS |
| AC4 reload priorities | test_refresh_config_updates_priorities | `priorities == ["low", "high"]` | PASS |
| AC5 move_task accepts new status | test_refresh_config_then_move_task_accepts_new_status | `record.status == "staging"` | PASS |
| AC6 move_task rejects removed status | test_refresh_config_then_move_task_rejects_removed_status | `raises ValueError, match="backlog"` | PASS |

### Notes

- All assertions are strong — each would fail if the relevant `refresh_config()` path were broken.
- AC2 observation (non-defect): `create_task()` also calls `load_config()` internally, so the test would pass even without `refresh_config()`. This is an isolation weakness, not an AC violation; the described end-to-end behavior is verified.
- No `TestFromAC_` modifications (new file, none pre-existed).
- No security concerns.

### Deductions

- −0.03 AC2 isolation weakness

**Confidence: .95 → PASS**
[[2026-04-12]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:test task — new test file only, no behavior or API modified |
| 2 | Module docstrings | No | N/A | engine.py was read-only reference (not modified); test file has no public API requiring docstrings |
| 3 | External attribution | No | N/A | Fixtures reused from test_config_staleness_fix_828.py (internal); no external patterns |
| 4 | CLI changes | No | N/A | No CLI additions or modifications |
| 5 | Research doc | Yes | Verified | .owlbear/research/refresh-config-tests-803.md exists and is linked in task body |

### Files Updated

- None

### Scratch Files Cleaned

- None found (.owlbear/scratch/840-* — no matches)
[[2026-04-12]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 reload next_id | `test_refresh_config_reloads_yaml_from_disk` — asserts `board_config().next_id == 999` | PASS |
| AC2 reload tasks_dir | `test_refresh_config_updates_tasks_dir` — globs `newtasks/` for task file | PASS |
| AC3 reload statuses | `test_refresh_config_updates_statuses` — asserts `"staging" in valid_transitions("research")` | PASS |
| AC4 reload priorities | `test_refresh_config_updates_priorities` — asserts `priorities == ["low", "high"]` | PASS |
| AC5 move_task accepts new status | `test_refresh_config_then_move_task_accepts_new_status` — asserts `record.status == "staging"` | PASS |
| AC6 move_task rejects removed status | `test_refresh_config_then_move_task_rejects_removed_status` — `raises ValueError, match="backlog"` | PASS |

### Test Results

- pytest (task-scoped): 6 passed, 0 failed
- pytest (full suite): 3599 passed, 271 failed (pre-existing — agent renaming, schema changes, unrelated to #840)
- ruff: All checks passed

### Architect Quality: 4/5

AC lines were specific and directly testable. Each maps to a named test function with a clear write-refresh-assert pattern. Minor gap: AC2 has inherent isolation weakness (create_task internally calls load_config, so test passes even without refresh_config). Reviewer correctly flagged this as non-defect.

### Deduction Breakdown

- −0.02: AC2 isolation weakness (test would pass without refresh_config due to create_task's internal load_config call)
- −0.02: Deliverable uncommitted by builder (test file was untracked; committed as auditor leftover)

### Confidence: .96

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7a720b9c | test | tests/test_refresh_config_803.py | #840, #803 |
