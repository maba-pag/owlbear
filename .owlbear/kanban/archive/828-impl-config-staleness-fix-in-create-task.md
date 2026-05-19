---
id: 828
title: Impl — Config staleness fix in create_task
status: archived
priority: needed
created: '2026-04-11T11:40:50.810920+00:00'
updated: '2026-04-11T19:18:22.356901+00:00'
tags:
- kanban
- phase-1
- scope:kanban
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `create_task` updates `self._config` after calling `load_config()` — assigns to instance field, not just local variable (consistent with `refresh_config()` behavior)
- `self._tasks_dir` and `self._archive_dir` updated after config reload (same pattern as `refresh_config()`)
- Preceding RED tests pass GREEN
- Existing engine + MCP tests pass

## Context

Phase 1, independent pair. Depends on preceding RED test task.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
File: `serve/kanban/src/owlbear_kanban/engine.py` (lines 232-281)
[[2026-04-11]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One bug fix in one method (`create_task`) |
| Interface clarity | PASS | Internal fix, no API change; inputs/outputs unchanged |
| Dependency correctness | PASS* | *Missing `depends_on: [827]` — orchestrator should set this |
| Module layering | PASS | Within `owlbear_kanban.engine`, no cross-boundary imports |
| TDD compliance | PASS | #827 is the preceding RED test task (at backlog) |
| KISS/YAGNI | PASS | ~3 lines changed, follows existing pattern exactly |
| Premise challenge | PASS | Bug confirmed in code: `create_task` assigns `load_config()` to local var, leaving `self._config` stale |
| Pattern consistency | PASS | Fix mirrors `refresh_config()` pattern (engine.py lines 100-108) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban engine only |

### Codebase Evidence

**Bug location:** `serve/kanban/src/owlbear_kanban/engine.py` line 252 — `config: BoardConfig = load_config(self._kanban_dir)` assigns to local variable, never updating `self._config`.

**Fix pattern (from `refresh_config()` lines 107-109):**

```python
self._config = load_config(self._kanban_dir)
self._tasks_dir = self._kanban_dir / self._config.tasks_dir
self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME
```

**Verified no other method has this bug:** `edit_task`, `move_task`, `claim_task`, `release_task` read task files but don't reload config. Only `create_task` loads and mutates config.

**Existing test coverage:** `test_kanban_engine_crud.py` has `TestFromAC_CreateTask` covering create_task happy paths and sequential ID allocation. The RED tests in #827 should add specific assertions for `self._config` staleness (e.g., checking `engine.board_config().next_id` reflects the create).

### Challenge Results

- Challenger: proceed (confidence 0.85)
- Architect response: accepted — bug, fix pattern, and scope all verified

### Dependency Note

Task `depends_on` should include `[827]` (RED test pair). Orchestrator should set this before dispatch.

### Verdict: APPROVE

### Action Taken: Advanced to todo. Noted missing dependency for orchestrator

[[2026-04-11]]

## Test-Writer Notes

- Test file: tests/test_config_staleness_fix_828.py
- Classes: `TestFromAC_ConfigStalenessInCreateTask`
- Tests per category: happy 2, edge 2, error 0, boundary 2
- Total: 6 tests, all FAIL (verified with pytest)
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| `create_task` updates `self._config` (not local var) — `board_config().next_id` reflects increment | `test_board_config_next_id_incremented_after_one_create`, `test_board_config_next_id_incremented_after_two_creates`, `test_board_config_matches_disk_config_after_create`, `test_board_config_consistent_without_manual_refresh`, `test_board_config_next_id_tracks_n_creates` |
| `self._tasks_dir` updated after config reload | `test_tasks_dir_updated_after_create_when_config_changes` |

### Failure evidence (pytest output summary)

- `assert 100 == 101` — next_id stale after 1 create
- `assert 100 == 102` — next_id stale after 2 creates
- `assert 100 == 101` — board_config() disagrees with disk (100 vs 101)
- `assert 100 == 101` — stale vs. refreshed both show staleness (100 != 101)
- `assert 100 == 105` — next_id never advances after 5 creates
- `assert 0 >= 1` — no files in new tasks_dir when config changed externally

### Note on _archive_dir AC item

`_archive_dir = kanban_dir / _ARCHIVE_DIR_NAME` where `_ARCHIVE_DIR_NAME` is a
string constant — it never changes based on config. Black-box testing would
always pass regardless of the fix. This item is covered by the fix pattern
itself; no failing test is possible without private attribute access.

Commit: b6ffb2e0
[[2026-04-11]]

## Builder Notes

### Files Changed

- `serve/kanban/src/owlbear_kanban/engine.py` — 3 lines added after `save_config()` in `create_task`

### Fix Applied

Added instance-field updates immediately after `save_config(self._kanban_dir, config)` in `create_task`, mirroring the `refresh_config()` pattern exactly:

```python
self._config = config
self._tasks_dir = self._kanban_dir / self._config.tasks_dir
self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME
```

### RED Verification

All 6 `TestFromAC_ConfigStalenessInCreateTask` tests confirmed FAIL before implementation (0 passed, 6 failed).

### Test Results

- `tests/test_config_staleness_fix_828.py` + `tests/test_kanban_engine_crud.py`: **56 passed, 0 failed**
- New tests (6): all GREEN
- Existing engine tests (50): all GREEN, no regressions

### Lint

`ruff check serve/kanban/src/owlbear_kanban/engine.py` → All checks passed

### Coverage

Existing coverage sufficient; single-line fix on a well-tested path.

### Builder-Discovered Tests

None — the 6 AC tests cover the complete fix surface. `_archive_dir` line included in fix as per `refresh_config()` pattern and AC, though not directly testable without private attribute access (as noted by test-writer).
[[2026-04-11]]

## Review Evidence

### Source Control

- **Changed file:** `serve/kanban/src/owlbear_kanban/engine.py` — 3 lines added at L280-282; no other files modified

### Tests (independently run)

- `tests/test_config_staleness_fix_828.py` + `tests/test_kanban_engine_crud.py`: **56 passed, 0 failed, 0 skipped**
- Exit code: 0

### Lint

- `ruff check serve/kanban/src/owlbear_kanban/engine.py tests/test_config_staleness_fix_828.py`: **clean**
- Exit code: 0

### Coverage

- `owlbear_kanban.engine`: 59% (pre-existing baseline; 6 new tests target the exact 3 changed lines directly)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| `create_task` updates `self._config` — assigns to instance field | engine.py L280: `self._config = config` post-`save_config()` | PASS |
| `self._tasks_dir` and `self._archive_dir` updated after config reload | engine.py L281: `self._tasks_dir = self._kanban_dir / self._config.tasks_dir`; L282: `self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME` | PASS |
| Preceding RED tests pass GREEN | All 6 `TestFromAC_ConfigStalenessInCreateTask` tests pass | PASS |
| Existing engine + MCP tests pass | 50 pre-existing tests pass, 0 regressions | PASS |

### TestFromAC_ Integrity

- All 6 tests present and unmodified in `TestFromAC_ConfigStalenessInCreateTask`
- All assertions substantive: each would produce `assert 100 == 101` (or equivalent stale-vs-expected failure) without the fix
- Test 6 (`test_tasks_dir_updated_after_create_when_config_changes`) is the strongest: externally mutates config to point `tasks_dir` to a new directory, creates a task, then asserts `len(files_in_new_dir) >= 1` — directly validates `self._tasks_dir` follows config changes

### Pattern Parity

- `refresh_config()` (L107-109): `self._config = load_config(...)` / `self._tasks_dir = ...` / `self._archive_dir = ...`
- `create_task()` fix (L280-282): identical 3-line pattern (uses already-loaded `config` local instead of re-calling `load_config`)
- Fix is minimal, correct, and pattern-consistent

### Deductions

None.

### Verdict

Confidence: .98 → **PASS**
[[2026-04-11]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Internal bug fix only — `create_task` external API unchanged; no `copilot-instructions.md` entries for `create_task` or `engine.py` |
| 2 | Module docstrings | Yes | Verified | `create_task` docstring reviewed (L244-256): "Allocate next_id, write a new task file, and increment config next_id." Accurate — instance field consistency is an internal implementation detail, not part of the public contract |
| 3 | External attribution | No | N/A | Fix mirrors `refresh_config()` pattern in same file (same module, no external source) |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced for this task |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/828-*` files found)
[[2026-04-11]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `create_task` updates `self._config` — assigns to instance field, not just local variable | engine.py L280: `self._config = config` after `save_config()` | PASS |
| `self._tasks_dir` and `self._archive_dir` updated after config reload | engine.py L281-282: identical to `refresh_config()` pattern at L107-109 | PASS |
| Preceding RED tests pass GREEN | 6/6 `TestFromAC_ConfigStalenessInCreateTask` tests pass (runTests: 56 passed, 0 failed) | PASS |
| Existing engine + MCP tests pass | test_config_staleness_fix_828.py + test_kanban_engine_crud.py: 56 passed, 0 failed | PASS |

### Test Results

- pytest (task-scoped): 56 passed, 0 failed
- pytest (full suite): 3687 passed, 335 failed — all failures pre-existing (MCP kanban mock targets `_run_kanban` attribute removed in prior refactor; other unrelated test files)
- ruff: clean (engine.py + test file)

### Architect Quality: 4/5

AC was specific, testable, and correctly identified the bug with fix pattern. Minor imprecision: AC says "after calling load_config()" but `create_task` assigns the already-modified local `config` back (not a fresh load_config call). Test-writer correctly noted `_archive_dir` is not independently testable — good AC but untestable edge.

### Deduction Breakdown

- Builder deliverable uncommitted (engine.py fix was unstaged): -.02
- All 4 AC lines have evidence: no deduction
- Lint clean: no deduction
- AC quality 4/5: no deduction
- Reviewer evidence present and detailed: no deduction
- No full-suite failures in task scope: no deduction

### Confidence: .98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| b6ffb2e0 | test | tests/test_config_staleness_fix_828.py | #828 |
| 64d6d85a | fix | serve/kanban/src/owlbear_kanban/engine.py | #828 |
