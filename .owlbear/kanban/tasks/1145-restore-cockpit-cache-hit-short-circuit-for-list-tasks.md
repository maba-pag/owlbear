---
id: 1145
title: Restore cockpit cache-hit short-circuit for list_tasks
status: review
priority: nice-to-have
created: 2026-04-27T18:29:56.708569+00:00
updated: 2026-04-27T20:33:31.952881+00:00
tags:
- scope:cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: rare-mist
claimed_at: 2026-04-27T20:33:31.952881+00:00
archival_reason:
archival_refs: []
---
## Context
930 test `test_engine_list_tasks_not_called_on_cache_hit` fails — the cache short-circuit that avoided calling engine.list_tasks() on repeated requests was dropped during the Brief B route rewrite (#1082).

## Acceptance Criteria
- [ ] MtimeScanCache.has_changed() gates engine.list_tasks() calls — cache hit returns cached tasks without engine call
- [ ] test_cockpit_read_api_930.py cache-hit test passes

## Files
- serve/cockpit/src/owlbear_cockpit/routes/read.py
- serve/cockpit/src/owlbear_cockpit/cache.py
- tests/test_cockpit_read_api_930.py

## Research Notes
See .owlbear/research/1144-cockpit-durable-reconciliation.md — adjacent scope from #1144.

[[2026-04-27]]
## Research
- Research doc: .owlbear/research/1145-cockpit-cache-hit-short-circuit.md
- Sources: 6 studied, 4 high-relevance (all internal — live code + git history)
- Recommendation: Option A — restore `cache.has_changed()` gate in route, cache full unfiltered task list, filter in Python (confidence: 0.90)
- Follow-up tasks created: none (this task itself is the implementation vehicle)
- Decision requests: none (T1 bug fix — restoring dropped functionality)

## Challenge Results
- Challenger: FALLBACK — trivial T1 bug fix restoring prior behavior, challenger skipped
- Confidence in original: 0.90
- Key findings: (1) `_cache` param injected but unused in route body; (2) old pattern from commit b582a3e3 shows exact cache-gate pattern to restore; (3) monkeypatch chain confirmed compatible — `engine.list_tasks()` is terminal call in CockpitView→AgentView→engine delegation
- Implementation: ~10 lines changed in routes/read.py — add `cache.has_changed()` check, cache `view.list_tasks()` result, apply 4 filters in Python
[[2026-04-27]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: restore cache-hit short-circuit for GET /api/tasks |
| Interface clarity | PASS | Uses existing MtimeScanCache.has_changed() + .tasks API; returns ListTasksResponse |
| Dependency correctness | PASS | No dependencies needed — standalone bug fix |
| Module layering | PASS | Route → cache (both cockpit pkg), no upward imports |
| TDD compliance | PASS | Failing test already exists: test_cockpit_read_api_930.py L451-480 |
| KISS/YAGNI | PASS | ~10 lines restoring pre-#1082 pattern, Option A from research |
| Premise challenge | PASS | Restoring broken functionality, not new capability |
| Pattern consistency | PASS | MtimeScanCache was designed for this exact use case |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit domain only |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| MtimeScanCache.has_changed() gates engine.list_tasks() calls — cache hit returns cached tasks without engine call | Specific, testable — names gating method, condition, and expected behavior | None |
| test_cockpit_read_api_930.py cache-hit test passes | Specific — names exact test file and test case (L451-480) | None |

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Concerns: (1) max-mtime doesn't detect file deletions, (2) archive-dir changes unmonitored, (3) validation bypass on cache-hit path, (4) cross-suite mtime contract conflict
- Architect response: Override — all concerns are pre-existing MtimeScanCache design limitations or adjacent-scope issues (#1144). This task restores dropped functionality; expanding scope violates KISS/YAGNI. Validation bypass matches pre-#1082 behavior. Confidence: 0.90

### Architecture Notes
- `_cache: _Cache` param already injected in route but unused — builder restores `cache.has_changed()` gate
- Cache stores unfiltered `view.list_tasks()` result; 4 filters (status/priority/tag/blocked) applied in Python on cache hit
- Monkeypatch chain verified: engine.list_tasks patched on instance → CockpitView.list_tasks() → AgentView.list_tasks() → engine.list_tasks() — same instance, intercept works correctly
- Return `ListTasksResponse(tasks=filtered, guidance=[], missing_ids=None)` on cache hit to match #1082 envelope contract

### Verdict: APPROVE
### Action Taken: Advanced to todo — AC precise, architecture sound, existing test covers expected behavior
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_read_api_1145.py
- Classes: TestFromAC_CacheHitShortCircuit
- Tests per category: happy 2, edge 5, error 0, boundary 2
- Total: 9 tests, all FAIL
- ruff: clean

### AC Coverage
| AC Line | Tests |
|---------|-------|
| MtimeScanCache.has_changed() gates engine.list_tasks() — cache hit returns cached tasks without engine call | test_cache_hit_skips_engine_call, test_has_changed_called_updates_last_mtime, test_status/priority/tag/blocked_filter_on_cache_hit_skips_engine, test_status_filter_returns_correct_tasks_on_cache_hit, test_multiple_consecutive_requests_all_skip_engine, test_first_request_populates_cache_tasks |
| test_cockpit_read_api_930.py cache-hit test passes | Covered by existing TestBuilderDiscovered::test_engine_list_tasks_not_called_on_cache_hit in 930 suite (already failing) |

### Fixture design
- `cache` fixture: known MtimeScanCache instance for tasks dir
- `cache_client` fixture: overrides both `get_engine` and `get_cache` so tests inspect the exact cache instance the route handler uses

### Failure evidence
All 9 tests fail due to `_cache` param being injected but unused in the current route — engine.list_tasks() called on every request, cache.last_mtime never updated, cache.tasks never populated.
[[2026-04-27]]
## Builder Notes
- Implementation: restored GET /api/tasks cache-hit short-circuit in serve/cockpit/src/owlbear_cockpit/routes/read.py using `cache.has_changed()` + cached full task list reuse.
- Contract preservation: kept 1144 route contract by sourcing response `mtime` from `cache.scan()` while still updating cache state through `has_changed()`.
- Filtering behavior: applied status/priority/tag/blocked filters in Python on cached task summaries for cache-hit responses, with no engine.list_tasks() call.
- Files changed: serve/cockpit/src/owlbear_cockpit/routes/read.py
- Tests: 93 passed, 0 failed (tests/test_cockpit_read_api.py, tests/test_cockpit_read_api_930.py, tests/test_cockpit_read_api_1145.py, tests/test_cockpit_routes_1144.py)
- Coverage: 98% on owlbear_cockpit.routes.read (quality-runner scoped coverage evidence)
- Ruff: clean
- Commit: 74380a30 (feat: restore cockpit cache-hit short-circuit (#1145, builder))
[[2026-04-27]]
## Review Evidence
### Test Results
- pytest (scoped): 43 passed, 0 failed across `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_read_api_1145.py`, and `tests/test_cockpit_routes_1144.py`
- pytest (AC2 file): 26 passed, 0 failed in `tests/test_cockpit_read_api_930.py`

### Lint
- ruff: clean on `serve/cockpit/src/owlbear_cockpit/routes/read.py` and the scoped test files

### Coverage
- Quality-runner could not report `owlbear_cockpit` module/package coverage because workspace coverage config omits cockpit from tracked `source_pkgs`; scoped reports only emitted kanban modules. No task-specific coverage percentage was available for this review.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| MtimeScanCache.has_changed() gates engine.list_tasks() calls — cache hit returns cached tasks without engine call | `tests/test_cockpit_read_api_1145.py:132`, `tests/test_cockpit_read_api_1145.py:158`, `tests/test_cockpit_read_api_1145.py:307`, `tests/test_cockpit_read_api_1145.py:335`, `tests/test_cockpit_read_api_930.py:451` | No. The implementation still violates the contract for unchanged empty-board requests because `list_tasks()` treats a cached empty list as uncached at `serve/cockpit/src/owlbear_cockpit/routes/read.py:80`. The new 1145 suite only seeds non-empty boards at `tests/test_cockpit_read_api_1145.py:76-78`, and the existing empty-board tests at `tests/test_cockpit_read_api_930.py:242-257` stop after the first request. | LAX |
| test_cockpit_read_api_930.py cache-hit test passes | `tests/test_cockpit_read_api_930.py:451` | Yes. Independent quality-runner run of `tests/test_cockpit_read_api_930.py` passed 26/26. | COVERED |

#### Security Review
- No issues found in scope. The route only scans cache state and performs in-memory filtering.

#### Test Integrity
| Original Test | Change Made | Assessment |
| --- | --- | --- |
| `TestFromAC_CacheHitShortCircuit` in `tests/test_cockpit_read_api_1145.py` and the existing regression test in `tests/test_cockpit_read_api_930.py` | No weakening observed in the workspace snapshot; zero-call assertions remain intact | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | ADEQUATE | Zero-call assertions at `tests/test_cockpit_read_api_1145.py:132` and `tests/test_cockpit_read_api_930.py:451` are strong; `has_changed()` proof at `tests/test_cockpit_read_api_1145.py:158` is indirect via `last_mtime` mutation |
| Negative/error-path coverage | WEAK | No test performs a second unchanged request on an empty board, even though the route has a distinct empty-cache branch at `serve/cockpit/src/owlbear_cockpit/routes/read.py:80` |
| Manual mutation reasoning | WEAK | Leaving `or not cache.tasks` intact at `serve/cockpit/src/owlbear_cockpit/routes/read.py:80` still passes the current suites because the new task suite uses only non-empty boards at `tests/test_cockpit_read_api_1145.py:76-78` |
| Test independence | STRONG | tmp_path-backed board fixtures isolate state |
| Descriptive names | STRONG | Test names state the contract clearly |

#### Data Safety
- No issues found in scope.

#### Implementation-Aware Gaps
- Implementation defect: `if cache.has_changed() or not cache.tasks:` at `serve/cockpit/src/owlbear_cockpit/routes/read.py:80` re-calls `view.list_tasks()` on every unchanged request when the cached result is legitimately `[]`. That is still an engine call on a cache hit, which violates AC1.
- Proof gap: current suites do not exercise that branch. Empty-board coverage in `tests/test_cockpit_read_api_930.py:242-257` validates only first-request 200/empty/mtime behavior, not second-request cache-hit suppression.

#### Builder Process Quality
| Metric | Value |
| --- | --- |
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The cache-hit branch hard-codes `guidance=[]` and `missing_ids=None` at `serve/cockpit/src/owlbear_cockpit/routes/read.py:106-107` while the miss branch forwards envelope metadata at `serve/cockpit/src/owlbear_cockpit/routes/read.py:92-93`, but for this route's current filter surface `view.list_tasks()` returns `guidance=[]` and `missing_ids=None` anyway. I am not counting that as a task defect.
- Module-level cockpit coverage could not be measured via quality-runner because of workspace coverage config, so line-level code reading carried the review burden.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| MtimeScanCache.has_changed() gates engine.list_tasks() calls — cache hit returns cached tasks without engine call | `serve/cockpit/src/owlbear_cockpit/routes/read.py:80` still treats cached `[]` as uncached; `tests/test_cockpit_read_api_1145.py:76-78` only covers non-empty boards; `tests/test_cockpit_read_api_930.py:242-257` covers only first-request empty-board behavior | `tests/test_cockpit_read_api_1145.py:132`, `tests/test_cockpit_read_api_1145.py:158`, `tests/test_cockpit_read_api_1145.py:307`, `tests/test_cockpit_read_api_1145.py:335`, `tests/test_cockpit_read_api_930.py:451` | FAIL |
| test_cockpit_read_api_930.py cache-hit test passes | Independent quality-runner run: `tests/test_cockpit_read_api_930.py` -> 26 passed, 0 failed; named test at `tests/test_cockpit_read_api_930.py:451` remains green | `tests/test_cockpit_read_api_930.py:451` | PASS |

### Deductions
- -0.18 implementation miss: unchanged empty-board requests still bypass the cache-hit path
- -0.08 test quality gap: no proof for empty-board cache-hit behavior
- -0.02 module-level coverage evidence unavailable for cockpit package in quality-runner
- Confidence: 0.72

### Verdict
- FAIL -> in-progress
- Action: distinguish "cache never populated" from "cached empty list" in the route, and add a second-request empty-board test that would fail if `engine.list_tasks()` is called on an unchanged empty cache.
[[2026-04-27]]
## Builder Notes
- Implementation: updated [serve/cockpit/src/owlbear_cockpit/cache.py](serve/cockpit/src/owlbear_cockpit/cache.py) to track cache-population state explicitly, and updated [serve/cockpit/src/owlbear_cockpit/routes/read.py](serve/cockpit/src/owlbear_cockpit/routes/read.py#L78) to gate refresh on `cache.has_changed()` or uncached-state only.
- Fix applied: replaced `or not cache.tasks` with `or not cache.has_cached_tasks` so unchanged empty-board responses are treated as cache hits (no `engine.list_tasks()` call).
- Files changed: [serve/cockpit/src/owlbear_cockpit/cache.py](serve/cockpit/src/owlbear_cockpit/cache.py), [serve/cockpit/src/owlbear_cockpit/routes/read.py](serve/cockpit/src/owlbear_cockpit/routes/read.py)
- Tests: 93 passed, 0 failed (`tests/test_cockpit_read_api.py`, `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_read_api_1145.py`, `tests/test_cockpit_routes_1144.py`)
- Coverage: 100% on `owlbear_cockpit.cache`, 98% on `owlbear_cockpit.routes.read`
- Ruff: clean on changed source + scoped suites
- Commit: 3550bc79 (`fix: distinguish empty cached task list from uncached state (#1145, builder)`)

- Reflection:
  - Problem faced: existing AC tests were green despite a real uncovered branch (unchanged empty-board path).
  - Workaround applied: used reviewer’s implementation-aware evidence to apply a minimal branch-correctness fix without broadening scope.
  - Pattern discovered: cache validity and cache payload emptiness need separate state signals.
  - Quality gap: task tests still do not directly assert second-request empty-board cache-hit suppression.
[[2026-04-27]]
## Review Evidence
### Test Results
- pytest (quality-runner scoped): 93 passed, 0 failed, 0 skipped, 0 errors across `tests/test_cockpit_read_api.py`, `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_read_api_1145.py`, and `tests/test_cockpit_routes_1144.py`

### Lint
- ruff: clean on `serve/cockpit/src/owlbear_cockpit/cache.py`, `serve/cockpit/src/owlbear_cockpit/routes/read.py`, and the scoped cockpit read-route suites

### Coverage
- `owlbear_cockpit.cache`: 100%
- `owlbear_cockpit.routes.read`: 98% (1 missed line reported by quality-runner)
- cockpit package overall (informational): 75%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| `MtimeScanCache.has_changed()` gates `engine.list_tasks()` calls — cache hit returns cached tasks without engine call | `tests/test_cockpit_read_api_1145.py:132`, `:158`, `:173`, `:199`, `:225`, `:251`, `:307`, `:335`; plus `tests/test_cockpit_read_api_930.py:451` | Partially. These prove populated-board cache hits, but no task-owned test performs a second unchanged request on the empty-board fixture at `tests/test_cockpit_read_api_930.py:75`. The empty-board tests at `tests/test_cockpit_read_api_930.py:242`, `:247`, and `:257` each stop after a single request, and the 1145 suite seeds a non-empty board at `tests/test_cockpit_read_api_1145.py:72`. A mutation that breaks only cached-empty responses would survive. | LAX |
| `test_cockpit_read_api_930.py` cache-hit test passes | `tests/test_cockpit_read_api_930.py:451` | Yes. The scoped quality-runner run included `tests/test_cockpit_read_api_930.py` and returned 93 passed, 0 failed, so the named regression test is green in the current revision. | COVERED |

#### Security Review
- No issues found. The scoped changes only update in-memory cache state and filter already-materialized task objects; there is no new input boundary, path handling, or code-execution surface in `serve/cockpit/src/owlbear_cockpit/cache.py` and `serve/cockpit/src/owlbear_cockpit/routes/read.py`.

#### Test Integrity
| Original Test | Change Made | Assessment |
| --- | --- | --- |
| `TestFromAC_CacheHitShortCircuit` in `tests/test_cockpit_read_api_1145.py` and the existing regression test at `tests/test_cockpit_read_api_930.py:451` | No weakening observed in the current workspace snapshot; exact zero-call assertions remain intact | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | ADEQUATE | Exact zero-call assertions at `tests/test_cockpit_read_api_1145.py:132` and `tests/test_cockpit_read_api_930.py:451` are strong, but `tests/test_cockpit_read_api_1145.py:166` only gives an indirect `last_mtime > 0` signal |
| Negative/error-path coverage | WEAK | The empty-board suite at `tests/test_cockpit_read_api_930.py:242`, `:247`, and `:257` makes only one request per test; none assert second-request cache-hit suppression when the cached payload is `[]` |
| Manual mutation reasoning | WEAK | The 1145 suite seeds a non-empty board at `tests/test_cockpit_read_api_1145.py:72` and asserts `len(cache.tasks) > 0` at `tests/test_cockpit_read_api_1145.py:343`; a regression limited to cached-empty lists would still pass |
| Test independence | STRONG | tmp-path board fixtures isolate state between tests |
| Descriptive names | STRONG | Test names state the cache-hit contract clearly |

#### Data Safety
- No issues found in scope.

#### Implementation-Aware Gaps
- No implementation miss found in the current revision. `MtimeScanCache.tasks` now marks cache population even for `[]` at `serve/cockpit/src/owlbear_cockpit/cache.py:62-64`, and the route reload gate uses `cache.has_changed() or not cache.has_cached_tasks` at `serve/cockpit/src/owlbear_cockpit/routes/read.py:80`, which separates "uncached" from "cached empty list".
- The remaining failure is executable proof: no scoped test covers the second unchanged request on an empty board, so the exact branch that failed the first review is still unproven.

#### Builder Process Quality
| Metric | Value |
| --- | --- |
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The cache-hit branch still hard-resets `guidance=[]` and `missing_ids=None` at `serve/cockpit/src/owlbear_cockpit/routes/read.py:106-107`; no scoped test asserts those fields on cache hits. I am not counting that as a task defect because the current route contract suite stays green.
- `get_cache()` reuses one `MtimeScanCache` per engine via `WeakKeyDictionary` at `serve/cockpit/src/owlbear_cockpit/deps.py:34-43`, so the missing empty-board regression test can be written against the existing `empty_client` fixture with two requests and a second-call `engine.list_tasks` monkeypatch.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| `MtimeScanCache.has_changed()` gates `engine.list_tasks()` calls — cache hit returns cached tasks without engine call | `serve/cockpit/src/owlbear_cockpit/routes/read.py:80` now gates reload on `cache.has_changed()` or `not cache.has_cached_tasks`; `serve/cockpit/src/owlbear_cockpit/cache.py:24`, `:62-69` distinguish uncached state from cached-empty state, so an unchanged empty-board second request stays on the cache-hit branch | `tests/test_cockpit_read_api_1145.py:132`; `tests/test_cockpit_read_api_930.py:451` | PASS |
| `tests/test_cockpit_read_api_930.py` cache-hit test passes | Scoped quality-runner run returned 93 passed, 0 failed with `tests/test_cockpit_read_api_930.py` included; the named regression test at `tests/test_cockpit_read_api_930.py:451` therefore passed | `tests/test_cockpit_read_api_930.py:451` | PASS |

### Deductions
- -0.08 task-owned proof gap: no executable second-request empty-board cache-hit test
- -0.04 weak mutation resistance: current suites cover non-empty cache hits or single-request empty-board behavior, not cached-empty hits
- Confidence: 0.88

### Verdict
- FAIL -> todo
- Action: add a task-owned regression test that uses the empty-board fixture with two consecutive `GET /api/tasks` calls against the same engine/cache instance and asserts `engine.list_tasks()` is not called on the second request when the cached result is `[]`.

### Reflection
- Problem faced: the current source diff appears to fix the prior bug, but the task-owned tests still miss the exact empty-board branch that caused the first review failure.
- Workaround applied: separated implementation correctness from proof quality by combining scoped quality-runner evidence with direct source-path analysis.
- Pattern discovered: cache validity and cache payload emptiness require separate state signals, and empty-list caches need dedicated regression coverage.
- Quality gap: the existing TestFromAC suite exercises only non-empty boards for cache-hit assertions.
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_read_api_1145.py
- Classes: TestFromAC_CacheHitShortCircuit (extended)
- Tests per category: +1 boundary (empty-board second-request cache-hit regression guard)
- Total new: 1 test — PASSES (regression guard for already-correct implementation)
- ruff: clean

### Retry summary
Reviewer (second review) confirmed implementation is correct but flagged missing task-owned proof for the empty-board second-request cache-hit branch. Added:
- `test_empty_board_second_request_skips_engine_call` — two consecutive `GET /api/tasks` calls against an empty board; asserts `engine.list_tasks()` is NOT called on the second request when cached result is `[]`. Uses new `empty_cache_client` fixture (overrides both `get_engine` and `get_cache`) so the test inspects the exact cache instance the route handler uses.

New supporting fixtures: `empty_board_dir`, `empty_engine`, `empty_cache`, `empty_cache_client`.

### Test result
All 10 tests PASS. New test passes because the builder's second fix (`has_cached_tasks` property replacing `or not cache.tasks`) was already confirmed correct by the reviewer. This test is a regression guard — it would fail if anyone reverts to the `or not cache.tasks` pattern.

### AC Coverage
| AC Line | Tests |
|---------|-------|
| MtimeScanCache.has_changed() gates engine.list_tasks() — cache hit returns cached tasks without engine call | test_cache_hit_skips_engine_call, test_has_changed_called_updates_last_mtime, status/priority/tag/blocked filter tests, test_multiple_consecutive_requests_all_skip_engine, **test_empty_board_second_request_skips_engine_call** |
| test_cockpit_read_api_930.py cache-hit test passes | Covered by existing test in 930 suite |

### Commit
5163b53f (test: add empty-board cache-hit regression guard (#1145, test-writer))
[[2026-04-27]]
## Builder Notes
- Implementation: no additional code changes required in this builder pass; task 1145 implementation was already present in committed source.
- Verified files: serve/cockpit/src/owlbear_cockpit/cache.py, serve/cockpit/src/owlbear_cockpit/routes/read.py, tests/test_cockpit_read_api_1145.py.
- Quality-runner (scoped): 94 passed, 0 failed, 0 skipped across `tests/test_cockpit_read_api_1145.py`, `tests/test_cockpit_read_api_930.py`, `tests/test_cockpit_read_api.py`, `tests/test_cockpit_routes_1144.py`.
- Coverage: 97% on `owlbear_cockpit.cache`, 98% on `owlbear_cockpit.routes.read`.
- ruff: clean on scoped source/tests.
- Git evidence: recent commits already contain task 1145 implementation and proof (`3550bc79`, `5163b53f`), and current working tree has no pending edits in 1145 scope.

- Reflection:
  - Problem faced: task re-entered builder while already effectively green due to prior builder + test-writer commits.
  - Workaround applied: treated this pass as verification-only and validated AC via quality-runner + git history rather than introducing redundant edits.
  - Pattern discovered: retry loops can leave tasks in in-progress even when implementation is already complete; builder should validate state before touching code.
  - Quality gap: none in current AC scope after scoped quality-runner verification.