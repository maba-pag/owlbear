---
id: 1443
title: 'P4-06: Replace next_id config allocation and hard-code activity logging'
status: archived
priority: medium
created: 2026-05-08T19:31:58.431269+00:00
updated: 2026-05-10T22:57:46.914247+00:00
tags:
- phase-4
- scope:kanban
- type:refactor
- id-allocation
- activity
- deployment-readiness
parent: 1437
depends_on:
- 1442
- 1439
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: kanban storage ID allocation, create_task persistence, and activity logging defaults.
Out of scope: MCP schema, Cockpit UI, setup seed, and docs.

## Acceptance Criteria
1. `storage.allocate_next_id` or its replacement acquires the create lock, scans active and archive task filename prefixes, computes max prefix plus one (or 1 when no files exist), and keeps the lock held while `create_task` writes the new task file. (td:2)
2. `KanbanEngine.create_task` no longer reads or writes `config.next_id`, and a scratch board can create tasks when `config.yml` is absent. (td:2)
3. Given active task prefixes 1 and 3 plus archive prefixes 2 and 5, `KanbanEngine.create_task` writes a task with ID 6. (td:2)
4. Concurrent `create_task` calls under one scratch board produce distinct task filename prefixes and leave `config.yml` absent or unchanged. (td:2)
5. `KanbanEngine` activity logging defaults to enabled without reading `config.activity_log`; `create_task` appends one `ActivityEvent` with all six model fields: `timestamp`, `task_id`, `action`, `source`, `detail`, and `task_status_at_start` (set to the entry status). (td:2)
6. Builder uses the probe artifacts from #1442 as implementation reference alongside the test-writer's test suite. (td:0)
[[2026-05-10]]


## Architecture Review

