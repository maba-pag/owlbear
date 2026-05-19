---
id: 923
title: 'P1-01: RED — list_sessions() engine helper tests'
status: archived
priority: important
created: 2026-04-17T19:57:10.925706+00:00
updated: 2026-04-18T10:39:20.784336+00:00
tags:
- cockpit
- engine
- phase-1
- type:test
parent: 920
depends_on:
- 921
- 922
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Write failing tests for the `list_sessions()` engine helper that derives logical Work Sessions from `activity.jsonl` events (D10).

## Acceptance Criteria

- [ ] Test file at `tests/test_list_sessions.py`
- [ ] Tests cover:
  - Derives one session per claim cycle (claim event through release/end_work event)
  - Session states: running, stuck, released, completed-pass, completed-fail, completed-rejected
  - Stuck detection: claim older than configured timeout with no subsequent activity
  - Filter by state: active-only (default), all, failed-or-rejected, released
  - Empty activity log returns empty list
  - Malformed/incomplete entries are skipped gracefully
  - Multiple sessions for same task (re-claimed after release) are distinct rows
- [ ] All tests fail (RED phase — implementation does not exist yet)
- [ ] Tests import from `owlbear_kanban` package (engine domain, not cockpit)

## Files

- `tests/test_list_sessions.py`
[[2026-04-18]]

## Research

- Research doc: `.owlbear/research/923-list-sessions-tests.md`
- Sources: 6 studied (all internal), 4 high-relevance
- Recommendation: test design sound; tests should use explicit detail prefixes (F1), map block→completed-fail (F2), build JSONL fixtures directly (confidence: .82)
- Key finding: `end_work` detail format is ambiguous for success vs reject — both produce `"X -> Y"`. Follow-up #951 created to prefix outcome type.
- Follow-up tasks created: #951 (prefix end_work detail with outcome type) at research
- Decision requests: none
- Test scenario matrix: 16 scenarios covering all 6 session states + edge cases (empty log, malformed entries, re-claim cycles, multi-task interleaving, filters)
[[2026-04-18]]

## Architecture Review

### AC Refinements (supersede original where they differ)

**Path fix:** Test file at `serve/kanban/tests/test_list_sessions.py` (not root `tests/`)

**Revised AC:**

- [ ] Test file at `serve/kanban/tests/test_list_sessions.py`
- [ ] Tests cover:
  - Derives one session per claim cycle (claim event through release/end_work event)
  - Session states: running, stuck, released, completed-pass, completed-fail, completed-rejected
  - `end_work(block)` outcome maps to completed-fail state (not a 7th state)
  - Stuck detection: claim older than configured timeout with no subsequent activity events in the log; anti-test: claim older than timeout WITH recent mid-session activity (edit/move) remains running, not stuck
  - `sweep-release` dual events: engine sweep produces `release` + `sweep-release` pair for each expired claim — session closes as released without phantom second session from the `sweep-release` event
  - Filter by state: active-only (default), all, failed-or-rejected, released
  - Empty activity log returns empty list
  - Malformed/incomplete entries are skipped gracefully
  - Multiple sessions for same task (re-claimed after release) are distinct rows
- [ ] All tests fail (RED phase — implementation does not exist yet)
- [ ] Tests import `KanbanEngine` from `owlbear_kanban` and call `engine.list_sessions()` — method on engine, not standalone function. Each test fails at method call (AttributeError), not at import (ImportError)
- [ ] Test fixtures build JSONL activity data directly (inline `tmp_path / "activity.jsonl"`, not via engine operations)

**Files:** `serve/kanban/tests/test_list_sessions.py`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for one function only |
| Interface clarity | PASS (after refinement) | Engine method, 6 states + block mapping explicit, sweep dual-event addressed, stuck anti-test added |
| Dependency correctness | PASS | #921 (bench) and #922 (mockup) both archived/done |
| Module layering | PASS | Tests in kanban package, imports from owlbear_kanban |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | ~18 scenarios (16 + sweep dual-event + stuck anti-test) — comprehensive but not excessive for 6 states + filters + edge cases |
| Premise challenge | PASS | D10 brief explicitly calls for `list_sessions` engine helper |
| Pattern consistency | PASS | Follows `test_mtime_cache_942.py` patterns (inline fixtures, tmp_path, KanbanEngine import) |
| Security surface | N/A | Test file, no new system boundaries |
| Single domain | PASS | Engine domain only |

