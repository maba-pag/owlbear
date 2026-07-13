---
id: 944
title: Implement _id_to_filename cache for show_task() and _find_task_path()
status: archived
priority: medium
created: 2026-04-17T22:57:35.591784+00:00
updated: 2026-04-17T23:56:29.642131+00:00
tags:
- engine
- cockpit
- phase-0
- type:build
parent: 920
depends_on:
- 943
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Implement the _id_to_filename cache extension so show_task() and _find_task_path() benefit from the mtime cache.

## Acceptance Criteria

- [ ] `__init__` adds `_id_to_filename: dict[int, str] = {}`
- [ ] `list_tasks()` rebuilds `_id_to_filename` from `_task_cache` after scandir loop
- [ ] `refresh_config()` clears `_id_to_filename`
- [ ] `show_task()` checks `_id_to_filename` → `_task_cache` → stat validate → fallback to glob
- [ ] `show_task()` evicts stale entries on stat() FileNotFoundError
- [ ] `_find_task_path()` checks `_id_to_filename` → return path → fallback to glob
- [ ] No archive dispatch in `_find_task_path()` (all callers use tasks_dir)
- [ ] All existing tests pass + new tests from RED phase pass

## Files

- `serve/kanban/src/owlbear_kanban/engine.py`

## Context

