---
id: 1262
title: Extend SSE watcher to recursive kanban_dir with typed multi-surface 
  events
status: review
priority: someday
created: 2026-05-01T09:53:38.519349+00:00
updated: 2026-05-02T02:43:21.266862+00:00
tags:
- cockpit
- backend
parent: 1236
depends_on:
- 1234
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

After #1234 (tasks-only SSE) lands, refactor the watcher from `awatch(tasks_dir, recursive=False)` to `awatch(kanban_dir, recursive=True)` with path-based classification. Emit typed events: `tasks-changed`, `decisions-changed`, `activity-changed`. Add watch filter that accepts tasks/*.md (not .tmp-), decisions/pending/*.md, and activity.jsonl. See .owlbear/research/1236-extend-sse-decisions-activity.md
[[2026-05-02]]
## Research

**Validation pass** — parent research (.owlbear/research/1236-extend-sse-decisions-activity.md) covers this task comprehensively. Findings confirmed against live code:

| Check | Result |
|-------|--------|
| Dep #1234 (tasks-only SSE) | ✓ Done (archived) |
| Dep #1235 (useEventSource hook) | ✓ Done (archived) |
| `engine.kanban_dir` → Path property | ✓ Confirmed |
| `engine.tasks_dir` → Path property | ✓ Confirmed |
| decisions path: `kanban_dir / "decisions" / "pending"` | ✓ Matches `deps.get_decisions_dir` |
| activity path: `kanban_dir / "activity.jsonl"` | ✓ Matches `activity_store._ACTIVITY_FILE` |
| Current events.py: awatch(tasks_dir, recursive=False) | ✓ ~65 LOC, tasks-only |
| decisions/pending dir doesn't exist on disk | ✓ Recursive watch handles this |
| Frontend follow-ups exist (#1263, #1264) | ✓ Both at research status |

**Implementation scope:** ~20 LOC delta — replace `awatch(tasks_dir, recursive=False)` with `awatch(kanban_dir, recursive=True)`, add path-based `watch_filter` + `classify()`, emit typed events per research doc §3.3.

**Classification:** T1 — Autonomous. Extends existing SSE transport with additional event types. No new capability, same architecture.

**Confidence:** 0.85 (high — validated against live code, all deps satisfied, clear pseudocode in parent research)
[[2026-05-02]]


## Acceptance Criteria

- [ ] AC1: Watch filter accepts paths matching: (a) `tasks/*.md` excluding `.tmp-` prefix, (b) `decisions/pending/*.md`, (c) exact `activity.jsonl`; rejects all other paths under `kanban_dir` (td:2)
- [ ] AC2: Path classification returns `"tasks-changed"` | `"decisions-changed"` | `"activity-changed"` | `None` based on which surface the path belongs to; filter and classifier require board-specific paths (`engine.tasks_dir`, decisions/pending dir, activity.jsonl path) (td:2)
- [ ] AC3: `awatch` uses `engine.kanban_dir` with `recursive=True` replacing the current `engine.tasks_dir` with `recursive=False` (td:1)
- [ ] AC4: Each distinct event type in a change batch yields a separate SSE event with `event={type}` and `data={"mtime": <max_st_mtime_ns>}`; if all paths for a type are deleted (stat fails), no event is emitted for that type — same deletion semantics as existing tasks-only endpoint (td:2)
- [ ] AC5: Missing `kanban_dir` → stream returns immediately, no events, no crash (td:1)

## Builder Guidance

- Existing `test_cockpit_events_1234.py` asserts `recursive=False` and imports module-level `_watch_filter` — these will need updating to match the new watch target and filter scope. The test-writer will cover new AC; the builder must ensure both new and updated existing tests pass.
- Research pseudocode in `.owlbear/research/1236-extend-sse-decisions-activity.md` §3.3–§3.4 provides reference implementation. The deletion-only silent behavior (AC4) is deliberate — decisions/activity polling continues independently per §3.5.
- `decisions/pending/` may not exist on disk at startup; recursive watch on `kanban_dir` handles late-created directories automatically.

[[2026-05-02]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One change: extend SSE watcher from tasks-only to multi-surface |
| Interface clarity | PASS | 5 AC lines with precise filter/classify/event contracts |
| Dependency correctness | PASS | Dep #1234 archived/done. No missing deps |
| Module layering | PASS | Only touches events.py; imports from owlbear_kanban engine unchanged |
| TDD compliance | PASS | Routes to todo for test-writer processing |
| KISS/YAGNI | PASS | ~20 LOC delta, no new abstractions, no deletion test needed |
| Premise challenge | PASS | Typed multi-surface events required for frontend follow-ups #1263/#1264 |
| Pattern consistency | PASS | Follows established invalidation-only SSE pattern from #1234 |
| Security surface | PASS | No new user input or external API; read-only file stat for mtime |
| Single domain | PASS | Cockpit backend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| stat() on rapidly deleted file | FileNotFoundError | FileNotFoundError | Yes — existing try/except continues | None — deletion-only batches emit no event; polling catches up |
| decisions/pending/ not yet created | No events for that surface | N/A | Yes — recursive watch detects dir creation | None — 60s poll still active |
| kanban_dir missing | awatch would fail | N/A | Yes — AC5 early-return guard | Clean empty stream |

### Design Diverge
- Trigger: skipped — single clear approach (recursive watch + path classification) with no competing alternatives

### Challenge Results
- Challenger: reconsider (0.34 confidence)
- Challenges raised: (1) AC contradiction between test preservation and recursive=True — resolved by removing contradictory AC6, adding builder guidance; (2) helper contract ambiguity — AC specifies behavior not structure; (3) deletion-only gap — deliberately silent per research §3.5, explicitly documented in AC4; (4) evidence overstatement on confidence — noted, not blocking
- Architect response: revised AC to address all critical/moderate concerns; core design unchallenged

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Wrote 5 verifiable AC lines with td annotations and builder guidance. Advanced to todo.
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_cockpit_events_1262.py
- Classes: TestFromAC_WatchFilter, TestFromAC_Classify, TestFromAC_AWatchTarget, TestFromAC_TypedEvents, TestFromAC_MissingKanbanDir
- Tests per category: happy 6, edge 7, error 3, boundary 3
- Total: 19 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) — board-specific filter | 6 tests | all FAIL |
| AC2 (td:2) — path classifier event types | 5 tests | all FAIL |
| AC3 (td:1) — awatch target kanban_dir + recursive=True | 2 tests | all FAIL |
| AC4 (td:2) — typed events, per-surface mtime, deletion | 5 tests | all FAIL |
| AC5 (td:1) — missing kanban_dir guard | 1 test | FAILS |

Key failure modes:
- AC1: current generic `_watch_filter` accepts any .md (no board scope, no activity.jsonl)
- AC2: current generator only emits `tasks-changed` regardless of path surface
- AC3: current awatch called with `engine.tasks_dir, recursive=False`
- AC4: no per-surface event typing; single global mtime across all paths
- AC5: current guard checks `tasks_dir.exists()`, not `kanban_dir.exists()`

Commit: 1bf6414d — tests/test_cockpit_events_1262.py
[[2026-05-02]]
## Builder Notes
- Implementation: updated serve/cockpit/src/owlbear_cockpit/routes/events.py
- Scope: switched watcher target from engine.tasks_dir (non-recursive) to engine.kanban_dir (recursive), with board-specific path normalization and matching
- AC1/AC2: added board-scoped watch filtering + path classification for tasks/*.md (excluding .tmp-), decisions/pending/*.md, and exact activity.jsonl
- AC3: awatch now uses kanban_dir with recursive=True
- AC4: batch processing now groups by typed event (`tasks-changed`, `decisions-changed`, `activity-changed`) and emits one SSE event per type with per-type max mtime; deletion-only paths remain silent via FileNotFoundError skip
- AC5: stream now early-returns when kanban_dir is missing
- Tests: 19 TestFromAC tests passed in tests/test_cockpit_events_1262.py
- Coverage: 96% for owlbear_cockpit.routes.events
- Lint: clean (ruff)
- Durable module test file: tests/test_cockpit_events.py not present; skipped per workflow
- Commit: 4d8931e1e7bde080cb9a78e945a41626739b5539 (`feat: extend SSE watcher to recursive kanban_dir (#1262, builder)`)

## Post-task Reflection
- Problem faced: initial target path assumption was wrong (`owlbear_cockpit/events.py`); implementation lives in routes/events.py.
- Workaround applied: validated file path from the test contract first, then patched only that route module.
- Pattern discovered: using board-root recursive watch with strict path classification keeps SSE behavior extensible without extra watchers.
- Quality gap noted: there is no durable module-level events test file yet, so regression signal currently relies on task-scoped tests.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped pytest: 19 passed, 0 failed (`tests/test_cockpit_events_1262.py`)

### Lint
- clean (`serve/cockpit/src/owlbear_cockpit/routes/events.py`, `tests/test_cockpit_events_1262.py`)

### Coverage
- `owlbear_cockpit.routes.events`: 96% (missed lines 49, 95, 98)

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: filter accepts board-scoped `tasks/*.md` except `.tmp-`, `decisions/pending/*.md`, exact `activity.jsonl`; rejects others | `TestFromAC_WatchFilter` (`tests/test_cockpit_events_1262.py:147-247`) | No. The suite proves some positives/negatives, but there is no executable `.tmp-` rejection case for the branch in `serve/cockpit/src/owlbear_cockpit/routes/events.py:48`; `.tmp-` appears only in comments/docstrings. | MISSING |
| AC2: classifier returns typed event or `None` using board-specific paths | `TestFromAC_Classify` (`tests/test_cockpit_events_1262.py:265-430`) | No. Positive decisions/activity cases exist, but there is no classifier-negative proof for other-board `decisions/pending/*.md` or other-board `activity.jsonl`, so a name-only implementation for those surfaces could stay green. | MISSING |
| AC3: `awatch(engine.kanban_dir, recursive=True)` | `test_awatch_called_with_kanban_dir_not_tasks_dir`, `test_awatch_called_with_recursive_true` (`tests/test_cockpit_events_1262.py:443-468`) | Yes. These assertions would fail on the old `tasks_dir` / `recursive=False` behavior. | COVERED |
| AC4: one SSE event per surface type with per-type max mtime; deletion-only paths for a type emit nothing | `TestFromAC_TypedEvents` (`tests/test_cockpit_events_1262.py:484-802`) | No. Typed events and per-surface mtimes are covered, but the deletion-only suppression branch at `serve/cockpit/src/owlbear_cockpit/routes/events.py:113` is not. The only delete case still includes a surviving decisions file. | MISSING |
| AC5: missing `kanban_dir` returns immediately with no events and no crash | `test_missing_kanban_dir_awatch_not_called` (`tests/test_cockpit_events_1262.py:816-859`) | No for the `no events` subclause. It proves 200 + `awatch` not called, but does not assert the consumed stream stayed empty. | LAX |

#### Security Review
- No issues found. The route normalizes board-owned paths, compares them against engine-owned directories, reads file mtimes, and emits SSE payloads. No command execution, secret handling, or unsafe deserialization is introduced.

#### Test Integrity
- No weakening/removal is visible in the current snapshot of `tests/test_cockpit_events_1262.py`.
- Confidence deduction applied: builder/test-writer immutability could not be proven from commit diff evidence in this environment.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | Several stream tests stop after the first event or first event/data pair, so extra incorrect events in the same batch could go unobserved (`tests/test_cockpit_events_1262.py:294-298`, `337-341`, `513-517`, `561-565`, `613-617`, `667-671`, `787-791`). |
| Negative/error-path coverage | WEAK | No executable `.tmp-` filter test; no deletion-only suppression test; no classifier-negative coverage for other-board decisions/activity. |
| Manual mutation reasoning | WEAK | Removing the `.tmp-` guard, broadening activity matching from exact path to name-only, or emitting an event for deletion-only batches would still leave parts of the suite green. |
| Test independence | STRONG | Per-test temp boards and consistent dependency override cleanup prevent cross-test contamination. |
| Descriptive names | STRONG | Class/test naming maps cleanly to the AC. |

#### Data Safety
- No issues found. State remains request-local; deleted files are handled by `FileNotFoundError` skip semantics.

#### Implementation-Aware Gaps
- `serve/cockpit/src/owlbear_cockpit/routes/events.py:46-50` implements exact activity-path matching and `.tmp-` rejection, but the `.tmp-` branch is unproven.
- `serve/cockpit/src/owlbear_cockpit/routes/events.py:64-70` correctly classifies board-scoped paths, but decisions/activity board-specific negatives are unproven.
- `serve/cockpit/src/owlbear_cockpit/routes/events.py:109-115` skips vanished files; deletion-only suppression is unproven.
- `serve/cockpit/src/owlbear_cockpit/routes/events.py:79-80` guards missing `kanban_dir`; the empty-stream half of AC5 is unproven.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/cockpit/src/owlbear_cockpit/routes/events.py:35-37` uses builtin `callable` as a return annotation; a precise `Callable[...]` type would document the watch-filter contract better.
- The test file repeats near-identical SSE collection scaffolding; a shared helper that collects the full stream would reduce the chance of reintroducing early-break false greens.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Source behavior matches at `serve/cockpit/src/owlbear_cockpit/routes/events.py:46-50`, but `tests/test_cockpit_events_1262.py:147-247` does not execute the `.tmp-` rejection requirement. | `TestFromAC_WatchFilter` | FAIL |
| AC2 | Source behavior matches at `serve/cockpit/src/owlbear_cockpit/routes/events.py:57-70`, but `tests/test_cockpit_events_1262.py:265-430` does not fully prove board-specific decisions/activity classification. | `TestFromAC_Classify` | FAIL |
| AC3 | `serve/cockpit/src/owlbear_cockpit/routes/events.py:87-93` plus direct assertions in `tests/test_cockpit_events_1262.py:443-468`. | `TestFromAC_AWatchTarget` | PASS |
| AC4 | Source behavior matches at `serve/cockpit/src/owlbear_cockpit/routes/events.py:100-120`, but `tests/test_cockpit_events_1262.py:484-802` misses the deletion-only suppression clause. | `TestFromAC_TypedEvents` | FAIL |
| AC5 | Guard exists at `serve/cockpit/src/owlbear_cockpit/routes/events.py:79-80`, and `tests/test_cockpit_events_1262.py:816-859` proves no `awatch` call, but not the empty-stream/no-events clause. | `TestFromAC_MissingKanbanDir` | FAIL |

### Deductions
- -0.08 AC1 proof gap
- -0.08 AC2 proof gap
- -0.08 AC4 proof gap
- -0.05 AC5 proof gap
- -0.03 early-break false-green pattern across SSE tests
- -0.02 TestFromAC immutability could not be diff-verified

### Confidence: 0.66
### Verdict: FAIL
### Action
- Reject to `todo`.
- Implementation in `serve/cockpit/src/owlbear_cockpit/routes/events.py` appears to satisfy the reviewed contract, but the task does not clear review because AC1, AC2, AC4, and AC5 are not fully proven by executable tests.
- Required follow-up is test-only: add discriminating proof for `.tmp-` rejection, board-specific classifier negatives for decisions/activity, deletion-only suppression, and explicit empty-stream verification for missing `kanban_dir`.
[[2026-05-02]]
## Test-Writer Notes
- Retry: filled 4 reviewer-identified gaps with 5 new tests (surgical fill mode)
- Test file: tests/test_cockpit_events_1262.py
- New tests added to existing TestFromAC_ classes:
  - AC1 gap: `test_filter_rejects_tmp_prefixed_task_md` — proves the .tmp- guard branch is hit
  - AC2 gap: `test_other_board_activity_jsonl_classified_as_none_no_event` — proves exact-path match, not name-only
  - AC2 gap: `test_other_board_decisions_pending_md_classified_as_none_no_event` — proves board-specific decisions classifier
  - AC4 gap: `test_deletion_only_tasks_batch_emits_no_tasks_changed_event` — proves deletion-only suppression per-surface
  - AC5 gap: `test_missing_kanban_dir_stream_is_empty` — proves the no-events subclause, not just no-awatch-call
- Total: 24 tests (19 existing preserved + 5 new), all PASS against current implementation
- Coverage: owlbear_cockpit.routes.events 97%
- Lint: clean (ruff)
- Builder skip: test-only retry, all new tests green against current impl
- Commit: 4cda55d2 — tests/test_cockpit_events_1262.py
[[2026-05-02]]
Test-only retry — 5 new tests all pass against current impl. Builder has no work to do. Advancing directly to review per Step 1b.1.