### Refinements Applied
1. **AC-1 lock scope**: Rewritten to specify the lock encompasses both scan and file write (per probe #1442 AC2 contract: "The scan and the write must both occur inside the same lock scope").
2. **AC-1 empty board**: Added base case — defaults to ID 1 when no task files exist.
3. **AC-5 field list**: Expanded from 5 fields to 6 to include `task_status_at_start` (matching #1442 AC3 architect refinement and `ActivityEvent` model).
4. **AC-6 pipeline compatibility**: Removed "does not use pytest or vitest" constraint. The probe artifacts from #1442 serve as implementation reference alongside the test-writer's test suite. The test-writer writes tests for AC-1 through AC-5 normally; the builder makes them pass.
5. **Crash-safety semantics**: The burned-ID contract (config.next_id incremented before file write) is intentionally replaced. Under scan-based allocation, a failed write inside the lock scope does not consume an ID — the next scan recomputes the same max+1. This is correct behavior. Existing tests in `test_engine_crash_safety.py` and `test_storage_io.py` that assert config-based burned-ID semantics will need updating by the test-writer/builder.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | ID allocation refactor and activity event emission are tightly coupled — both concern `create_task` mutation behavior |
| Interface clarity | PASS (after refinement) | Lock scope, base case, and field list made explicit |
| Dependency correctness | PASS | #1442 (probe) archived/done, #1439 (topology collapse) archived/done |
| Module layering | PASS | Changes stay within `storage.py` and `engine.py` — no upward imports added |
| TDD compliance | PASS | AC-1 through AC-5 are td:2; test-writer will write tests |
| KISS/YAGNI | PASS | Scan-based allocation is simpler than config-mediated counters; removes a write-back dependency |
| Premise challenge | PASS | Scan-based allocation eliminates stale-config coupling; activity event fills an existing gap in mutation logging |
| Pattern consistency | PASS | `_emit_event` pattern already used by edit/move/start_work/end_work/resolve_dr/archive; create_task follows the same pattern |
| Security surface | PASS | No new system boundaries; filename prefix parsing uses existing `list_task_files`/`list_archive_files` which filter temp/lock files |
| Single domain | PASS | kanban domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| scan active+archive dirs | OSError (disk failure) | OSError | No (propagates) | create_task fails cleanly — no partial state |
| write task file inside lock | OSError during atomic_write | OSError | No (propagates) | Lock released by context manager; no ID consumed |
| activity event append after write | OSError on activity.jsonl | OSError | Swallowed by _emit_event? No — propagates | Task created but event missing; matches existing pattern for other mutations |

### Challenger Results
- Challenger confidence in original: 0.41, recommendation: block
- Key challenges: (1) contract drift between task body and probe — addressed by refinements applied above; (2) crash-safety semantics reversal — addressed: intentional, documented, existing tests need updating; (3) interface boundary under-specified — addressed: AC-1 now specifies lock encompasses file write; (4) activity-event semantics — `task_status_at_start` for create events is a natural extension of the claim/start_work field to the creation point; (5) atomicity surface — create_task joins the existing write-then-log pattern used by all other mutations; (6) performance — filesystem scan of 1500 `.md` files is sub-millisecond
- Override rationale: all critical and moderate concerns are addressed by refinements or are within established patterns. The challenger's primary objection was contract drift, which is exactly what the refinements fix.

### Codebase Context
- `allocate_next_id`: `serve/kanban/src/owlbear_kanban/storage.py` L538-548
- `create_task`: `serve/kanban/src/owlbear_kanban/engine.py` L950-1050
- `_emit_event`: `serve/kanban/src/owlbear_kanban/engine.py` L1936-1960
- `list_task_files`/`list_archive_files`: `storage.py` L469-504
- `save_config`: `storage.py` L224-247 — writes only `next_id`; remains used by `migrate.py`
- `PRODUCT_TOPOLOGY.activity_log`: `topology.py` — already True
- `config_loader.load_config`: `config_loader.py` L28-80 — reads `next_id` from config.yml when present, defaults to 1
- Probe contract: `.owlbear/kanban/archive/1442-p4-05-probe-scan-based-task-id-allocation-and-activity-events.md` — AC1 (scan-based), AC2 (lock scope includes write), AC3 (6-field event)
- `test_engine_crash_safety.py`: existing tests assert config-based burned-ID flow — will need updating
- `activity_log=False` callers: ~15 test files — constructor parameter must remain available for test convenience

### Builder Guidance
- The `activity_log` constructor parameter on `KanbanEngine` must remain (tests use `activity_log=False`). Change only the default path: when `activity_log is None`, default to `True` directly instead of reading `self._config.activity_log`.
- The `save_config` function and `BoardConfig.next_id` field remain — they are used by `migrate.py`. Do not remove them.
- The `config.yml` file in `.owlbear/kanban/` will retain its stale `next_id` field — cleanup is out of scope for this task.
- Existing crash-safety tests (`test_engine_crash_safety.py`, `test_storage_io.py`) that assert burned-ID config semantics should be updated by the test-writer to match the new scan-based behavior.

### Test Depth
- AC-1: td:2 (new allocation logic with edge cases)
- AC-2: td:2 (config independence, absent config.yml)
- AC-3: td:2 (specific scenario with mixed active/archive prefixes)
- AC-4: td:2 (concurrency with locking)
- AC-5: td:2 (activity event emission, field validation)
- AC-6: td:0 (process constraint)
- Max depth: td:2. Test-writer writes tests for AC-1 through AC-5.

### Verdict: APPROVE (with refinements applied)

[[2026-05-10]]
Architecture review complete. Refined 4 AC lines: (1) AC-1 lock scope now explicitly encompasses file write per probe #1442 contract, added empty-board base case; (2) AC-5 expanded to 6-field ActivityEvent including task_status_at_start; (3) AC-6 removed pytest prohibition for pipeline compatibility; (4) test-depth annotations added (AC-1–5: td:2, AC-6: td:0). Challenger overridden — contract drift addressed by refinements, crash-safety reversal intentional and documented, interface boundary clarified. All 10 evaluation criteria PASS. Advanced to todo.
[[2026-05-10]]
## Test-Writer Notes
- Test file: tests/test_engine_1443.py
- Classes: TestFromAC_ScanBasedIdAllocation
- Tests per category:
  - AC-1 (scan-based allocation, lock scope): 5 tests (happy: empty board, active scan, archive scan; error: crash no-burn; boundary: lock scope via crash probe)
  - AC-2 (no config dependency): 4 tests (happy: no config.yml works; error: config not created, config.next_id unchanged; boundary: high config.next_id ignored)
  - AC-3 (specific scenario): 1 test (active 1,3 + archive 2,5 → ID 6)
  - AC-4 (concurrency): 3 tests (distinct IDs with scan proof; config.yml absent after concurrent; config unchanged)
  - AC-5 (activity logging defaults): 4 tests (default=True enabled; 1 event appended; 6 fields present; task_status_at_start=entry_status)
- Total: 17 tests, all FAIL ✓
- ruff: clean
- Also updated serve/kanban/tests/test_engine_crash_safety.py (3 tests rewritten for scan-based semantics, all FAIL) and serve/kanban/tests/test_storage_io.py (test_ac_c51 rewritten, FAILS) — per architect guidance that burned-ID config tests need updating.
- Commit: 8ccdbe5b1047488e0c827218139e87302b2f391e
[[2026-05-10]]
## Builder Notes
- Implementation: Updated serve/kanban/src/owlbear_kanban/storage.py and serve/kanban/src/owlbear_kanban/engine.py.
- Fixes applied:
  - `storage.allocate_next_id` now supports scan-based allocation under `.next_id.lock` and accepts `write_task_fn` so scan+write can happen in one lock scope.
  - In callback mode (used by create flow), ID is computed from active+archive filename prefixes (`max+1`, empty board -> 1) and no config mutation occurs.
  - In allocation-only mode, `.next_id.lock` stores last allocated ID to keep concurrent `allocate_next_id()` calls distinct while remaining independent of `config.next_id`.
  - `KanbanEngine.create_task` now performs task-file write inside the allocation lock via `write_task_fn`, then emits one create activity event with all required fields (`timestamp`, `task_id`, `action`, `source`, `detail`, `task_status_at_start`).
  - `KanbanEngine` default behavior for `activity_log=None` now enables activity logging directly (`True`) instead of reading `config.activity_log`.
- Tests:
  - RED verification (quality-runner scoped): 17 failed / 0 passed for tests/test_engine_1443.py before implementation.
  - GREEN verification (quality-runner scoped): 17 passed / 0 failed for tests/test_engine_1443.py.
  - Durable regression suite: 47 passed / 0 failed across:
    - tests/test_engine_1443.py
    - serve/kanban/tests/test_engine_crash_safety.py
    - serve/kanban/tests/test_storage_io.py
- Coverage (scoped run on selected tests): 30% aggregate on `serve/kanban/src/owlbear_kanban` (`engine.py` 18%, `storage.py` 80%).
- Ruff: clean (`serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`).
- Evidence summary: AC-1..AC-5 behaviors are now satisfied with lock-scoped scan allocation during create, config decoupling in create path, concurrency-safe distinct IDs, and default-on create-task activity emission.
- Commit: bef6d7e890505ece55344bdf18295963d58d3836
[[2026-05-10]]
## Review Evidence
### Test Results
- quality-runner scoped task suite: 47 passed, 0 failed across tests/test_engine_1443.py, serve/kanban/tests/test_engine_crash_safety.py, and serve/kanban/tests/test_storage_io.py
- quality-runner adjacent regression: 24 passed, 0 failed in serve/kanban/tests/test_engine_atomicity.py
- Commit presence was verified in .git/logs/HEAD:2556-2559 and .git/logs/refs/heads/dev:2360-2363. Terminal access was unavailable for exact git show and git status checks, so commit-diff and dirty-tree evidence is lower confidence.

### Lint: clean
- ruff clean on serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/storage.py, tests/test_engine_1443.py, serve/kanban/tests/test_engine_crash_safety.py, serve/kanban/tests/test_storage_io.py, and serve/kanban/tests/test_engine_atomicity.py

### Coverage: scoped evidence only
- task-scoped run: overall 30%; owlbear_kanban.engine 18%; owlbear_kanban.storage 80%
- adjacent atomicity run: overall 33%
- Low module percentages are informational here. Reject is driven by implementation safety and proof quality, not module-level percent.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-1 | tests/test_engine_1443.py::test_ac1_* plus serve/kanban/tests/test_engine_crash_safety.py::test_ac1_crash_during_write_does_not_burn_id | Yes. Empty-board, active-scan, archive-scan, and write-crash retry cases would fail on old config-based or unlocked allocation behavior. | COVERED |
| AC-2 | tests/test_engine_1443.py::test_ac2_* plus serve/kanban/tests/test_engine_crash_safety.py::test_ac2_* plus serve/kanban/tests/test_storage_io.py::test_ac_c51_scan_based_allocation_ignores_config_next_id | Yes. These tests would fail if create_task still read or wrote config.next_id or required config.yml. | COVERED |
| AC-3 | tests/test_engine_1443.py::test_ac3_active_1_3_archive_2_5_yields_id_6 | Yes. The exact mixed-prefix scenario would fail if max(active, archive) plus 1 were wrong. | COVERED |
| AC-4 | tests/test_engine_1443.py::test_ac4_* plus serve/kanban/tests/test_storage_io.py::test_ac_c4_* | Yes. Duplicate IDs, config mutation, or unlocked concurrency would fail these tests. | COVERED |
| AC-5 | tests/test_engine_1443.py::test_ac5_* | Partially. The suite proves success-path emission on a no-config board, but it does not fail if the default constructor incorrectly honors config.activity_log: false, and it allows any non-empty action/source strings. | LAX |
| AC-6 | N/A (td:0) | Task body architecture notes and builder notes align with probe #1442 semantics; no contradictory evidence in reviewed scope. | N/A |

#### Security Review
- No issues found in the reviewed scope. The new allocator only scans existing board files and the create flow stays within validated board paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| tests/test_engine_1443.py::TestFromAC_ScanBasedIdAllocation | No weakening is visible in the current file on read. Exact builder-vs-test-writer diff could not be reconstructed in this session because git show was unavailable. | PRESERVED (lower confidence) |
| serve/kanban/tests/test_engine_crash_safety.py and serve/kanban/tests/test_storage_io.py task-related additions | Current assertions still discriminate on scan-based semantics and config non-mutation. Exact commit-level authorship could not be reconstructed in this session. | PRESERVED (lower confidence) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | tests/test_engine_1443.py:424-425 assert only that evt.action and evt.source are non-empty. A wrong non-empty action or source would still pass. |
| Negative and error-path coverage | WEAK | tests/test_engine_1443.py:380-452 covers only success-path create-event emission. No task or adjacent regression test simulates append_activity_event failure after create_task writes the file. |
| Manual mutation reasoning | WEAK | A regression that honored config.activity_log: false on default construction, or emitted the wrong non-empty action/source, would stay green under the current AC-5 tests. |
| Test independence | ADEQUATE | Concurrent tests protect shared result collection with local locks and do not share cross-test mutable state. |
| Descriptive names | STRONG | Test names are explicit and AC-scoped across the task suite. |

#### Data Safety
- FAIL: KanbanEngine.create_task writes the task inside the allocator callback at serve/kanban/src/owlbear_kanban/engine.py:1042, then emits the required create event afterward at serve/kanban/src/owlbear_kanban/engine.py:1058-1062. Unlike edit_task, move_task, and release_task, create_task has no OSError rollback wrapper; compare serve/kanban/src/owlbear_kanban/engine.py:1199-1217, 1319-1339, and 1505-1524. A failed append_activity_event call can therefore leave the task file committed while create_task raises.

#### Implementation-Aware Gaps
- No adjacent regression covers create_task emit-failure rollback. serve/kanban/tests/test_engine_atomicity.py is green, but its current cases cover edit_task, move_task, claim_task, release_task, end_work, and sweep only; there is no create_task case.
- No reviewed test proves the default constructor ignores config.activity_log: false on a board that actually has config.yml present.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- serve/kanban/src/owlbear_kanban/engine.py:1-12 and serve/kanban/src/owlbear_kanban/engine.py:957-961 still describe the old config.next_id persistence and burned-ID behavior.
- Python reference lookup for allocate_next_id was unavailable in this session; grep fallback found call sites only in engine.py and tests.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-1 | serve/kanban/src/owlbear_kanban/storage.py:540-576, serve/kanban/src/owlbear_kanban/engine.py:1017-1043, tests/test_engine_1443.py:69-198, serve/kanban/tests/test_engine_crash_safety.py:84-136 | tests/test_engine_1443.py::test_ac1_* | PASS |
| AC-2 | serve/kanban/src/owlbear_kanban/storage.py:556-579, tests/test_engine_1443.py:201-260, serve/kanban/tests/test_engine_crash_safety.py:145-208, serve/kanban/tests/test_storage_io.py:441-472 | tests/test_engine_1443.py::test_ac2_* | PASS |
| AC-3 | tests/test_engine_1443.py:267-278 and allocator max-scan logic at serve/kanban/src/owlbear_kanban/storage.py:553-569 | tests/test_engine_1443.py::test_ac3_active_1_3_archive_2_5_yields_id_6 | PASS |
| AC-4 | serve/kanban/src/owlbear_kanban/storage.py:548-579, tests/test_engine_1443.py:285-373, serve/kanban/tests/test_storage_io.py:267-309 | tests/test_engine_1443.py::test_ac4_* | PASS |
| AC-5 | Constructor default is correct at serve/kanban/src/owlbear_kanban/engine.py:361-369, and success-path emit uses six fields at serve/kanban/src/owlbear_kanban/engine.py:1058-1062 and 1950-1974, but create_task lacks emit-failure rollback and the task suite leaves the config.activity_log false branch and exact action/source values under-proven. | tests/test_engine_1443.py::test_ac5_* | FAIL |
| AC-6 | Architecture Review and Builder Notes both align to probe #1442 semantics: lock-scoped scan allocation plus six-field create event. | N/A (td:0) | PASS |

### Confidence: 0.74
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Add emit-failure rollback to KanbanEngine.create_task so a failed create-event append does not leave committed task state behind | serve/kanban/src/owlbear_kanban/engine.py | Data Safety finding: create_task writes at 1042 and emits at 1058-1062 without the rollback used at 1199-1217, 1319-1339, and 1505-1524 |
| 2 | builder | Add an adjacent regression for create_task emit-failure rollback in the atomicity suite without modifying TestFromAC content | serve/kanban/tests/test_engine_atomicity.py | Implementation-Aware Gaps: file header at 1-5 defines write-before-log rollback expectations, but there is no create_task case |

[[2026-05-10]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py.
- Fixes applied:
  - Added rollback handling in KanbanEngine.create_task so if create-event emission raises OSError after file write, the newly created task file is deleted and cache/index entries are cleaned before re-raising.
  - Kept the change surgical and aligned with existing write-then-log rollback semantics used by other mutators.
  - Updated create_task docstring to match current scan-based allocation behavior (no config.next_id coupling).
- Tests:
  - quality-runner scoped verification: 71 passed, 0 failed across tests/test_engine_1443.py, serve/kanban/tests/test_engine_atomicity.py, serve/kanban/tests/test_engine_crash_safety.py, serve/kanban/tests/test_storage_io.py.
- Coverage:
  - quality-runner scoped module coverage for owlbear_kanban.engine: 40%.
- ruff:
  - clean on serve/kanban/src/owlbear_kanban/engine.py and scoped test files.
- Evidence summary:
  - create_task now rolls back filesystem state when activity emit fails, addressing the reviewer’s data-safety finding about write-after-log failure handling.
- Commit:
  - 6feb5132
[[2026-05-10]]
## Review Evidence
### Test Results
- quality-runner scoped suite: 71 passed, 0 failed across `tests/test_engine_1443.py`, `serve/kanban/tests/test_engine_atomicity.py`, `serve/kanban/tests/test_engine_crash_safety.py`, and `serve/kanban/tests/test_storage_io.py`.
- ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`, and the scoped test files.
- Coverage: 37% overall; `owlbear_kanban.engine` 40%; `owlbear_kanban.storage` 81%.
- Commit presence verified in `.git/logs/HEAD` and `.git/logs/refs/heads/dev` for `8ccdbe5b1047488e0c827218139e87302b2f391e`, `bef6d7e890505ece55344bdf18295963d58d3836`, and `6feb5132f596ee1db09013c5a5a6afb63701bc5c`.
- Exact `git diff` / dirty-tree reconstruction was not available in this session, so commit-integrity confidence is slightly reduced.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC-1 | `storage.allocate_next_id` holds the lock while invoking `write_task_fn` at `serve/kanban/src/owlbear_kanban/storage.py:540-576`; task tests cover empty board, active/archive scan, crash-no-burn, and concurrent distinct IDs at `tests/test_engine_1443.py:69-194` and `tests/test_engine_1443.py:288-327`. | PASS |
| AC-2 | `create_task` routes through allocator callback at `serve/kanban/src/owlbear_kanban/engine.py:1019-1043`; tests prove scratch-board create without `config.yml` and no `config.next_id` mutation at `tests/test_engine_1443.py:201-260`, with adjacent regression at `serve/kanban/tests/test_engine_crash_safety.py:137-249` and `serve/kanban/tests/test_storage_io.py:441-472`. | PASS |
| AC-3 | Mixed active/archive max+1 scenario is pinned at `tests/test_engine_1443.py:268-279`. | PASS |
| AC-4 | Concurrent create tests prove distinct IDs and config non-mutation at `tests/test_engine_1443.py:288-373`. | PASS |
| AC-5 | Source satisfies the defaulting clause at `serve/kanban/src/owlbear_kanban/engine.py:367-369`, and `config_loader` only reads `next_id` from disk at `serve/kanban/src/owlbear_kanban/config_loader.py:45-55`. Task tests prove default-on logging, one emitted event, and `task_status_at_start == task.status` at `tests/test_engine_1443.py:380-451`. | PASS |
| AC-6 | Task history still aligns with probe `#1442`; no contradictory evidence in reviewed scope. | PASS |

#### Security Review
- No issues found in the reviewed scope.

#### Test Integrity
- No weakening or removal is visible in the current `TestFromAC_*` suites.
- Confidence is reduced slightly because exact commit-level test immutability could not be reconstructed with `git show` in this session.

#### Test Quality
- FAIL: the retry added a new `create_task` rollback branch at `serve/kanban/src/owlbear_kanban/engine.py:1060-1070`, but there is still no executable regression that proves this branch works.
- Evidence: the task suite only simulates pre-write `OSError` through `write_task` patches at `tests/test_engine_1443.py:144` and `tests/test_engine_1443.py:178`. It does not patch `append_activity_event` / `_emit_event` for `create_task`.
- Evidence: the adjacent atomicity suite still contains emit-failure rollback cases for `edit_task`, `move_task`, `claim_task`, `end_work`, and `release_task` at `serve/kanban/tests/test_engine_atomicity.py:155`, `serve/kanban/tests/test_engine_atomicity.py:192`, `serve/kanban/tests/test_engine_atomicity.py:243`, `serve/kanban/tests/test_engine_atomicity.py:265`, and `serve/kanban/tests/test_engine_atomicity.py:342`, but no `create_task` rollback case.
- Because the previous review rejected this task on that same proof gap, the green suite still does not prove the new safety path added by commit `6feb5132f596ee1db09013c5a5a6afb63701bc5c`.

#### Data Safety
- No live implementation defect was confirmed in the current source. The rejection is for missing executable proof on the retry-added rollback path, not for an observed runtime failure in the current implementation.

#### Implementation-Aware Gaps
- Significant untested path: post-write activity-emit failure in `KanbanEngine.create_task` after the new rollback logic was added.
- The AC-5 defaulting clause is source-proven rather than runtime-proven because `config_loader` hardcodes `activity_log` from topology and does not read that field from `config.yml`; this is noted for planning, not treated as a blocking runtime gap.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Prior `## Review Evidence` sections before this review | 1 |
| Current issue type | repeated proof gap |
| Assessment | LOOP-BREAKER: second review failure routes to `backlog` |

### Pass 2 — INFORMATIONAL
- Top-level engine module docs are still stale about config-based ID persistence at `serve/kanban/src/owlbear_kanban/engine.py:1-14`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC-1 | `serve/kanban/src/owlbear_kanban/storage.py:540-576`; `tests/test_engine_1443.py:69-194`; `tests/test_engine_1443.py:288-327` | `tests/test_engine_1443.py::test_ac1_*` | PASS |
| AC-2 | `serve/kanban/src/owlbear_kanban/engine.py:1019-1043`; `tests/test_engine_1443.py:201-260`; `serve/kanban/tests/test_engine_crash_safety.py:137-249`; `serve/kanban/tests/test_storage_io.py:441-472` | `tests/test_engine_1443.py::test_ac2_*` | PASS |
| AC-3 | `tests/test_engine_1443.py:268-279` | `tests/test_engine_1443.py::test_ac3_active_1_3_archive_2_5_yields_id_6` | PASS |
| AC-4 | `tests/test_engine_1443.py:288-373` | `tests/test_engine_1443.py::test_ac4_*` | PASS |
| AC-5 | `serve/kanban/src/owlbear_kanban/engine.py:367-369`; `serve/kanban/src/owlbear_kanban/engine.py:1060-1064`; `serve/kanban/src/owlbear_kanban/config_loader.py:45-55`; `tests/test_engine_1443.py:380-451` | `tests/test_engine_1443.py::test_ac5_*` | PASS |
| AC-6 | task history / builder notes align with probe `#1442` | N/A (td:0) | PASS |

### Deductions
- `-0.10`: significant retry-added rollback branch remains untested.
- `-0.04`: same proof gap survived into a second review cycle, invoking loop-breaker routing.
- `-0.02`: exact diff/dirty-tree verification unavailable in-session.

### Confidence: 0.84
### Verdict: FAIL
### Action
- Reject to `backlog`. This is the second review failure and the remaining blocker is still proof quality / retry planning, not a demonstrated implementation defect.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-scope the retry so it includes executable proof for `create_task` post-write emit-failure rollback before another builder pass | `serve/kanban/tests/test_engine_atomicity.py`, `tests/test_engine_1443.py`, `serve/kanban/src/owlbear_kanban/engine.py` | New rollback branch exists at `serve/kanban/src/owlbear_kanban/engine.py:1060-1070`, but task tests only patch `write_task` at `tests/test_engine_1443.py:144` and `tests/test_engine_1443.py:178`, and the adjacent atomicity suite still only lists other mutators at `serve/kanban/tests/test_engine_atomicity.py:155`, `:192`, `:243`, `:265`, `:342` |
| 2 | architect | Clarify in the next retry plan that AC-5's `without reading config.activity_log` clause should be discharged by source proof rather than an impossible runtime `config.yml` toggle test | `serve/kanban/src/owlbear_kanban/config_loader.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_1443.py` | `config_loader` reads only `next_id` from disk at `serve/kanban/src/owlbear_kanban/config_loader.py:45-47` and hardcodes `activity_log` from topology at `:55`, while the constructor hardcodes the default at `serve/kanban/src/owlbear_kanban/engine.py:367-369` |
[[2026-05-10]]

## Retry Scope (Review Cycle 3)

### New AC
7. When `_emit_event` raises `OSError` after `create_task` writes the task file, `create_task` deletes the newly created file, removes its cache/index entries, and re-raises `OSError`; no activity event is written and `activity.jsonl` has no entry for the failed create. (td:2)

### AC-5 Clarification
The "without reading `config.activity_log`" clause in AC-5 is discharged by source proof: the constructor defaults `activity_log` to `True` at `engine.py:367-369`, and `config_loader` hardcodes `activity_log` from topology at `config_loader.py:55` (it never reads this field from `config.yml`). No runtime toggle test is required for this sub-clause.

### Test Placement
AC-7 test belongs in `serve/kanban/tests/test_engine_atomicity.py` alongside the existing emit-failure rollback tests for `edit_task`, `move_task`, `claim_task`, `end_work`, `release_task`, and `sweep`. Follow the same pattern: patch `owlbear_kanban.activity_store.append_activity_event` with `side_effect=OSError`, call `create_task`, assert OSError propagates, assert no task file remains on disk, assert no activity event written.

### What Changed vs Prior Cycles
- AC-1 through AC-6: unchanged, all PASS in review evidence.
- AC-7: new, covers the untested rollback branch that blocked both prior reviews.
- The rollback implementation already exists (commit `6feb5132`). This retry adds only the missing executable proof.

### Builder Guidance (Retry)
- The rollback code at `engine.py:1060-1070` already implements AC-7. The test-writer writes the failing test; the builder confirms it passes (it should already pass against the current implementation).
- Do NOT modify `tests/test_engine_1443.py` — the new test goes in `serve/kanban/tests/test_engine_atomicity.py`.
- If the existing rollback code does not pass the new test, fix it.

[[2026-05-10]]
## Architecture Review (Retry Cycle 3)

### Verdict: APPROVE → todo

### What changed
- Added AC-7: executable proof for `create_task` post-write emit-failure rollback in `test_engine_atomicity.py` (td:2). This is the exact gap that caused both prior review failures.
- Clarified AC-5: `config.activity_log` independence is source-proven (constructor default + config_loader hardcoding), no runtime toggle test required.
- AC-1 through AC-6: unchanged, all passed in both prior reviews.

### Evaluation (delta from original review)
- All 10 criteria remain PASS from the original architecture review.
- The retry adds one focused AC line targeting a proven implementation gap (rollback branch at engine.py:1060-1070 has no test).
- No new architectural concerns — the rollback code already exists and follows the established pattern from other mutators.

### Challenger: SKIP
- All AC lines from original review were previously challenged (confidence override documented). AC-7 is a test-only addition following an established pattern — no architectural decision to challenge.

### Test Depth
- AC-7: td:2 (emit-failure rollback with file deletion assertion)
- All other AC lines: unchanged from original review
[[2026-05-10]]
## Test-Writer Notes
- Retry cycle 3 — surgical fill only (Step 1b.1 direct-to-review advance).
- Test file: `serve/kanban/tests/test_engine_atomicity.py`
- New tests added to `TestFromAC_EngineAtomicity`:
  - `test_create_task_emit_failure_rollback`: patches emit with OSError, asserts task file deleted from `tasks/`, asserts no activity.jsonl entry — 1 test
  - `test_create_task_emit_failure_task_not_in_index`: asserts failed create leaves no ghost in `list_tasks()` — 1 test
- Total new: 2 tests
- Both PASS against current implementation (rollback code at `engine.py:1060-1070` already handles AC-7; this retry adds the executable proof that was missing).
- Ruff: clean.
- Commit: 75df9542
- Builder skip: all new tests pass — no implementation work required.
- AC coverage: AC-7 now has executable proof. AC-1 through AC-5 unchanged (all passed prior reviews). AC-6 td:0.
[[2026-05-10]]
## Builder Notes
- Non-implementation builder pass (retry cycle 3 builder-skip validation): no source/test edits were required in this pass.
- Verification (quality-runner, scoped): 73 passed, 0 failed across `tests/test_engine_1443.py`, `serve/kanban/tests/test_engine_atomicity.py`, `serve/kanban/tests/test_engine_crash_safety.py`, and `serve/kanban/tests/test_storage_io.py`.
- Coverage: `owlbear_kanban.engine` 44% in scoped run (informational for this pass-through check).
- Ruff: clean on scoped source/test paths.
- Evidence summary: AC-7 proof tests added by test-writer are green against current implementation; no additional builder implementation was needed, so task is advanced to review.
[[2026-05-10]]
## Review Evidence
### Test Results
- quality-runner scoped suite: 73 passed, 0 failed across tests/test_engine_1443.py, serve/kanban/tests/test_engine_atomicity.py, serve/kanban/tests/test_engine_crash_safety.py, and serve/kanban/tests/test_storage_io.py.
- Commit presence verified in .git/logs/HEAD lines 2556, 2559, 2560, and 2570, and .git/logs/refs/heads/dev lines 2360, 2363, 2364, and 2374 for task-related commits 8ccdbe5b1047488e0c827218139e87302b2f391e, bef6d7e890505ece55344bdf18295963d58d3836, 6feb5132f596ee1db09013c5a5a6afb63701bc5c, and 75df9542acc2fee5d275dcb34d5af169e283f1e5.
- Exact git diff and dirty-tree reconstruction were unavailable in this session, so commit-integrity confidence is slightly reduced.

### Lint
- ruff clean on serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/storage.py, tests/test_engine_1443.py, serve/kanban/tests/test_engine_atomicity.py, serve/kanban/tests/test_engine_crash_safety.py, and serve/kanban/tests/test_storage_io.py.

### Coverage
- overall 51%; owlbear_kanban.engine 44%; owlbear_kanban.storage 81%.
- Module percentages are informational here. The changed create-task and allocator paths have direct executable proof from the task suite and the adjacent atomicity/crash-safety regressions.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC-1 | storage.allocate_next_id holds the shared create lock and invokes write_task_fn inside the lock scope at serve/kanban/src/owlbear_kanban/storage.py:540-576. Tests prove empty-board id 1, active scan, archive scan, and write-crash no-burn behavior at tests/test_engine_1443.py:69-198 and serve/kanban/tests/test_engine_crash_safety.py:84-136. | COVERED |
| AC-2 | create_task routes through allocate_next_id in callback mode and does not use config.next_id for allocation at serve/kanban/src/owlbear_kanban/engine.py:946-1043. Tests prove scratch-board create without config.yml and unchanged config.next_id at tests/test_engine_1443.py:201-260, serve/kanban/tests/test_engine_crash_safety.py:145-208, and serve/kanban/tests/test_storage_io.py:441-472. | COVERED |
| AC-3 | Mixed active/archive max-plus-one scenario is pinned by tests/test_engine_1443.py:267-278, matching allocator scan logic at serve/kanban/src/owlbear_kanban/storage.py:556-576. | COVERED |
| AC-4 | Concurrent create tests prove distinct ids and config non-mutation at tests/test_engine_1443.py:285-373, with allocation-only concurrency support exercised in serve/kanban/tests/test_storage_io.py:267-309. | COVERED |
| AC-5 | Constructor defaults activity logging to enabled directly at serve/kanban/src/owlbear_kanban/engine.py:361-369, while config_loader hardcodes activity_log from topology and reads only next_id from config.yml at serve/kanban/src/owlbear_kanban/config_loader.py:45-58. Tests prove one emitted create event, all six fields present, and task_status_at_start equals entry status at tests/test_engine_1443.py:380-451. | COVERED |
| AC-6 | Task history remains aligned with probe #1442 usage in the Architecture Review and builder notes; no contradictory evidence was found in the reviewed repo scope. | COVERED |
| AC-7 | create_task re-raises OSError and rolls back the failed create at serve/kanban/src/owlbear_kanban/engine.py:1060-1072. The retry-added tests prove file deletion, zero activity entries, and no ghost task in list_tasks at serve/kanban/tests/test_engine_atomicity.py:812-844 and serve/kanban/tests/test_engine_atomicity.py:119-126. | COVERED |

#### Security Review
- No issues found in the reviewed scope. The allocator scans board-local files only, create_task still validates containment before write, and no new injection, path traversal, deserialization, or secret-handling surface was introduced.

#### Test Integrity
- No weakening or removal is visible in the current TestFromAC suites in tests/test_engine_1443.py, serve/kanban/tests/test_engine_crash_safety.py, serve/kanban/tests/test_storage_io.py, and serve/kanban/tests/test_engine_atomicity.py.
- Confidence is reduced slightly because exact commit-level test immutability and scoped dirty-tree state could not be reconstructed in this session.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC-5 requires field presence plus task_status_at_start equality, which tests/test_engine_1443.py:380-451 proves directly. AC-7 assertions fail if the file survives, an activity entry is written, or the task remains visible after rollback in serve/kanban/tests/test_engine_atomicity.py:812-844. |
| Negative and error-path coverage | STRONG | AC-1 write-crash and AC-7 emit-failure paths are both exercised in serve/kanban/tests/test_engine_crash_safety.py:84-136 and serve/kanban/tests/test_engine_atomicity.py:812-844. |
| Manual mutation reasoning | ADEQUATE | Reverting to config.next_id allocation, dropping archive scan, removing rollback, or leaving ghost state would fail the scoped suites cited above. |
| Test independence | ADEQUATE | Concurrency tests isolate shared state within per-test scratch boards and local synchronization. |
| Descriptive names | STRONG | Test names remain AC-scoped and behavior-specific across the task suite. |

#### Data Safety
- No live issue confirmed in the current AC scope. The stale rollback-path concern raised during adversarial analysis depends on tasks_dir or archive_dir changing between engine construction and create_task, but config_loader fixes both paths from PRODUCT_TOPOLOGY at serve/kanban/src/owlbear_kanban/config_loader.py:57-58, so create_task and write_task resolve the same directories in current runtime.

#### Implementation-Aware Gaps
- No significant untested path remains within the current retry scope. The prior blocker was executable proof for post-write emit-failure rollback, and that proof now exists in serve/kanban/tests/test_engine_atomicity.py:812-844.
- The earlier retry-path objection is non-blocking because the latest bound retry scope adds AC-7 without a retry requirement.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Prior Review Evidence sections before this review | 2 |
| Latest retry change | Architecture Review wrote AC-7 into the task body; test-writer added two focused rollback proofs; builder skip was appropriate because they passed against current source |
| Assessment | CLEAN after scoped retry refinement |

### Pass 2 - INFORMATIONAL
- serve/kanban/src/owlbear_kanban/engine.py:1-14 still contains stale top-level wording about config.next_id persistence.
- serve/kanban/tests/test_engine_crash_safety.py:80-81 retains a stale burned-id comment even though the test body now asserts no-burn scan semantics.
- Python reference lookup for allocate_next_id was unavailable; grep fallback found production call sites only in serve/kanban/src/owlbear_kanban/engine.py plus test coverage in the scoped suites.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-1 | serve/kanban/src/owlbear_kanban/storage.py:540-576; tests/test_engine_1443.py:69-198; serve/kanban/tests/test_engine_crash_safety.py:84-136 | tests/test_engine_1443.py::test_ac1_* | PASS |
| AC-2 | serve/kanban/src/owlbear_kanban/engine.py:946-1043; tests/test_engine_1443.py:201-260; serve/kanban/tests/test_engine_crash_safety.py:145-208; serve/kanban/tests/test_storage_io.py:441-472 | tests/test_engine_1443.py::test_ac2_* | PASS |
| AC-3 | serve/kanban/src/owlbear_kanban/storage.py:556-576; tests/test_engine_1443.py:267-278 | tests/test_engine_1443.py::test_ac3_active_1_3_archive_2_5_yields_id_6 | PASS |
| AC-4 | serve/kanban/src/owlbear_kanban/storage.py:556-579; tests/test_engine_1443.py:285-373; serve/kanban/tests/test_storage_io.py:267-309 | tests/test_engine_1443.py::test_ac4_* | PASS |
| AC-5 | serve/kanban/src/owlbear_kanban/engine.py:361-369; serve/kanban/src/owlbear_kanban/config_loader.py:45-58; serve/kanban/src/owlbear_kanban/engine.py:1058-1064; tests/test_engine_1443.py:380-451 | tests/test_engine_1443.py::test_ac5_* | PASS |
| AC-6 | Task-body Architecture Review and Builder Notes remain consistent with probe #1442 usage; no contradictory repo evidence found | task history | PASS |
| AC-7 | serve/kanban/src/owlbear_kanban/engine.py:1060-1072; serve/kanban/tests/test_engine_atomicity.py:812-844; serve/kanban/tests/test_engine_atomicity.py:119-126 | serve/kanban/tests/test_engine_atomicity.py::test_create_task_emit_failure_* | PASS |

### Deductions
- -0.03: exact git diff and dirty-tree inspection unavailable in-session.
- -0.02: TestFromAC immutability inferred from current bodies plus commit-presence logs, not from a direct commit diff.

### Confidence: 0.93
### Verdict: PASS
### Action
- Advance to docs.
[[2026-05-10]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified | `serve/kanban/README.md` — `create_task` row says "Allocate next ID and write a new task file" — accurate and not tied to config-based semantics; no other prose docs reference `allocate_next_id` or `config.next_id` allocation path |
| 2 | Module docstrings | Yes | Updated | `engine.py` lines 10–12: stale "(persists config.next_id before write)" replaced with scan-based wording matching the new implementation. `storage.py` `allocate_next_id` docstring was already accurate (updated by builder). `create_task` function docstring was already updated by builder. Committed in `1bbd2f34` (broad-audit overlap). |
| 3 | External attribution | No | N/A | No external repos or articles cited in task body or builder notes |
| 4 | Research doc | No | N/A | No `.owlbear/research/` document produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `kanban.excalidraw` describes `serve/kanban/src/**`; `mcp-topology.excalidraw` also describes `serve/kanban/src/**`. Both footer text elements updated to `Last verified: 2026-05-10 (f5dcd426)` — committed in `1bbd2f34` (broad-audit overlap). |
| 6 | Explicit diagram creation | No | N/A | No new diagram requested |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN | Module docstring updated |
| `serve/kanban/src/owlbear_kanban/storage.py` | IN | Docstring already accurate |
| `tests/test_engine_1443.py` | OUT | Test file — no action |
| `serve/kanban/tests/test_engine_atomicity.py` | OUT | Test file — no action |
| `serve/kanban/tests/test_engine_crash_safety.py` | OUT | Test file — no action |
| `serve/kanban/tests/test_storage_io.py` | OUT | Test file — no action |

### Files Updated
- `serve/kanban/src/owlbear_kanban/engine.py` — module docstring line 12 (already committed by broad-audit `1bbd2f34`)
- `share/diagrams/kanban.excalidraw` — footer updated (broad-audit `1bbd2f34`)
- `share/diagrams/mcp-topology.excalidraw` — footer updated (broad-audit `1bbd2f34`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1443-*` files found in `.owlbear/scratch/`)
[[2026-05-10]]
## Audit
### Regression Detection
- quality-runner mode full: 4340 passed, 209 failed, 5 errors (vitest timeouts)
- 207 failures are pre-existing background noise (missing archived task-scoped test files, unrelated modules)
- **2 failures are task-caused regressions in the kanban domain:**
  1. `serve/kanban/tests/test_engine_archived_edit.py::TestFromAC_StorageCoveragePaths::test_allocate_next_id_returns_current_next_id_and_increments` — expects old config-based `allocate_next_id` to return `next_id=10` from config, gets `1` from scan-based allocation
  2. `serve/kanban/tests/test_storage.py::TestBuilderDiscovered::test_allocate_next_id_returns_current_and_persists_increment` — expects `allocate_next_id` to return current value and persist increment (`assert 1 == (1 + 1)`), scan-based allocation returns `1`
- Both confirmed by direct `uv run pytest` execution. Kanban suite: 1071 passed, 2 failed.
- regression verdict: FAIL

### Intent Verification
- scope alignment: PASS (changed files: `engine.py`, `storage.py` in `serve/kanban/src/owlbear_kanban/`; tests in `tests/test_engine_1443.py`, `serve/kanban/tests/test_engine_atomicity.py`, `test_engine_crash_safety.py`, `test_storage_io.py`)
- purpose match: PASS (scan-based ID allocation replaces config-based, create-task activity logging added)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
The architect explicitly called out `test_engine_crash_safety.py` and `test_storage_io.py` as needing updates for the new scan-based semantics, but missed `test_engine_archived_edit.py` and `test_storage.py` which also have tests depending on the old `allocate_next_id` config-based behavior. This gap propagated through test-writer, builder, and reviewer — all scoped their runs to the explicitly listed files and never discovered the 2 additional regressions. The full-suite auditor pass caught them.

### Commit Integrity
- upstream commit presence: PASS — 4 task commits verified: `8ccdbe5b` (test-writer), `bef6d7e8` (builder), `6feb5132` (builder rollback fix), `75df9542` (test-writer retry-3)
- working tree: clean except kanban task files (from auditor claim)
- kanban commit packaging: N/A (reject — no archive commit)

### Deduction Breakdown
- -.10: regression failures — 2 task-caused regressions in `test_engine_archived_edit.py` and `test_storage.py`
- -.03: AC quality ≤ 3 — architect missed downstream test dependencies beyond explicitly listed files
### Confidence: 0.87
### Action: reject-to-backlog
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update `test_allocate_next_id_returns_current_next_id_and_increments` in `test_engine_archived_edit.py` to match scan-based allocation semantics | `serve/kanban/tests/test_engine_archived_edit.py:1044` | Expects config-based `next_id=10`, gets scan-based `1` |
| 2 | builder | Update `test_allocate_next_id_returns_current_and_persists_increment` in `test_storage.py` to match scan-based allocation semantics | `serve/kanban/tests/test_storage.py:1784` | Expects config-based increment behavior, scan-based returns `1` |
[[2026-05-10]]

## Retry Scope (Auditor Cycle 4)

### Root Cause
Architect (original review) explicitly listed `test_engine_crash_safety.py` and `test_storage_io.py` as needing scan-based updates, but missed two additional durable tests in `test_engine_archived_edit.py` and `test_storage.py` that also depend on the old config-based `allocate_next_id` behavior. The gap propagated through all downstream agents because they scoped runs to the explicitly listed files only.

### New AC
8. `test_engine_archived_edit.py::TestFromAC_StorageCoveragePaths::test_allocate_next_id_returns_current_next_id_and_increments` and `test_storage.py::TestBuilderDiscovered::test_allocate_next_id_returns_current_and_persists_increment` are updated to assert scan-based `allocate_next_id` semantics: on a fresh board with no task files, `allocate_next_id(kanban_dir)` returns `1` and `load_config(kanban_dir).next_id` is unchanged after the call. Both tests pass. The full kanban suite (`serve/kanban/tests/`) passes with zero regressions. (td:1)

### What Changed vs Prior Cycles
- AC-1 through AC-7: unchanged, all PASS in review evidence (cycle 3 review confidence 0.93).
- AC-8: new, fixes the 2 auditor-discovered regressions that blocked cycle 4 exit.
- No implementation changes needed — the scan-based allocation is correct. Only test assertions need updating.

### Test Placement
AC-8 updates are in-place edits of existing durable tests, not new test files:
- `serve/kanban/tests/test_engine_archived_edit.py` — update assertions in existing test method
- `serve/kanban/tests/test_storage.py` — update assertions in existing test method

### Builder Guidance (Retry)
- Update both test methods to assert: (a) `allocate_next_id(kanban_dir)` returns `1` on a fresh empty board; (b) `load_config(kanban_dir).next_id` is the same before and after the call (config is NOT mutated).
- Update docstrings to describe scan-based behavior instead of config-based.
- Do NOT modify any source files in `serve/kanban/src/`.
- Run the full kanban suite to confirm zero regressions.

[[2026-05-10]]
## Architecture Review (Retry Cycle 4)

### Verdict: APPROVE → todo

### What changed
- Added AC-8: update 2 pre-existing durable tests that still assert config-based `allocate_next_id` semantics to match scan-based allocation (td:1). These are the exact regressions the auditor caught.
- AC-1 through AC-7: unchanged, all PASS from prior reviews.

### Evaluation (delta from prior reviews)
- All 10 criteria remain PASS. AC-8 is a test-assertion update — no architectural decision, no new interfaces, no new code paths.
- The regression was an architect gap (missed 2 downstream test files), not an implementation defect.

### Challenger: SKIP
- AC-8 is a mechanical test-assertion update following established scan-based semantics already proven in AC-1–AC-5. No design trade-off to challenge.

### Test Depth
- AC-8: td:1 (assertion update in existing tests, one happy path each)
- All other AC lines: unchanged from prior reviews
[[2026-05-10]]
## Test-Writer Notes
- Retry cycle 4 — Step 1b.1 direct-to-review advance (test-only, no impl work needed).
- Updated files:
  - `serve/kanban/tests/test_engine_archived_edit.py` — `TestFromAC_StorageCoveragePaths::test_allocate_next_id_returns_current_next_id_and_increments`: updated docstring and assertions to scan-based semantics (returns 1 on empty board, config.next_id unchanged).
  - `serve/kanban/tests/test_storage.py` — `TestBuilderDiscovered::test_allocate_next_id_returns_current_and_persists_increment`: updated docstring and assertions to scan-based semantics (returns 1 on empty board, after == before).
- AC coverage: AC-8 (td:1) — both tests now assert scan-based allocate_next_id behavior. AC-1 through AC-7 unchanged (all PASS from prior review cycle 3, confidence 0.93).
- Both updated tests PASS against current implementation (rollback code at engine.py:1060-1070 already in place since commit 6feb5132).
- Full kanban suite: 1338 passed, 0 failed, 0 errors (zero regressions).
- ruff: clean on both files.
- Commit: eab9d05f
[[2026-05-10]]
## Builder Notes
- Non-implementation builder pass (retry cycle 4): no source edits were required in this pass.
- Verification (quality-runner, scoped): 161 passed, 0 failed across `serve/kanban/tests/test_engine_archived_edit.py` and `serve/kanban/tests/test_storage.py` (plus their module-local dependencies).
- Regression verification (quality-runner): full `serve/kanban/tests/` suite passed with 1338 passed, 0 failed.
- Coverage (scoped informational): `owlbear_kanban.engine` 37%, `owlbear_kanban.storage` 95%, overall 43%.
- ruff: clean on scoped test files.
- Evidence summary: AC-8 test updates are green and no task-caused regressions remain in the kanban durable suite.

[[2026-05-10]]
## Review Evidence
### Test Results
- Fresh quality-runner scoped suite: 234 passed, 0 failed across `tests/test_engine_1443.py`, `serve/kanban/tests/test_engine_atomicity.py`, `serve/kanban/tests/test_engine_crash_safety.py`, `serve/kanban/tests/test_storage_io.py`, `serve/kanban/tests/test_engine_archived_edit.py`, and `serve/kanban/tests/test_storage.py`.
- Fresh quality-runner full kanban regression: 1338 passed, 0 failed across `serve/kanban/tests/`.
- Commit presence verified in `.git/logs/HEAD` lines 2556, 2559, 2560, 2570, and 2581 plus `.git/logs/refs/heads/dev` lines 2360, 2363, 2364, 2374, and 2385 for task commits `8ccdbe5b`, `bef6d7e8`, `6feb5132`, `75df9542`, and `eab9d05f`.

### Lint
- Ruff clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`, `tests/test_engine_1443.py`, `serve/kanban/tests/test_engine_atomicity.py`, `serve/kanban/tests/test_engine_crash_safety.py`, `serve/kanban/tests/test_storage_io.py`, `serve/kanban/tests/test_engine_archived_edit.py`, and `serve/kanban/tests/test_storage.py`.

### Coverage
- Fresh scoped coverage: `owlbear_kanban.engine` 53%, `owlbear_kanban.storage` 97%.
- Module percentages are informational here. The gate is executable proof on the touched create-task, allocator, atomicity, and durable regression paths, which the fresh scoped run plus full kanban regression now provide.

### Pass 1 - CRITICAL
#### Security Review
- No issues found in the AC scope. The allocator scans board-local numeric filename prefixes only, and `create_task` / `write_task` still validate path containment before persistence.

#### Test Integrity
- No weakening or removal is visible in the current `TestFromAC_*` suites.
- Confidence is reduced slightly because exact commit-level TestFromAC immutability was inferred from current file bodies plus commit-presence logs rather than a direct `git show` diff.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | AC-8 durable tests now assert exact scan-based outcomes (`serve/kanban/tests/test_engine_archived_edit.py:1042-1045`, `serve/kanban/tests/test_storage.py:1778-1784`). AC-7 rollback tests assert no new task file and no ghost task after emit failure (`serve/kanban/tests/test_engine_atomicity.py:812-844`). |
| Negative and error-path coverage | STRONG | Write-crash no-burn behavior is covered in `tests/test_engine_1443.py:113-198`, and post-write emit-failure rollback is covered in `serve/kanban/tests/test_engine_atomicity.py:812-844`. |
| Manual mutation reasoning | ADEQUATE | Reverting to config-driven allocation, dropping archive scan, removing emit rollback, or leaving the two durable tests on stale config-next_id semantics would fail the cited suites. |
| Test independence | ADEQUATE | Task tests use scratch boards per test and local synchronization in concurrency cases. |
| Descriptive names | STRONG | Test names remain AC-scoped and behavior-specific across the reviewed suites. |
- Code-reader raised two non-blocking proof-shape concerns: AC-1 lock-scope proof is source-backed rather than a blocked-write harness, and AC-5 field proof does not assert exact `action/source/detail` strings. I treated both as deductions rather than failures because AC-1 is directly closed by source at `storage.py:540-579` + `engine.py:1018-1044`, and AC-5 requires one create event with the six model fields plus `task_status_at_start == entry status`, not exact payload strings.

#### Data Safety
- No live AC-scope defect confirmed.
- Code-reader identified a possible allocation-only/callback ID-reuse risk in `allocate_next_id`, but grep on `allocate_next_id(` found only one production caller (`serve/kanban/src/owlbear_kanban/engine.py:1044`); the remaining call sites are tests. That concern is outside the current task AC and is non-blocking for this review.

#### Implementation-Aware Gaps
- No significant untested path remains inside the bound retry scope.
- The prior review blocker was AC-7 rollback proof. That gap is now closed by `serve/kanban/tests/test_engine_atomicity.py:812-844`.
- The prior auditor blocker was stale durable assertions. That gap is now closed by the updated assertions in `serve/kanban/tests/test_engine_archived_edit.py:1042-1045` and `serve/kanban/tests/test_storage.py:1778-1784`, plus the fresh full kanban regression pass (1338 green).

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC-1 | `storage.allocate_next_id` holds the create lock while invoking the write callback (`serve/kanban/src/owlbear_kanban/storage.py:540-579`), and `create_task` performs the task write through that callback (`serve/kanban/src/owlbear_kanban/engine.py:1018-1044`). Task tests cover empty-board allocation, archive scan, crash-no-burn, and concurrent distinct IDs (`tests/test_engine_1443.py:113-198`, `tests/test_engine_1443.py:285-373`). | PASS |
| AC-2 | `create_task` routes through the allocator callback and does not mutate `config.next_id` (`serve/kanban/src/owlbear_kanban/engine.py:1018-1044`); tests prove scratch-board create without `config.yml` and unchanged `config.next_id` (`tests/test_engine_1443.py:201-260`, `serve/kanban/tests/test_engine_crash_safety.py:183-208`, `serve/kanban/tests/test_storage_io.py:461-472`). | PASS |
| AC-3 | Mixed active/archive max+1 behavior is pinned by `tests/test_engine_1443.py:267-278` and matches the allocator scan logic in `serve/kanban/src/owlbear_kanban/storage.py:556-579`. | PASS |
| AC-4 | Concurrent create tests prove distinct IDs and config non-mutation on one board (`tests/test_engine_1443.py:285-373`), and allocation-only concurrency remains green in `serve/kanban/tests/test_storage_io.py:267-309`. | PASS |
| AC-5 | `KanbanEngine` defaults `activity_log=None` to enabled directly (`serve/kanban/src/owlbear_kanban/engine.py:361-369`), `config_loader` reads only `next_id` from `config.yml` and hardcodes `activity_log` from topology (`serve/kanban/src/owlbear_kanban/config_loader.py:45-58`), and create-task event tests prove one emitted event with all six fields plus `task_status_at_start == entry status` (`tests/test_engine_1443.py:380-451`). | PASS |
| AC-6 | Task-body architecture/builder notes remain aligned with probe `#1442`, and no contradictory repo evidence surfaced in review scope. | PASS |
| AC-7 | `create_task` re-raises on emit failure and prunes the failed create (`serve/kanban/src/owlbear_kanban/engine.py:1058-1072`); atomicity tests prove file deletion, zero activity writes, and no ghost task after rollback (`serve/kanban/tests/test_engine_atomicity.py:812-844`). | PASS |
| AC-8 | Durable tests now assert scan-based `allocate_next_id` semantics on empty boards with unchanged `config.next_id` (`serve/kanban/tests/test_engine_archived_edit.py:1042-1045`, `serve/kanban/tests/test_storage.py:1778-1784`), and the fresh full `serve/kanban/tests/` regression is green at 1338 passed, 0 failed. | PASS |

### Pass 2 - INFORMATIONAL
- The updated durable test names still mention old next-id/increment wording even though their bodies now assert scan-based semantics (`serve/kanban/tests/test_engine_archived_edit.py:1037-1045`, `serve/kanban/tests/test_storage.py:1771-1784`).
- Exact `git diff` / dirty-tree reconstruction was unavailable in-session; current confidence relies on fresh quality-runner output plus git-log commit-presence checks, not direct diff ownership proof.

### Deductions
- `-0.04`: exact `git diff` and dirty-tree inspection unavailable in-session.
- `-0.03`: TestFromAC immutability inferred from current bodies plus commit-presence logs rather than a direct commit diff.
- `-0.02`: AC-1 lock-scope proof relies on source + concurrent/crash behavior rather than a dedicated blocked-write harness.

### Confidence: 0.91
### Verdict: PASS
### Action
- Advance to docs.
[[2026-05-10]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Cycles 3–4 delta: test files only. Source behavior unchanged. `serve/kanban/README.md` verified in prior docs gate pass. |
| 2 | Module docstrings | No | N/A | No source files changed in cycles 3–4. Engine.py module docstring already updated in prior docs gate (commit `1bbd2f34`). |
| 3 | External attribution | No | N/A | No external repos or articles cited in cycles 3–4. |
| 4 | Research doc | No | N/A | No research document produced for this task. |
| 5 | Diagram maintenance (describes match) | No | N/A | Changed files (`serve/kanban/tests/**`) do not match `describes: serve/kanban/src/**` for kanban.excalidraw or mcp-topology.excalidraw. Footers already updated in prior docs gate (commit `1bbd2f34`). |
| 6 | Explicit diagram creation | No | N/A | No new diagram requested. |
| 7 | Deletion detection | No | N/A | No files deleted in cycles 3–4; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/tests/test_engine_atomicity.py` | OUT | test file — no action |
| `serve/kanban/tests/test_engine_archived_edit.py` | OUT | test file — no action |
| `serve/kanban/tests/test_storage.py` | OUT | test file — no action |

### Files Updated
- None (all cycle 3–4 changes are test files; prior docs gate handled all IN-scope docs)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1443-*` files found in `.owlbear/scratch/`)
[[2026-05-10]]
## Audit
### Regression Detection
- quality-runner mode full: 4338 passed, 211 failed, 5 errors (vitest timeouts)
- 211 failures are pre-existing background noise (missing archived task-scoped test files, unrelated modules); no kanban-domain failures
- Kanban suite confirmation: 1355 passed, 0 failed (direct pytest run)
- Prior audit (cycle 3) found 2 task-caused regressions in test_engine_archived_edit.py and test_storage.py — both fixed in cycle 4 (commit eab9d05f)
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changed files: engine.py, storage.py in serve/kanban/src/owlbear_kanban/; tests in tests/test_engine_1443.py, serve/kanban/tests/{test_engine_atomicity,test_engine_crash_safety,test_storage_io,test_engine_archived_edit,test_storage}.py — all kanban domain)
- purpose match: PASS (scan-based ID allocation replaces config-based, create-task activity logging added with emit-failure rollback)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
Original architect missed 2 of 4 downstream test files requiring scan-based updates (test_engine_archived_edit.py, test_storage.py), causing an extra audit rejection cycle. The architect correctly identified test_engine_crash_safety.py and test_storage_io.py but failed to discover all callers of the old allocate_next_id contract. AC-1 through AC-5 were otherwise well-specified. Score confirmed from prior audit cycle.

### Commit Integrity
- upstream commit presence: PASS — 5 task commits verified via git log:
  - 8ccdbe5b (test-writer cycle 1)
  - bef6d7e8 (builder cycle 1)
  - 6feb5132 (builder rollback fix cycle 2)
  - 75df9542 (test-writer retry-3 AC-7)
  - eab9d05f (test-writer cycle 4 AC-8)
- working tree: clean for task files (only kanban task .md modified from auditor claim)
- kanban commit packaging: deferred to post-verdict

### Deduction Breakdown
- -.03: AC quality score ≤ 3 (architect missed downstream test dependencies)
### Confidence: 0.97
### Action: archive