See `.owlbear/research/extend-mtime-cache-943.md` for approach details and trade-off analysis.
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/extend-mtime-cache-943.md (validation pass — existing doc from #943 covers approach)
- Sources: 1 studied (engine.py codebase), 1 high-relevance
- Recommendation: Implementation already complete — all 8 AC items verified in codebase (confidence: 0.95)
- Verification: 25/25 tests in test_idtofilename_cache_943.py PASSED (0.15s)
- Follow-up tasks created: none — implementation is done
- Decision requests: none

AC validation summary:

1. `_id_to_filename: dict[int, str] = {}` in `__init__` ✓
2. Rebuilt in `list_tasks()` via sorted dict comprehension from `_task_cache` ✓
3. Cleared in `refresh_config()` ✓
4. `show_task()`: O(1) lookup → stat validate → cache hit/re-read → glob fallback ✓
5. `show_task()`: evicts both caches on stat FileNotFoundError ✓
6. `_find_task_path()`: O(1) when search_dir ==_tasks_dir → glob fallback ✓
7. No archive dispatch in `_find_task_path()` ✓
8. All 25 RED-phase tests green ✓
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One cache extension, one file (engine.py) |
| Interface clarity | PASS | AC specifies exact method-level behavior, data structures, and fallback chains |
| Dependency correctness | PASS | #943 archived (done) — provides mtime cache foundation |
| Module layering | PASS | Single file, no cross-module concerns |
| TDD compliance | PASS | 25 tests in test_idtofilename_cache_943.py, all green |
| KISS/YAGNI | PASS | Minimal O(1) lookup extension of existing _task_cache pattern |
| Premise challenge | PASS | Cache extension justified by research doc extend-mtime-cache-943.md |
| Pattern consistency | PASS | Follows existing _task_cache mtime validation pattern |
| Security surface | PASS | No new system boundaries; TOCTOU low-risk, mitigated by mtime_ns validation |
| Single domain | PASS | Kanban engine only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| show_task() cache hit → stat | File deleted externally | FileNotFoundError | Yes — dual eviction + re-raise (lines 340-345) | One error per ghost, self-healing |
| show_task() glob fallback | No matching file | FileNotFoundError | Yes — raised with message (line 353) | Expected behavior |
| _find_task_path() cache hit | File deleted externally | FileNotFoundError from read_task() in caller | Yes — caller-handled | Correct propagation |

### Challenge Results

- Challenger: reconsider (confidence 0.60)
- Raised 5 concerns: ghost entries after archive (C2), glob not backfilling cache (C1), _find_task_path no stat (C3), test file naming (C4), duplicate IDs (C5)
- Architect response: override → APPROVE
  - C2: self-healing — stat failure evicts ghost, next call uses glob. Archived tasks correctly absent from tasks_dir
  - C1: performance optimization, not correctness bug. AC satisfied ("fallback to glob")
  - C3: stat would be redundant — callers immediately read_task() which raises on missing file
  - C4: naming references feature/research-doc number, not task ID
  - C5: YAGNI — corruption edge case outside normal operation

### Codebase Verification

- All 8 AC items verified in engine.py (lines 148, 196, 267-273, 283-307, 292-293, 831-847)
- Implementation already complete per researcher validation (confidence 0.95)
- 25/25 tests passing in test_idtofilename_cache_943.py

### Verdict: APPROVE

### Action Taken: Advanced to todo. All AC verifiable, architecture sound, implementation verified

[[2026-04-17]]

## Test-Writer Notes

**Test file:** `serve/kanban/tests/test_idtofilename_cache_944.py`
**Class:** `TestFromAC_IdToFilenameCache_944`

| Category | Count | Tests |
|----------|-------|-------|
| Happy path | 8 | init, list_tasks+filter, list_tasks+new-file, archived-no-corrupt, refresh_config, show_task-cold-glob, find_path-returns-path-obj/absolute/exists |
| Edge cases | 7 | id-cache-warm+task-cache-cold (no-glob, calls-read_task, repopulates-cache), eviction-leaves-others, second-call-after-eviction-succeeds, find-path-id-absent-falls-back |
| Error paths | 5 | show_task-unknown-id, non-int-id (show_task + find_task_path), stale-id-raises-fnf, find-path-missing-raises-fnf |
| Boundary | 3 | list_tasks-deleted-task-removed, archive-dir-uses-glob-not-id-cache, tasks-dir-never-accesses-archive |

**Total: 23 tests**
**Ruff: clean**

### ⚠ Pre-implemented exception

All 23 tests **PASS** (0.12s) — the implementation was already complete when this task entered the pipeline (confirmed by researcher at 0.95 confidence; verified against engine.py lines 137, 186, 274-279, 335-354, 915-921). This is NOT a RED-phase violation — the feature exists and the tests serve as a comprehensive regression suite and specification. The builder's GREEN phase will be a verification pass only.

### AC Coverage

| AC | Description | Tests |
|----|-------------|-------|
| AC1 | `__init__` adds `_id_to_filename: dict[int, str] = {}` | test_init_* |
| AC2 | `list_tasks()` rebuilds `_id_to_filename` from `_task_cache` | test_list_tasks_* (4 tests) |
| AC3 | `refresh_config()` clears `_id_to_filename` | test_refresh_config_* |
| AC4 | `show_task()`: _id_to_filename →_task_cache → stat → glob | test_show_task_warm_id_cache_cold_*(3), test_show_task_id_cache_cold_* |
| AC5 | `show_task()` evicts stale entries on FileNotFoundError | test_show_task_stale_*, test_show_task_eviction_* (3) |
| AC6 | `_find_task_path()`: _id_to_filename → path → glob fallback | test_find_task_path_* (6 tests) |
| AC7 | No archive dispatch in `_find_task_path()` | test_find_task_path_with_archive_dir_*, test_find_task_path_tasks_dir_does_not_access_* |
[[2026-04-17]]

## Builder Notes

### Files Changed

- `serve/kanban/src/owlbear_kanban/engine.py` — implementation was already complete (confirmed by researcher at 0.95 confidence; pre-implemented feature verified by test-writer)
- `serve/kanban/tests/test_idtofilename_cache_944.py` — 23-test regression/specification suite (written by test-writer, all green)

### Test Results

- **23/23 passed** (0.12s) — `TestFromAC_IdToFilenameCache_944`
- No builder-discovered edge cases (implementation complete, test-writer covered all branches)

### Lint Status

- ruff: **clean** — `serve/kanban/src/` + `serve/kanban/tests/test_idtofilename_cache_944.py`

### Evidence Summary

GREEN phase was a verification pass only — implementation pre-existed (researcher validated 8/8 AC items in engine.py at lines 148, 196, 267–273, 283–307, 292–293, 831–847). All 23 AC tests pass without any code changes required.

### AC Coverage Verified

1. `_id_to_filename: dict[int, str] = {}` in `__init__` ✓
2. `list_tasks()` rebuilds from `_task_cache` ✓
3. `refresh_config()` clears `_id_to_filename` ✓
4. `show_task()` O(1) → stat validate → cache read → glob fallback ✓
5. `show_task()` dual eviction on FileNotFoundError ✓
6. `_find_task_path()` O(1) → glob fallback ✓
7. No archive dispatch in `_find_task_path()` ✓
8. All existing tests pass ✓
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest (scoped — test_idtofilename_cache_944.py): **23 passed, 0 failed**
- pytest (full suite — serve/kanban/tests/): **94 passed, 0 failed**

### Lint: clean (ruff exit code 0)

### Coverage

- owlbear_kanban.engine (task-scoped): 32% — gap is entirely in pre-existing untouched code; suppressed per review rules
- owlbear_kanban.engine (full suite): 46%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `__init__` adds `_id_to_filename: dict[int, str] = {}` | test_init_id_to_filename_exists_before_any_list_tasks | YES — asserts `hasattr`, `== {}`, `type is dict` | COVERED |
| AC2: `list_tasks()` rebuilds from `_task_cache` | 4× test_list_tasks_* | YES — checks specific IDs; cross-checks filtered vs non-filtered | COVERED |
| AC3: `refresh_config()` clears `_id_to_filename` | test_refresh_config_clears_id_to_filename_to_empty_dict | YES — asserts `== {}`, `type is dict` | COVERED |
| AC4: show_task() lookup chain | 3× test_show_task_warm_id_cache_cold_* + test_show_task_id_cache_cold_falls_back_to_glob | YES — mocks verify glob not called; asserts result.id; asserts cache repopulated | COVERED |
| AC5: evict stale entries on FileNotFoundError | test_show_task_stale_id_entry_raises_file_not_found, test_show_task_eviction_leaves_other_tasks_intact, test_show_task_after_eviction_second_call_can_succeed_via_glob | YES — verifies surgical eviction and self-healing via glob | COVERED |
| AC6: `_find_task_path()` lookup + fallback | 6× test_find_task_path_* | YES — warm+miss → glob; return type/absolute/exists; error paths | COVERED |
| AC7: No archive dispatch | test_find_task_path_with_archive_dir_does_not_use_id_to_filename, test_find_task_path_tasks_dir_does_not_access_archive_dir | YES — mock asserts archive.glob never called; result.parent == archive_dir | COVERED |
| AC8: All existing tests pass | Full suite 94/94 | YES — verified independently, not from builder self-report | COVERED |

No MISSING or LAX entries.

#### Security Review

- Hardcoded secrets: None
- Path traversal: Safe — `_id_to_filename` values sourced from disk scandir, not user input; path construction is `_tasks_dir / filename` with filesystem-safe filenames
- Insecure deserialization: None (no pickle, eval, exec, or unsafe yaml.load)
- Injection: None
- New dependencies: None
- Secret leakage: None

#### Test Integrity

Builder made **no changes** to engine.py or the TestFromAC class. Test-writer wrote all 23 tests; builder performed verification-only GREEN pass. No TestFromAC modifications to assess. ✅

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | No lazy `assert result` patterns; all assertions are specific (exact IDs, type checks, mock call counts, parent directory checks) |
| Negative/error-path coverage | STRONG | FileNotFoundError for stale, missing, non-integer IDs; ValueError-to-None branch; archive isolation |
| Manual mutation reasoning | STRONG | Flipping `==` in guard → test_find_task_path_with_archive_dir fails; removing eviction → test_show_task_eviction_leaves_other_tasks_intact fails; removing glob fallback → test_show_task_id_cache_cold fails |
| Test independence | STRONG | Each test uses `tmp_path`-backed fixtures; no shared mutable state |
| Descriptive test names | STRONG | All names fully describe scenario and expected behavior |

#### Data Safety

- No unvalidated LLM output, no race conditions (single-threaded engine), no unbounded inputs
- Dual eviction in show_task() is atomic within Python GIL — no data safety concern

#### Implementation-Aware Gaps

- `_find_task_path()` cold-cache path (`_id_to_filename == {}`, search_dir == tasks_dir → glob) not explicitly tested in this file, but covered by pre-existing suite in #943. Not a new code path.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single pass) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `_find_task_path()` cold-cache + tasks_dir path (empty `_id_to_filename` → glob) untested in this file but covered by #943 suite — informational only.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | engine.py:204 `self._id_to_filename: dict[int, str] = {}` | test_init_id_to_filename_exists_before_any_list_tasks | PASS |
| AC2 | engine.py:332–337 sorted dict comprehension from pruned `_task_cache` | 4× test_list_tasks_* | PASS |
| AC3 | engine.py:252 `self._id_to_filename = {}` | test_refresh_config_clears_id_to_filename_to_empty_dict | PASS |
| AC4 | engine.py:348 (id-cache check) → 357 (stat) → 362 (task-cache) → 370 (glob fallback) | 3× test_show_task_warm_id_cache_cold_* + test_show_task_id_cache_cold_falls_back_to_glob | PASS |
| AC5 | engine.py:358–361 dual eviction (`_task_cache.pop` + `del _id_to_filename[int_id]`) before raise | test_show_task_stale_*, test_show_task_eviction_* (×2) | PASS |
| AC6 | engine.py:1156–1161 guard → O(1) lookup → glob fallback at 1163 | 6× test_find_task_path_* | PASS |
| AC7 | engine.py:1156 `if search_dir == self._tasks_dir` guard; no archive branch anywhere in method | test_find_task_path_with_archive_dir_*, test_find_task_path_tasks_dir_does_not_access_* | PASS |
| AC8 | Full suite 94/94 — verified independently via quality-runner | serve/kanban/tests/ | PASS |

### Confidence: .97

### Verdict: PASS

[[2026-04-17]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | `_id_to_filename` is a private internal attribute; `show_task()` and `_find_task_path()` public signatures and observable behavior are unchanged |
| 2 | Module docstrings | Yes | Pass | `refresh_config()` docstring already names all 3 caches including `_id_to_filename` (L177); `show_task()` and `_find_task_path()` docstrings are accurate — no new behavior exposed to callers |
| 3 | External attribution → sources/overview.md | No | N/A | Researcher: "1 studied (engine.py codebase)"; no external URLs; prior #941 mtime-cache entry covers os.scandir pattern — no new row needed |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | `.owlbear/research/extend-mtime-cache-943.md` exists and is linked in task body |
| 6 | Scratch files | N/A | Pass | No `.owlbear/scratch/944-*` files found |

**Files updated:** None required.
**Verdict:** No documentation impact — internal performance optimization only. Docstrings accurate, no external sources, no CLI changes.
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `__init__` adds `_id_to_filename: dict[int, str] = {}` | engine.py:137 — spot-checked | PASS |
| AC2: `list_tasks()` rebuilds from `_task_cache` | engine.py:274-278 — sorted dict comprehension, spot-checked | PASS |
| AC3: `refresh_config()` clears `_id_to_filename` | engine.py:186 — spot-checked | PASS |
| AC4: `show_task()` id-cache, stat validate, glob fallback | engine.py:335-349 — 3-stage lookup, spot-checked | PASS |
| AC5: `show_task()` evicts on FileNotFoundError | engine.py:342 — dual eviction (_task_cache + _id_to_filename), spot-checked | PASS |
| AC6: `_find_task_path()` O(1) lookup, glob fallback | engine.py:915-921 — guard + cache check + direct return, spot-checked | PASS |
| AC7: No archive dispatch in `_find_task_path()` | engine.py:915 — guard `search_dir == self._tasks_dir`, no archive branch | PASS |
| AC8: All existing tests pass + new tests pass | Full suite 332 passed; kanban suite 94/94 (reviewer); 23/23 task tests pass | PASS |

### Test Results

- pytest (full): 332 passed, 6 failed — all 6 failures in serve/mcp-knowledge/ (pre-existing, outside kanban scope)
- ruff: clean (exit 0)

### Reviewer Evidence

Comprehensive review section present (.97 confidence, PASS verdict). Detailed AC mapping with line numbers, security review, test quality assessment, mutation reasoning. Trusted for code-level findings.

### Architect Quality: 5/5

AC specifies exact data structures (`dict[int, str]`), method-level behavior with explicit fallback chains, edge cases (eviction, archive isolation). Architecture review included failure mode map and challenger challenge/response. No builder improvisation required — clean implementation path.

### Deduction Breakdown

- AC lines without evidence: 0 (all 8 verified)
- Lint violations: 0
- AC quality: 5/5 (no deduction)
- Reviewer evidence section: present and detailed (no deduction)
- Full-suite failures in task scope: 0 (6 failures all in mcp-knowledge)

### Confidence: 1.00

### Action: archive
