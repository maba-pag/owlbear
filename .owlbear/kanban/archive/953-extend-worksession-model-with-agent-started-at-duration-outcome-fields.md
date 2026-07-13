---
id: 953
title: Extend WorkSession model with agent, started_at, duration, outcome fields
status: archived
priority: medium
created: 2026-04-18T10:45:23.829337+00:00
updated: 2026-04-18T12:37:08.932026+00:00
tags:
- cockpit
- engine
- phase-1
- type:build
parent: 926
depends_on:
- 952
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Extend the `WorkSession` dataclass to include all 6 AC fields from #926: `task_id`, `agent`, `status` (state), `started_at`, `duration`, `outcome`.

## Acceptance Criteria

- [ ] WorkSession has fields: `task_id: int`, `agent: str`, `state: str`, `started_at: str` (ISO-8601), `duration: float | None` (seconds, None for open sessions), `outcome: str | None` (None for running/stuck)
- [ ] `_collect_task_sessions()` populates all fields from JSONL events
- [ ] `agent` derived from `claim` event detail (the actor/detail field)
- [ ] `started_at` derived from `claim` event timestamp
- [ ] `duration` = close timestamp − claim timestamp (None for open sessions)
- [ ] `outcome` mirrors the end_work detail or "released"/"sweep-released" (None for running/stuck)
- [ ] All existing 23 tests still pass
- [ ] New tests for each added field
- [ ] `WorkSession` exported from `owlbear_kanban.__init__`

## Files

- `serve/kanban/src/owlbear_kanban/engine.py` (WorkSession + _collect_task_sessions)
- `serve/kanban/src/owlbear_kanban/__init__.py` (export)
- `serve/kanban/tests/test_list_sessions.py` (new field assertions)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/953-extend-worksession-model.md
- Sources: 7 studied (all internal), 5 high-relevance
- Recommendation: Direct implementation — all 4 fields derivable from existing JSONL event data (confidence: .90)
- Follow-up tasks created: none (AC is self-contained)
- Decision requests: none

### Key Findings

1. `agent` from claim event `detail` field (confirmed: engine writes `detail=self._agent_name`)
2. `started_at` from claim event `timestamp` (already tracked as `open_claim_ts`)
3. `duration` = close_ts − claim_ts via `total_seconds()` (None for running/stuck incl. superseded claims)
4. `outcome` = raw end_work detail string, "released" for release, None for running/stuck
5. All 23 existing tests access `.task_id`/`.state` via list_sessions() — no direct WorkSession construction, so adding required fields won't break them
6. ~20 LOC change total across 3 files (engine.py, __init__.py, test_list_sessions.py)
[[2026-04-18]]

## Architecture Review

### AC Refinements (supersede original lines where noted)

__AC line 3 (refined):__ `agent` derived from claim event `detail` field (NOT `actor` — both happen to equal `self._agent_name` for claims, but `detail` is canonical per engine.py L752).

__AC line 5 (refined):__ `duration` = `(close_dt - claim_dt).total_seconds()` where both timestamps are normalized to UTC (apply same `tzinfo is None` guard as `_state_from_age`). `None` for open sessions AND superseded claims.

__AC line 6 (refined):__ `outcome` = raw `end_work` detail string for completed sessions; `"released"` for `release` action; `None` for running/stuck/superseded. __`sweep-release` continues to produce no session__ (existing behavior unchanged — do NOT add a "sweep-released" outcome).

__New AC line (superseded claims):__ For superseded claims (new claim arrives before close), the orphaned session gets: `agent` from original claim `detail`, `started_at` from original claim `timestamp`, `duration=None`, `outcome=None`, `state` from age-based classification (existing behavior).

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extends one dataclass + one helper function |
| Interface clarity | PASS (after refinement) | Sweep-released ambiguity fixed; superseded-claim case explicit |
| Dependency correctness | PASS | #952 archived (done) |
| Module layering | PASS | Changes confined to engine.py, __init__.py, tests — no upward imports |
| TDD compliance | PASS | type:build tag; test-writer processes first; AC line 8 mandates new field tests |
| KISS/YAGNI | PASS | Exact fields needed for cockpit Activity tab, no extras |
| Premise challenge | PASS | Fields required by parent #926 plan |
| Pattern consistency | PASS | Follows existing _state_from_age() timezone pattern,_collect_task_sessions() state machine |
| Security surface | PASS | No new system boundaries; reads existing JSONL |
| Single domain | PASS | Engine domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Duration calc: tz-naive − tz-aware | TypeError | datetime subtraction | Must handle — normalize both to UTC | None if handled per refined AC |

