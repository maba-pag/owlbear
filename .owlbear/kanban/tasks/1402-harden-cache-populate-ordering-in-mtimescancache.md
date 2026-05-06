---
id: 1402
title: Harden cache populate ordering in MtimeScanCache
status: in-progress
priority: nice-to-have
created: 2026-05-06T03:40:51.447745+00:00
updated: 2026-05-06T05:12:04.360363+00:00
tags:
- cockpit
- cache
parent: 1346
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

In `serve/cockpit/src/owlbear_cockpit/routes/read.py:92-93`, `cache.has_changed_at(mtime)` commits the new signature as a side effect before `view.list_tasks()` populates `cache.tasks` at line 95. If `view.list_tasks()` raises (e.g., engine CorruptionError on duplicate IDs), the signature is committed but the cache holds stale data. The next request with the same directory state sees no change (signature already committed) and serves stale tasks until the next real file modification.

Note: on first-ever populate (no prior cached tasks), the `not cache.has_cached_tasks` guard retries regardless. The stale-response window only opens after a prior successful population followed by a failed refresh.

Identified during architect re-review of #1346 as follow-up recommendation #1.

## Acceptance Criteria

1. `MtimeScanCache` signature state is not updated until `cache.tasks` is successfully populated. If `view.list_tasks()` raises after a directory-signature change is detected, the signature must remain at its previous value so the next request retries the populate. (td:2)
2. A test proves the warm-cache failure-recovery path: (a) prime cache with a successful populate, (b) simulate a directory-signature change, (c) make `view.list_tasks()` raise on the refresh attempt, (d) verify the signature was NOT committed — a subsequent request with the same directory state must re-detect the change and retry population successfully. (td:2)
3. Existing cockpit test suites pass without modification (154+ tests across `test_cockpit_cache_sse_1346.py`, `test_cockpit_read_api.py`, `test_cockpit_events_*`). (td:0)

## Scope