### Challenge Results

- Challenger: reconsider (confidence 0.50)
- Architect response: **Accepted all 5 challenges** — C1 (sweep dual events), C2 (stuck anti-test), C3 (engine method import) incorporated into refined AC; C4 (#951→#926 dep) noted as follow-up; C5 (release detail) noted as fixture guidance

### Architecture Notes

- **#951 dependency gap:** Task #926 (GREEN) should add #951 (detail prefix) to its `depends_on` list. The RED tests should write fixtures with the prefixed format (`"success: X -> Y"`) per research recommendation, but this dependency must be wired before GREEN proceeds. Follow-up for #926 architect review.
- **Return type:** Not constrained in AC — test-writer defines the contract through tests (standard RED practice). #926 AC specifies "Pydantic model or TypedDict" which the GREEN phase will align to.
- **Existing patterns:** `activity_log.py` schema (5 fields), `engine.py` L813-820 detail formats, `dispatch.py` L81-88 `_claim_is_active()` timeout logic all verified in codebase.

### Verdict: APPROVE (after refinement)

### Action Taken: Refined AC (path fix, sweep dual-event scenario, stuck anti-test, engine method specification, block→completed-fail mapping), advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/kanban/tests/test_list_sessions.py`
- Classes: `TestFromAC_ListSessions`
- Tests per category: happy 7, edge 5, error 3, boundary 7
- Total: **22 tests, all FAIL** (AttributeError: 'KanbanEngine' object has no attribute 'list_sessions')
- ruff: clean

### AC Coverage

| AC Line | Test(s) |
|---------|---------|
| One session per claim cycle | `test_claim_to_end_work_is_one_session` |
| State: completed-pass | `test_end_work_success_state_is_completed_pass` |
| State: completed-fail (fail) | `test_end_work_fail_state_is_completed_fail` |
| State: completed-fail (block) | `test_end_work_block_maps_to_completed_fail` |
| State: completed-rejected | `test_end_work_reject_state_is_completed_rejected` |
| State: released | `test_release_event_state_is_released` |
| State: running | `test_open_recent_claim_state_is_running` |
| Stuck detection | `test_old_claim_no_activity_state_is_stuck` |
| Stuck anti-test (recent activity) | `test_old_claim_with_recent_activity_is_running_not_stuck` |
| sweep-release dual events (no phantom) | `test_sweep_release_pair_produces_one_released_session` |
| Filter: active-only default | `test_default_filter_returns_running_and_stuck_only`, `test_active_only_excludes_released` |
| Filter: all | `test_filter_all_returns_every_session` |
| Filter: failed-or-rejected | `test_filter_failed_or_rejected_includes_fail_and_reject`, `test_filter_failed_or_rejected_excludes_pass_and_released` |
| Filter: released | `test_filter_released_returns_released_sessions_only` |
| Empty log → [] | `test_empty_activity_log_returns_empty_list` |
| Missing log → [] | `test_missing_activity_log_returns_empty_list` |
| Malformed JSON skipped | `test_malformed_json_line_skipped_gracefully` |
| Incomplete entry skipped | `test_incomplete_entry_missing_fields_skipped_gracefully` |
| Re-claim → 2 distinct sessions | `test_reclaim_after_release_produces_two_distinct_sessions` |
| Multi-task interleaved | `test_interleaved_events_attributed_to_correct_task` |

### Implementation Notes for Builder

- `engine.list_sessions(filter="active")` — method on KanbanEngine, reads from `self._activity_log_path`
- detail prefix format: `"success: X -> Y"`, `"reject: X -> Y"`, `"outcome=fail"`, `"blocked: reason"`
- Timeout from `self._parse_claim_timeout()` (config `claim_timeout: 1h`)
- Sessions returned have at minimum `.task_id` (int) and `.state` (str)
- **#951 dependency:** GREEN phase (#926) must adopt prefixed detail format (research F1 option B)

### Commit

`7ebdb2a1` — test: add failing tests for list_sessions() engine helper (#923, test-writer)
[[2026-04-18]]

## Builder Notes

**Files changed:** `serve/kanban/src/owlbear_kanban/engine.py` (1 file, +148 lines)

**Implementation:**

- Module-level `WorkSession` dataclass (`.task_id: int`, `.state: str`)
- Module-level helpers: `_classify_end_work()`, `_collect_task_sessions()`, `_apply_session_filter()`, `_CLOSE_ACTIONS` constant
- `KanbanEngine.list_sessions(*, filter="active")` — reads log, calls `_derive_sessions()`, applies filter
- `KanbanEngine._read_log_entries()` — JSONL parser (skips malformed/incomplete lines)
- `KanbanEngine._derive_sessions()` — groups by task_id, calls `_collect_task_sessions`

**Session state logic:**

- `end_work` detail: `"success: ..."` → completed-pass, `"reject: ..."` → completed-rejected, all other → completed-fail
- `release` → released; `sweep-release` after release → ignored (no phantom session)
- Open claim age: uses most recent event timestamp; < timeout → running, ≥ timeout → stuck

**Test results:** 22 passed (all TestFromAC_ListSessions), 116 passed (full kanban suite), 0 failed
**Ruff:** clean
**Coverage:** 27% of engine.py overall (expected — only list_sessions tested; new code is ~90%+ covered)
**Commit:** `19f22edb` — feat: implement list_sessions() engine helper (#923, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

pytest: **22 passed, 0 failed** (serve/kanban/tests/test_list_sessions.py)
Full suite: 116 passed (builder report — not independently re-run)
ruff: **clean**
Coverage: 27% of engine.py overall (expected — only list_sessions path touched)

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Test file at serve/kanban/tests/test_list_sessions.py | File exists, 22 tests in TestFromAC_ListSessions | — | PASS |
| One session per claim cycle | `assert len == 1` on claim→end_work sequence | `test_claim_to_end_work_is_one_session` | PASS |
| State: running | exact list equality `== ["running"]` | `test_open_recent_claim_state_is_running` | PASS |
| State: stuck | exact list equality `== ["stuck"]` | `test_old_claim_no_activity_state_is_stuck` | PASS |
| State: released | exact list equality `== ["released"]` | `test_release_event_state_is_released` | PASS |
| State: completed-pass | exact state match | `test_end_work_success_state_is_completed_pass` | PASS |
| State: completed-fail | exact state match | `test_end_work_fail_state_is_completed_fail` | PASS |
| State: completed-rejected | exact state match | `test_end_work_reject_state_is_completed_rejected` | PASS |
| end_work(block) → completed-fail | `"blocked: …"` detail asserts completed-fail | `test_end_work_block_maps_to_completed_fail` | PASS |
| Stuck anti-test (recent activity → running) | 2h claim + 5min edit → running | `test_old_claim_with_recent_activity_is_running_not_stuck` | PASS |
| sweep-release → one session | `len == 1`, `state == "released"` | `test_sweep_release_pair_produces_one_released_session` | PASS |
| Filter: active-only default | two tests: inclusion + exclusion | `test_default_filter_returns_running_and_stuck_only`, `test_active_only_excludes_released` | PASS |
| Filter: all | `{20,21,22}.issubset(returned_ids)` | `test_filter_all_returns_every_session` | PASS |
| Filter: failed-or-rejected | include + exclude tests | `test_filter_failed_or_rejected_*` (×2) | PASS |
| Filter: released | `state set ≤ {"released"}` | `test_filter_released_returns_released_sessions_only` | PASS |
| Empty log → [] | `assert sessions == []` | `test_empty_activity_log_returns_empty_list` | PASS |
| Missing log → [] | log file never created | `test_missing_activity_log_returns_empty_list` | PASS |
| Malformed JSON skipped | surrounding valid entries returned | `test_malformed_json_line_skipped_gracefully` | PASS |
| Incomplete entry (missing keys) skipped | subsequent entry still processed | `test_incomplete_entry_missing_fields_skipped_gracefully` | PASS |
| Re-claim → 2 distinct sessions | `len == 2`, both states checked | `test_reclaim_after_release_produces_two_distinct_sessions` | PASS |
| Multi-task interleaved | `by_task[80].state`, `by_task[81].state` | `test_interleaved_events_attributed_to_correct_task` | PASS |

### Pass 1 — Critical Failures

#### ❌ 5.4 Data Safety — Unguarded `ValueError` for malformed timestamps (engine.py ~L103)

`_read_log_entries` validates that the keys `"action"`, `"task_id"`, `"detail"`, `"timestamp"` are all present but does **not** validate that the `timestamp` value is a parseable ISO-8601 string. A JSONL entry like:

```json
{"action":"claim","task_id":1,"detail":"x","timestamp":"not-a-date"}
```

passes the key-presence check, enters `_collect_task_sessions`, assigns `open_claim_ts = "not-a-date"`, and then crashes `datetime.fromisoformat("not-a-date")` with an unhandled `ValueError` that propagates out of `list_sessions()`. This directly violates AC: **"Malformed/incomplete entries are skipped gracefully."**

**Fix:** Wrap `datetime.fromisoformat(entry["timestamp"])` in a `try/except ValueError` inside `_read_log_entries` (or at point of parse) and skip the entry.

#### ❌ 5.5 Test Gap — Crash path for malformed timestamp (no test)

The above crash path has no test. `test_malformed_json_line_skipped_gracefully` covers bad JSON syntax; `test_incomplete_entry_missing_fields_skipped_gracefully` covers missing keys. Neither covers: **valid JSON, all keys present, invalid timestamp value**. The AC's graceful-skip guarantee is not fully tested.

**Fix:** Add a `TestFromAC_ListSessions` test: write a JSONL log containing one entry with all required keys but `"timestamp": "not-a-date"`, sandwiched between two valid entries, and assert the two valid sessions are returned.

### Pass 1 — Passed Criteria

- 5.0 AC-to-Test Coverage: 21/21 COVERED (every assertion would fail on AC violation)
- 5.1 Security: clean — no secrets, no injection, no path traversal, no insecure deserialization
- 5.2 Test Integrity: no builder modifications to TestFromAC_* methods
- 5.3 Test Quality: STRONG–ADEQUATE across all 5 dimensions, no WEAK rating
- 5.7 Builder Process: one clean iteration, no loop

### Informational (non-blocking)

- **Gap 1 — Double-claim without close (engine.py:84–86):** If a task log has two consecutive `claim` events with no close event between them, the first open claim is silently classified as `"stuck"` regardless of its age. This implicit behavior is not in the AC and not tested. May be intentional, but warrants documentation or a `TestBuilderDiscovered` test.
- **Gap 3 — Unknown filter returns all (engine.py:122–123):** An unrecognised filter string silently returns the full unfiltered session list (same as `"all"`). Not in AC; no test probes this. Could mask caller bugs.
- **6.3 — `test_filter_all_returns_every_session` uses `.issubset`:** `{20,21,22}.issubset(returned_ids)` passes even if extra unexpected sessions are returned. `returned_ids == {20,21,22}` would be more precise.

### Verdict

**Confidence: .68 → FAIL**

Deductions: -0.20 (data safety / unguarded ValueError propagating from list_sessions), -0.12 (test gap for same crash path not tested).

**Action:** → `in-progress` (builder adds timestamp parse guard in `_read_log_entries` + test-writer adds malformed-timestamp test to `TestFromAC_ListSessions`)
[[2026-04-18]]

## Builder Notes (review fix)

**Files changed:** `serve/kanban/src/owlbear_kanban/engine.py` (+4 lines), `serve/kanban/tests/test_list_sessions.py` (+39 lines)

**Reviewer finding addressed:**

- **5.4 Data Safety:** Added `try/except ValueError` around `datetime.fromisoformat(str(entry["timestamp"]))` in `_read_log_entries`. Entries with all required keys but unparseable timestamp values are now skipped gracefully, closing the unguarded crash path.
- **5.5 Test Gap:** Added `TestBuilderDiscovered::test_invalid_timestamp_value_skipped_gracefully` — valid JSON with all required keys but `"timestamp": "not-a-date"`, sandwiched between two valid entries. Verified RED (ValueError crash) then GREEN (graceful skip).

**Test results:** 23 passed (test_list_sessions.py), 117 passed (full kanban suite), 0 failed
**Ruff:** clean
**Commit:** `76eb0084` — fix: guard against unparseable timestamp in _read_log_entries (#923, builder)
[[2026-04-18]]

## Review Evidence

### Test Results (independent)

- pytest: **23 passed, 0 failed** (`serve/kanban/tests/test_list_sessions.py`)
- ruff: **clean**
- Coverage: 28% of `owlbear_kanban.engine` overall (expected — only `list_sessions` path in scope; new code ~90%+ covered)

### Pass 2 Focus — Reviewer Findings from Pass 1

#### Finding 5.4: Unguarded `ValueError` for malformed timestamps

**RESOLVED ✅**
`_read_log_entries` now wraps `datetime.fromisoformat(str(entry["timestamp"]))` in `try/except ValueError` at engine.py ~L1063–L1066. Guard is placed at the gatekeeper before entries are appended — only pre-validated timestamps reach `_collect_task_sessions`. A `"not-a-date"` timestamp value skips the entry cleanly.

No other vulnerable `fromisoformat` calls exist. The four other call sites (L102, L447, L451, L610, L931) all consume engine-controlled `Task` object fields, not external JSONL data.

#### Finding 5.5: Missing test for malformed-timestamp crash path

**RESOLVED ✅**
`TestBuilderDiscovered::test_invalid_timestamp_value_skipped_gracefully` (test_list_sessions.py ~L407–L437):

- Valid JSON with all required keys; `"timestamp": "not-a-date"`
- Sandwiched between two valid entries (task_ids 90 and 92)
- Asserts 90 ∈ returned_ids, 91 ∉ returned_ids, 92 ∈ returned_ids
- Uses `filter="all"` — no filter masking
- Test is well-constructed and would fail on the unguarded implementation

### AC Compliance Table (Pass 2 — all carry-forward from Pass 1)

| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at `serve/kanban/tests/test_list_sessions.py` | File exists, 23 tests | PASS |
| One session per claim cycle | `assert len == 1` | PASS |
| State: running | exact list equality | PASS |
| State: stuck | exact list equality | PASS |
| State: released | exact list equality | PASS |
| State: completed-pass | exact state match | PASS |
| State: completed-fail (fail) | exact state match | PASS |
| State: completed-fail (block) | `"blocked: …"` → completed-fail | PASS |
| State: completed-rejected | exact state match | PASS |
| Stuck anti-test (recent activity → running) | 2h claim + 5min edit | PASS |
| sweep-release → one session | len==1, state==released | PASS |
| Filter: active-only default | inclusion + exclusion tests | PASS |
| Filter: all | issubset check | PASS |
| Filter: failed-or-rejected | include + exclude tests | PASS |
| Filter: released | state set check | PASS |
| Empty log → [] | `assert sessions == []` | PASS |
| Missing log → [] | no file created | PASS |
| Malformed JSON skipped | valid entries returned | PASS |
| Incomplete entry (missing keys) skipped | subsequent entry processed | PASS |
| Re-claim → 2 distinct sessions | len==2, both states checked | PASS |
| Multi-task interleaved | by_task[80].state, by_task[81].state | PASS |

### Test Integrity (TestFromAC_* Modifications)

All 20 `TestFromAC_ListSessions` methods present and unchanged. Builder added `TestBuilderDiscovered` as a separate class — no merge, no weakening.

### Security

Clean — no secrets, no injection vectors, no path traversal, no insecure deserialization. New code reads `str(entry["timestamp"])` as a safe string coercion before fromisoformat.

### Informational (carry-forward, non-blocking)

- **Gap 1 — Double-claim without close:** Implicit `"stuck"` state regardless of age; undocumented, untested. Low severity.
- **Gap 3 — Unknown filter returns all:** Silent fallback; no test probes it. Low severity.
- **6.3 — `test_filter_all` uses `.issubset`:** `{20,21,22}.issubset(returned_ids)` passes with extra sessions present; `==` would be tighter. Low severity.

### Verdict

**Confidence: .93 → PASS**

Pass 1 deductions (-0.32) fully resolved. No new deductions. Informational items documented but non-blocking.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `list_sessions()` is an internal engine method; `.github/copilot-instructions.md` covers branches/cockpit only — no KanbanEngine API table exists |
| 2 | Module docstrings | Yes | Verified | `WorkSession` docstring accurate; `list_sessions()` has full Args/Returns docstring; all four module-level helpers have docstrings. No gaps. |
| 3 | External attribution | No | N/A | Research notes: "6 sources studied (all internal)" — no external patterns used |
| 4 | CLI changes | No | N/A | No CLI additions or modifications |
| 5 | Research doc | Yes | Verified | `.owlbear/research/923-list-sessions-tests.md` exists, linked in task body; follow-up #951 created |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/923-*` files found)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at `serve/kanban/tests/test_list_sessions.py` | File exists, 21 test methods (20 TestFromAC + 1 TestBuilderDiscovered) | PASS |
| One session per claim cycle | `test_claim_to_end_work_is_one_session` — assert len==1 | PASS |
| States: running, stuck, released, completed-pass/fail/rejected | 7 dedicated tests, reviewer mapped each with exact assertions | PASS |
| end_work(block) → completed-fail | `test_end_work_block_maps_to_completed_fail` | PASS |
| Stuck anti-test (recent activity → running) | `test_old_claim_with_recent_activity_is_running_not_stuck` | PASS |
| sweep-release dual events → one session | `test_sweep_release_pair_produces_one_released_session` | PASS |
| Filters: active-only, all, failed-or-rejected, released | 6 filter tests (inclusion + exclusion) | PASS |
| Empty/missing log → [] | `test_empty_activity_log_returns_empty_list`, `test_missing_activity_log_returns_empty_list` | PASS |
| Malformed/incomplete entries skipped | `test_malformed_json_line_skipped_gracefully`, `test_incomplete_entry_missing_fields_skipped_gracefully`, `test_invalid_timestamp_value_skipped_gracefully` | PASS |
| Re-claim → 2 distinct sessions | `test_reclaim_after_release_produces_two_distinct_sessions` | PASS |
| Multi-task interleaved | `test_interleaved_events_attributed_to_correct_task` | PASS |
| Tests import from owlbear_kanban | Confirmed: `from owlbear_kanban.engine import KanbanEngine` | PASS |
| Fixtures use inline JSONL (not engine ops) | Confirmed: `tmp_path` + `_write_log()` helper | PASS |

### Test Results

- pytest: 461 passed, 6 failed (all failures in serve/mcp-knowledge — unrelated to #923, 0 failures in kanban scope)
- ruff: clean

### Architect Quality: 4/5

Thorough refinement: path fix, 5 challenger items incorporated, sweep dual-event and stuck anti-test added, engine method import specified, block→completed-fail mapped. One minor gap: "malformed entries skipped gracefully" didn't explicitly cover valid JSON with unparseable field values — caught by reviewer in Pass 1, resolved by builder. Overall strong AC.

### Deduction Breakdown

- Full-suite failures in task scope: 0 → no deduction
- Lint violations: 0 → no deduction
- AC lines without evidence: 0 → no deduction
- Missing reviewer evidence: present, detailed, two-pass → no deduction
- AC quality ≤ 3: no (score 4) → no deduction

### Confidence: .98

### Action: archive