### Challenge Results

- Challenger: __reconsider__ (confidence 0.55)
- Architect response: __accepted C1 (sweep-released), C3 (timezone), superseded-claims blind spot__ — all 3 addressed via AC refinements above. Rebutted C2 (raw outcome is intentional — state provides normalized classification, outcome provides display context). Rebutted premature-export concern (parent #926 requires it).

### Verdict: APPROVE (after refinement)

### Action Taken: Refined AC lines 3, 5, 6 and added explicit superseded-claim AC. Advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/kanban/tests/test_list_sessions.py`
- Classes: `TestFromAC_WorkSessionFields`
- Tests per category: happy 10, edge 4, error 6, boundary 4
- Total: __24 tests, all FAIL__ (24 `AttributeError` — `WorkSession` missing `agent`, `started_at`, `duration`, `outcome` fields; `WorkSession` not in `__all__`)
- Existing 24 tests (`TestFromAC_ListSessions` + `TestBuilderDiscovered`): all __PASS__ (unaffected)
- ruff: __clean__
- Commit: `3bb05c96`

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 — 6 fields present | `test_session_has_agent_field`, `test_session_has_started_at_field`, `test_session_has_duration_field`, `test_session_has_outcome_field` |
| AC3 — agent from claim detail | `test_agent_equals_claim_event_detail`, `test_agent_is_detail_not_actor` |
| AC4 — started_at from claim ts | `test_started_at_equals_claim_timestamp`, `test_started_at_is_iso8601_string` |
| AC5 — duration math + None for open/superseded | `test_duration_is_close_minus_claim_seconds`, `test_duration_is_none_for_running_session`, `test_duration_is_none_for_stuck_session`, `test_duration_is_none_for_superseded_claim`, `test_duration_with_tz_naive_claim_timestamp`, `test_duration_is_set_for_released_session` |
| AC6 — outcome raw detail / "released" / None | `test_outcome_is_raw_end_work_detail_for_success`, `test_outcome_is_raw_end_work_detail_for_fail`, `test_outcome_is_released_string_for_release_event`, `test_outcome_is_none_for_running_session`, `test_outcome_is_none_for_stuck_session`, `test_outcome_is_none_for_superseded_claim` |
| AC9 — WorkSession exported | `test_worksession_exported_from_package`, `test_worksession_in_package_all` |
| New AC — superseded claim fields | `test_superseded_claim_agent_from_original_claim_detail`, `test_superseded_claim_started_at_from_original_claim_timestamp` |
[[2026-04-18]]

## Builder Notes

### Files Changed

- `serve/kanban/src/owlbear_kanban/engine.py` — Extended `WorkSession` with 4 new fields (`agent: str`, `started_at: str`, `duration: float | None`, `outcome: str | None`); added `_compute_duration()` helper (tz-naive normalization); updated all 3 `WorkSession(...)` construction sites in `_collect_task_sessions()` to populate new fields; reset `open_claim_agent` in all close paths including sweep-release
- `serve/kanban/src/owlbear_kanban/__init__.py` — Added `WorkSession` to import and `__all__`

### Test Results

- `serve/kanban/tests/test_list_sessions.py`: __48 passed__ (24 `TestFromAC_WorkSessionFields` + 24 existing `TestFromAC_ListSessions` + `TestBuilderDiscovered`)
- No builder-discovered tests needed — AC covered all edge cases

### Lint

- ruff: __clean__

### Coverage

- Not measured separately; all 48 tests pass against 2-file change (~46 LOC)

### Commit

- `52914884`: feat: extend WorkSession with agent, started_at, duration, outcome fields (#953, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- pytest: 48 passed, 0 failed (independent run via quality-runner)

### Lint

- ruff: clean

### Coverage

- owlbear_kanban: 100%
- owlbear_kanban.engine: 30% overall (scope artifact — engine.py is a large module; touched functions WorkSession,_compute_duration,_collect_task_sessions have full AC test coverage across 48 tests; other engine functions exercised by separate test files)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — 6 fields present | test_session_has_agent_field, test_session_has_started_at_field, test_session_has_duration_field, test_session_has_outcome_field | Fails on AttributeError if field absent; value correctness covered by AC3–AC6 tests | LAX (compensated) |
| AC3 — agent from claim detail | test_agent_equals_claim_event_detail, test_agent_is_detail_not_actor | Yes — exact string equality + inequality checks | COVERED |
| AC4 — started_at from claim ts | test_started_at_equals_claim_timestamp, test_started_at_is_iso8601_string | Yes — exact string match + fromisoformat parse | COVERED |
| AC5 — duration math + UTC + None for open/superseded | test_duration_is_close_minus_claim_seconds, test_duration_is_none_for_running_session, test_duration_is_none_for_stuck_session, test_duration_is_none_for_superseded_claim, test_duration_with_tz_naive_claim_timestamp, test_duration_is_set_for_released_session | Yes — pytest.approx(1800.0) with explicit math, explicit None checks, tz-naive + tz-aware mix | COVERED |
| AC6 — outcome raw/released/None | test_outcome_is_raw_end_work_detail_for_success, test_outcome_is_raw_end_work_detail_for_fail, test_outcome_is_released_string_for_release_event, test_outcome_is_none_for_running_session, test_outcome_is_none_for_stuck_session, test_outcome_is_none_for_superseded_claim | Yes — exact string equality + explicit None checks | COVERED |
| AC7 — existing 23 tests pass | Verified by quality-runner run (48 total = 24 new + 24 existing) | N/A | COVERED |
| AC8 — new tests per field | 24 new tests in TestFromAC_WorkSessionFields | N/A | COVERED |
| AC9 — WorkSession exported + in __all__ | test_worksession_exported_from_package, test_worksession_in_package_all | Yes — hasattr check + __all__ membership | COVERED |
| New AC — superseded claim fields | test_superseded_claim_agent_from_original_claim_detail, test_superseded_claim_started_at_from_original_claim_timestamp | Yes — exact string equality on original claim values | COVERED |

#### Security Review

- No hardcoded secrets
- JSON deserialization: stdlib json.loads only; no pickle/eval/yaml.load
- Path construction: hardcoded filename, no user input in path
- Timestamp parsing: stdlib datetime.fromisoformat; wrapped in try/except in _read_log_entries
- No injection, traversal, or insecure deserialization issues

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 24 TestFromAC_WorkSessionFields tests | Not modified by builder (test file unchanged) | N/A |
| All 24 TestFromAC_ListSessions + TestBuilderDiscovered tests | Not modified | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | 20/24 tests: exact string/float comparisons with pytest.approx(), double-sided assertions; 4/24 existence-only (compensated by value tests for each field) |
| Negative/error-path coverage | STRONG | Explicit None checks for running/stuck/superseded; both happy and error paths for all fields |
| Mutation resistance | STRONG | Concrete math (1800s, 3600s), exact strings, double-sided assertions (detail != actor) |
| Test independence | STRONG | Each test creates its own JSONL log via _write_log; no shared mutable state |
| Descriptive names | STRONG | All tests follow test_<noun>_<condition> pattern |

#### Data Safety

- No unvalidated LLM output persistence
- No race conditions in changed code
- No unbounded input to resource-intensive operations

#### Implementation-Aware Gaps

- Empty agent detail fallback (engine.py:124 `open_claim_agent or ""`) not explicitly tested; however, this is a defensive guard on pre-existing code logic, not new behavior from this task. Claim events always carry a detail field in practice.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- 4 field-existence tests (L560–583) could be strengthened with type/value assertions, though each field has strong compensating value tests
- Empty agent detail (`claim` event with `detail=""`) edge case undocumented/untested; safe fallback (`agent=""`) but behavior not specified

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 — 6 fields | engine.py:46–56 (WorkSession dataclass) | test_session_has_*_field (existence) + value tests | PASS |
| AC2 — _collect_task_sessions populates all fields | engine.py:93–155 | All 24 TestFromAC_WorkSessionFields | PASS |
| AC3 — agent from claim detail | engine.py:133 `open_claim_agent = detail` | test_agent_equals_claim_event_detail | PASS |
| AC4 — started_at from claim ts | engine.py:132 `open_claim_ts = ts` | test_started_at_equals_claim_timestamp | PASS |
| AC5 — duration calc + UTC + None | engine.py:75–83 (_compute_duration) + 117–126, 150–155 | test_duration_is_close_minus_claim_seconds, test_duration_with_tz_naive_claim_timestamp | PASS |
| AC6 — outcome raw/released/None, no sweep-release session | engine.py:138–155 | test_outcome_is_raw_end_work_detail_for_success, test_outcome_is_released_string_for_release_event | PASS |
| AC7 — existing tests pass | Quality-runner: 48/48 passed | All pre-existing tests | PASS |
| AC8 — new tests per field | test_list_sessions.py:544–900 (24 new tests) | TestFromAC_WorkSessionFields | PASS |
| AC9 — WorkSession exported | __init__.py:9,13 (import + __all__) | test_worksession_exported_from_package, test_worksession_in_package_all | PASS |
| New AC — superseded claim fields | engine.py:117–126 (WorkSession construction in superseded path) | test_superseded_claim_agent_from_original_claim_detail | PASS |

### Confidence: .96

### Verdict: PASS

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | WorkSession exported with 4 new fields; `.github/copilot-instructions.md` covers only branch structure and cockpit frontend — no kanban engine API table exists; no update required |
| 2 | Module docstrings | Yes | Verified | `WorkSession`: `"""One claim cycle derived from the activity log."""` ✓; `_compute_duration`: docstring accurate ✓; `_collect_task_sessions`: docstring at line 98 ✓; `__init__.py` module docstring says "its public models" — correctly encompasses WorkSession ✓ |
| 3 | External attribution | No | N/A | Task body confirms "7 studied (all internal), 5 high-relevance" — no external sources used |
| 4 | CLI changes | No | N/A | No CLI additions or modifications |
| 5 | Research doc | Yes | Verified | `.owlbear/research/953-extend-worksession-model.md` exists; linked from task body; follow-up tasks: none (AC self-contained) |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `953-*` scratch files found)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — 6 fields present | engine.py:47-55 — WorkSession dataclass with task_id, state, agent, started_at, duration, outcome | PASS |
| AC2 — _collect_task_sessions populates all | engine.py:98-160 — all 3 construction sites (superseded, close, unclosed) populate all fields | PASS |
| AC3 — agent from claim detail | engine.py:133 `open_claim_agent = detail` where action == "claim" | PASS |
| AC4 — started_at from claim ts | engine.py:132 `open_claim_ts = ts` where action == "claim" | PASS |
| AC5 — duration calc + UTC + None | engine.py:75-83 `_compute_duration` with tz-naive normalization; None for open/superseded sessions | PASS |
| AC6 — outcome raw/released/None | engine.py:138-155 — raw detail for end_work, "released" for release, None for running/stuck/superseded; sweep-release produces no session | PASS |
| AC7 — existing tests pass | Quality-runner: 498 passed full suite; all 24 pre-existing kanban tests pass | PASS |
| AC8 — new tests per field | 24 new tests in TestFromAC_WorkSessionFields (test_list_sessions.py:540-900) | PASS |
| AC9 — WorkSession exported | __init__.py:10 import + L17 in __all__ | PASS |
| New AC — superseded claim fields | engine.py:117-126 — agent/started_at from original claim, duration=None, outcome=None | PASS |

### Test Results

- pytest: 498 passed, 6 failed (all mcp-knowledge — get_stats schema tests + limit_forwarded + skill_md path), 33 errors (cockpit ImportError: cannot import 'get_engine') — all pre-existing, outside task scope. Zero kanban failures.
- ruff: clean

### Architect Quality: 5/5

Highly specific AC with exact field types, derivation sources, edge cases (superseded claims, tz-naive timestamps, sweep-release). Architect refinements after challenger review added valuable clarity (detail vs actor, superseded-claim behavior). No builder improvisation needed.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 10 PASS) → -0.00
- Lint violations: 0 → -0.00
- AC quality ≤ 3: no (5/5) → -0.00
- Missing reviewer evidence: no (detailed, .96 PASS) → -0.00
- Full-suite failures in task scope: 0 → -0.00

### Confidence: 1.00

### Action: archive