- **In scope:** `cache.py` (possible API change to separate check from commit), `routes/read.py` (reorder or wrap the signature commit).
- **Out of scope:** SSE events, archive watching, mutation-route invalidation (all handled by #1346).

## Key Files

- `serve/cockpit/src/owlbear_cockpit/cache.py`
- `serve/cockpit/src/owlbear_cockpit/routes/read.py`

## Architecture Review

### Verdict: APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 — signature not committed until populate succeeds | Verifiable, clear rollback semantics | Refined: added warm-cache precondition context |
| AC2 — failure-recovery proof test | Originally underspecified state sequence | Refined: explicit 4-step warm-cache→fail→retry sequence |
| AC3 — existing suites green | Regression gate, no ambiguity | No change (td:0) |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: fix signature commit ordering on populate failure |
| Interface clarity | PASS | Two approaches possible: (a) split has_changed_at into check+commit, (b) try/except with rollback in route. Both have clear API semantics |
| Dependency correctness | PASS | No deps. #1401 is independent (test-only, different concern). Parent #1346 code already landed |
| Module layering | PASS | cache.py ← routes/read.py, no upward imports |
| TDD compliance | PASS | Test-writer processes via normal pipeline |
| KISS/YAGNI | PASS | Minimal fix for a confirmed bug. No new abstractions |
| Premise challenge | PASS | Bug is real, confirmed by code inspection of has_changed_at committing signature at line 75 before view.list_tasks() at line 93 |
| Pattern consistency | PASS | Follows existing cache pattern in cache.py |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit cache domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| view.list_tasks() after signature commit | Engine CorruptionError (duplicate IDs, parse errors) | CorruptionError | Currently NO — signature committed, stale data served | Stale task list until next real file modification |
| Post-fix: view.list_tasks() failure | Same exceptions | Same | YES — signature rolled back, next request retries | Transient error, self-healing on retry |

### Challenger Results

Challenger recommended reconsider (confidence 0.68). Two valid concerns addressed:
1. AC2 warm-cache precondition: refined to specify the 4-step state sequence
2. Adjacent task coupling (#1401): confirmed independent — different concern, no overlap

Scope contradiction (test file not in scope section) dismissed: test files are always implied for implementation tasks.

### Test-writer Guidance

Test-writer: AC1 and AC2 cover the same behavior from implementation and proof angles. A single test exercising the 4-step sequence in AC2 satisfies both. AC3 is a regression gate (td:0).
[[2026-05-06]]
Architecture review complete. AC refined: AC2 now specifies the warm-cache precondition and 4-step failure-recovery test sequence (prime → change → fail → retry). Challenger concerns addressed. All 10 criteria PASS. Test depths: AC1 td:2, AC2 td:2, AC3 td:0.
[[2026-05-06]]
## Test-Writer Notes

**Test file:** `tests/test_cockpit_cache_populate_1402.py`

### Test Classes

| Class | Tests | Focus |
|-------|-------|-------|
| `TestFromAC_CachePopulateOrdering` | 2 | AC1: signature not committed on failed populate |
| `TestFromAC_WarmCacheFailureRecovery` | 2 | AC2: 4-step warm-cache failure-recovery sequence |

### Tests by Category

| Category | Tests |
|----------|-------|
| Error path | `test_signature_not_committed_when_list_tasks_raises`, `test_signature_rolled_back_after_warm_cache_failure` |
| Boundary | `test_stale_cache_not_served_after_failed_populate` (repeated same-sig request → must not serve stale) |
| Integration (4-step) | `test_4step_failure_recovery_warm_cache` (prime → sig-change → fail → retry-with-fresh-data; verifies call_count and task count) |

**Total: 4 tests, all FAIL (verified via quality-runner)**

### AC Coverage

| AC | Tests | Notes |
|----|-------|-------|
| AC1 (td:2) | `test_signature_not_committed_when_list_tasks_raises`, `test_stale_cache_not_served_after_failed_populate`, `test_signature_rolled_back_after_warm_cache_failure` | Checks `cache.last_mtime` stays at prior value; checks stale 200 not returned after failure |
| AC2 (td:2) | `test_4step_failure_recovery_warm_cache` | Full 4-step sequence: asserts 2 fresh tasks returned and `list_tasks.call_count == 3` |
| AC3 (td:0) | — | Skipped, td:0 |

### Key Fix Surface

Builder note: `cache.has_changed_at(mtime)` in `routes/read.py` commits `_last_signature` before `view.list_tasks()` is called. Fix can go in `cache.py` (split check/commit) or `routes/read.py` (try/except rollback). Both approaches will make these tests pass.
[[2026-05-06]]
## Builder Notes
- Implementation: deferred directory-signature commit until successful populate by separating detection from commit.
- Files changed: `serve/cockpit/src/owlbear_cockpit/cache.py`, `serve/cockpit/src/owlbear_cockpit/routes/read.py`.
- Fixes applied:
  - Added `changed_since(signature)` to check signature drift without side effects.
  - Added `commit_signature(signature)` for explicit commit after successful refresh.
  - Updated `/api/tasks` flow to call `view.list_tasks()` and cache tasks first, then commit signature.
- Behavioral result: if `view.list_tasks()` raises during refresh, signature remains at prior value, so the next request with the same directory state retries population instead of serving stale cached tasks.
- RED verification (pre-fix): `tests/test_cockpit_cache_populate_1402.py` had 4 failing `TestFromAC_*` tests.
- GREEN verification (post-fix): task test file passed 4/4.
- AC3 regression suites: 158 passed, 0 failed across:
  - `tests/test_cockpit_cache_populate_1402.py`
  - `tests/test_cockpit_cache_sse_1346.py`
  - `tests/test_cockpit_read_api.py`
  - `tests/test_cockpit_events_1234.py`
  - `tests/test_cockpit_events_1262.py`
- Coverage (touched modules):
  - `owlbear_cockpit.cache`: 91%
  - `owlbear_cockpit.routes.read`: 98%
- Ruff: clean.
- Commit: `bc30d605 feat: harden cache signature commit ordering (#1402, builder)`

### Reflection
- Keeping `has_changed_at` behavior intact while introducing explicit check/commit methods minimized downstream risk.
- Route-level commit deferral was the smallest change that satisfied both AC1 rollback semantics and AC2 warm-cache retry proof.
- Running the AC3 suites with coverage provided a stronger guard against regressions in existing cockpit read/event paths.
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner scoped run: 158 passed, 0 failed, 0 skipped across tests/test_cockpit_cache_populate_1402.py, tests/test_cockpit_cache_sse_1346.py, tests/test_cockpit_read_api.py, tests/test_cockpit_events_1234.py, and tests/test_cockpit_events_1262.py.

### Lint Results
- Ruff clean on serve/cockpit/src/owlbear_cockpit/cache.py, serve/cockpit/src/owlbear_cockpit/routes/read.py, and tests/test_cockpit_cache_populate_1402.py.

### Coverage
- owlbear_cockpit.cache: 91%
- owlbear_cockpit.routes.read: 98%

### Scope and Integrity
- Builder commit `bc30d605` verified in `.git/logs/HEAD:2111`; changed-file scope reconstructed from builder notes: serve/cockpit/src/owlbear_cockpit/cache.py and serve/cockpit/src/owlbear_cockpit/routes/read.py.
- No prior `## Review Evidence` section exists in .owlbear/kanban/tasks/1402-harden-cache-populate-ordering-in-mtimescancache.md, so this is the first review cycle.
- TestFromAC assertions in the current task test body remain stringent; no weakened or removed assertions were found. Direct diff-scoped immutability proof was not available from the current tool surface, so a small confidence deduction applies.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | Implementation defers signature commit until after task population at serve/cockpit/src/owlbear_cockpit/routes/read.py:92-95, using cache helpers at serve/cockpit/src/owlbear_cockpit/cache.py:79-83. The TestFromAC suite proves failure-side rollback at tests/test_cockpit_cache_populate_1402.py:168, tests/test_cockpit_cache_populate_1402.py:174, and tests/test_cockpit_cache_populate_1402.py:411, but it never asserts that a successful populate commits the new signature. Removing cache.commit_signature(mtime) at serve/cockpit/src/owlbear_cockpit/routes/read.py:95 would leave the current TestFromAC suite green. | FAIL |
| AC2 | test_4step_failure_recovery_warm_cache exercises the warm-cache prime, failed refresh, and retry sequence at tests/test_cockpit_cache_populate_1402.py:327-358, and it asserts fresh two-task data plus mock_view.list_tasks.call_count == 3 at tests/test_cockpit_cache_populate_1402.py:351 and tests/test_cockpit_cache_populate_1402.py:358. This would fail if the same-signature retry served stale data or skipped the retry. | PASS |
| AC3 | quality-runner scoped run passed all 158 tests in the task suite and the adjacent cockpit regression suites named in the AC. | PASS |

### Findings
- Implementation appears correct. The route now checks cache.changed_since(mtime) before refresh and commits the signature only after cache.tasks is replaced at serve/cockpit/src/owlbear_cockpit/routes/read.py:92-95.
- New helper usage is tightly scoped. Grep found changed_since and commit_signature only in serve/cockpit/src/owlbear_cockpit/cache.py:74-83 and serve/cockpit/src/owlbear_cockpit/routes/read.py:92-95; no broader caller impact was found.
- No security or data-safety issues were found in the changed code path.
- Blocking issue is proof quality only: AC1 says the signature state is not updated until populate succeeds, but the TestFromAC suite proves only the rollback half of that contract.

### Deductions
- 0.10: AC1 missing success-side TestFromAC proof for serve/cockpit/src/owlbear_cockpit/routes/read.py:95.
- 0.02: No diff-scoped TestFromAC immutability proof; assessed from final file body plus commit-log reconstruction only.
- Confidence: 0.86.

### Verdict
- FAIL to todo.
- Reason: implementation and regression evidence are clean, but AC1 is only partially proven by the TestFromAC suite.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | test-writer | Strengthen the AC1 TestFromAC proof so a successful populate explicitly proves the new signature is committed after success, not merely rolled back on failure. | tests/test_cockpit_cache_populate_1402.py | Missing proof for serve/cockpit/src/owlbear_cockpit/routes/read.py:95; current AC1 assertions are only at tests/test_cockpit_cache_populate_1402.py:168, tests/test_cockpit_cache_populate_1402.py:174, and tests/test_cockpit_cache_populate_1402.py:411. |
[[2026-05-06]]
## Test-Writer Notes
- Retry: added 1 test for reviewer gap (AC1 success-side proof).
- Test file: tests/test_cockpit_cache_populate_1402.py
- New test: `TestFromAC_CachePopulateOrdering.test_signature_committed_after_successful_populate`
  - Happy path: fresh cache → successful GET /api/tasks → asserts `cache.last_mtime == sig_new`
  - Regression guard: proves `commit_signature(mtime)` is called on the success path; removing it leaves `last_mtime == 0` and the assertion fails.
- All 5 tests PASS against current implementation (AC1 success-side was already correctly implemented).
- Builder skip: test-only retry, all tests green — advancing directly to review.
- Commit: `4d4b5288 test: add retry tests for cache signature success-side proof (#1402, test-writer)`
- ruff: clean