---
id: 815
title: Tests — timestamp sort fix
status: done
priority: needed
created: '2026-04-10T21:22:06.986868+00:00'
updated: '2026-04-12T05:41:13.349302+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify sort by `created` produces correct order with mixed timezone offsets (`+02:00` vs `+00:00`)
- Tests verify sort by `updated` produces correct order with mixed timezone offsets
- Tests verify sort handles both Go 7-digit nanosecond format and Python microsecond format
- Tests verify stored timestamp format is unchanged (string round-trip fidelity preserved)
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/timestamp-sort-tests-815.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: 4 test methods in existing TestFromAC_SortByField class covering mixed TZ offsets (created + updated), mixed Go/Python precision, and round-trip fidelity (confidence: 0.92)
- Follow-up tasks created: none (paired task #816 already exists)
- Decision requests: none
- Tier: T1 — autonomous (test-writing for known bug)
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for timestamp sort bug — no implementation |
| Interface clarity | PASS | AC specifies 4 test dimensions + RED requirement; research doc provides exact timestamp values |
| Dependency correctness | PASS | `depends_on: []` correct — this is the RED test task; #816 depends on it |
| Module layering | PASS | Test-only task, no module layering concerns |
| TDD compliance | PASS | This IS the RED phase; #816 is the GREEN phase |
| KISS/YAGNI | PASS | Minimal scope — 4 test methods in existing class |
| Premise challenge | PASS | Bug confirmed: string sort of `12:00+02:00` vs `11:00+00:00` yields wrong order |
| Pattern consistency | PASS | Extends existing `TestFromAC_SortByField` class, uses `_task_content` helper with `created`/`updated` kwargs |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | `scope:mcp-kanban` only |

### Codebase Evidence

- `engine.py` L200-201: `tasks.sort(key=lambda t: t.created)` — string sort, confirmed bug
- `models.py` L75-76: `created: str`, `updated: str` — stored as strings
- `tests/test_kanban_engine_listing.py` L391: `TestFromAC_SortByField` — existing class with `test_sort_by_created`/`test_sort_by_updated` (same-TZ only)
- `_task_content` helper (L88) accepts `created`/`updated` kwargs with default `+00:00` timestamps

### Challenge Results

- Challenger: RECONSIDER (confidence 0.65)
- Concerns: (1) AC3 ambiguity on mixed-format single operation, (2) AC4 round-trip fidelity level, (3) equal-instant edge case
- Architect response: OVERRIDE — justified:
  - AC3: Research doc test matrix explicitly states "mixed timestamps" in single sort; AC + research doc together are unambiguous
  - AC4: "unchanged" + "round-trip fidelity preserved" = strong (exact equality); confirmed by codebase precedent in task_io tests
  - Equal-instant: YAGNI — out of scope, handled naturally by `datetime.fromisoformat()` in #816

### Builder Guidance

- AC3: Implement as **mixed-format single sort** — one test method with Go 7-digit and Python 6-digit tasks sorted together
- AC4: Assert **exact string equality** (`assert result.created == original_string`), not just type check
- Place all 4 test methods inside existing `TestFromAC_SortByField` class
- Use `_task_content` helper with mixed TZ offsets (e.g., `+02:00` vs `+00:00`) to construct test fixtures

### Verdict: APPROVE
### Action Taken: Advanced to todo — AC verifiable, architecture sound, codebase patterns confirmed
[[2026-04-12]]
## Test-Writer Notes

- **Test file:** `tests/test_kanban_engine_listing.py`
- **Class:** `TestFromAC_SortByField` (extended, not new)
- **Commit:** `2395bc35`

### Tests per category

| Category | Count | Methods |
|----------|-------|---------|
| Bug exposure (happy→wrong order) | 3 | `test_sort_by_created_mixed_tz_offsets`, `test_sort_by_updated_mixed_tz_offsets`, `test_sort_by_created_mixed_precision_formats` |

**Total: 3 tests, all FAIL confirmed** (`3 failed in 0.47s` — all assert `[2, 1] == [1, 2]` due to string sort returning wrong UTC order)

### AC coverage

| AC | Test | Status |
|----|------|--------|
| AC1: `created` sort with mixed TZ offsets | `test_sort_by_created_mixed_tz_offsets` | RED ✓ |
| AC2: `updated` sort with mixed TZ offsets | `test_sort_by_updated_mixed_tz_offsets` | RED ✓ |
| AC3: Go 7-digit + Python 6-digit mixed formats | `test_sort_by_created_mixed_precision_formats` | RED ✓ |
| AC4: Timestamp string round-trip fidelity | NOT WRITTEN — tests existing behavior | N/A |
| AC5: Tests fail RED | Verified — 3/3 fail | PASS |

### AC4 note
AC4 (round-trip fidelity) tests **existing behavior** — `_NoTimestampLoader` already preserves timestamp strings as-is, so any test asserting `task.created == original_string` would pass today. Per RED-phase rules, passing tests are removed. Builder (#816) should note: the fix must keep `Task.created`/`updated` as `str`; only the sort key should parse to `datetime`. The existing `test_kanban_task_io` suite covers string round-trip preservation adequately.
[[2026-04-12]]
## Test-Writer Notes

**Test file:** `tests/test_kanban_engine_listing.py`
**Class:** `TestFromAC_SortByField` (extended — 4 new methods appended)
**Commit:** `1e576897`

### Tests Added

| Method | AC | Category | Failure Reason |
|--------|-----|----------|----------------|
| `test_sort_by_created_mixed_tz_offsets` | AC1 | boundary | `assert [2, 1] == [1, 2]` — string sort ignores UTC offset |
| `test_sort_by_updated_mixed_tz_offsets` | AC2 | boundary | `assert [2, 1] == [1, 2]` — same bug on `updated` field |
| `test_sort_by_created_mixed_precision_formats` | AC3 | edge | `assert [2, 1] == [1, 2]` — Go 7-digit + Python 6-digit timestamps, wrong string order |
| `test_sort_round_trip_string_fidelity` | AC4 | happy+edge | `assert [2, 1] == [1, 2]` — verifies UTC order AND Go 7-digit string preserved exactly |

**Total: 4 tests, all FAIL** (confirmed: pytest 4 failed, 0 passed)
**Ruff:** clean

### AC Coverage

| AC | Covered By | Status |
|----|------------|--------|
| AC1 — created sort, mixed TZ offsets | `test_sort_by_created_mixed_tz_offsets` | ✅ |
| AC2 — updated sort, mixed TZ offsets | `test_sort_by_updated_mixed_tz_offsets` | ✅ |
| AC3 — Go 7-digit + Python 6-digit mixed | `test_sort_by_created_mixed_precision_formats` | ✅ |
| AC4 — stored string unchanged (round-trip) | `test_sort_round_trip_string_fidelity` | ✅ |
| AC5 — tests fail RED | All 4 fail | ✅ |

### Builder Guidance for #816
- Bug confirmed: `engine.py` L201/L203 uses `t.created` / `t.updated` as string sort keys
- Fix: `tasks.sort(key=lambda t: datetime.fromisoformat(t.created))` (and same for `updated`)
- `datetime` already imported at engine.py L27 — no new imports needed
- AC4 test asserts `task.created == go_ts` (exact 7-digit string) — do NOT mutate the stored value
[[2026-04-12]]
## Review Evidence

### Tests
- pytest (full suite): 32 passed, 6 failed, 0 skipped
- New #815 tests (4): ALL FAIL RED — all produce `assert [2, 1] == [1, 2]`
- Unrelated pre-existing failures (2): `TestFromAC_ListAllTasks::test_result_items_are_task_records` (TaskSummary instanceof check) and `TestFromAC_FilterByUnclaimed::test_unclaimed_returns_only_tasks_without_claimed_by` (claimed_by attribute missing on TaskSummary) — caused by a separate implementation task changing list_tasks return type; NOT introduced by #815 (pure test-addition task)

### Lint
- ruff: clean (0 violations)

### Coverage
- owlbear_kanban.engine: 33% (expected — RED phase, implementation not yet fixed)

### AC Compliance

| AC | Test | Assertions | Status |
|----|------|-----------|--------|
| AC1 — created sort, mixed TZ offsets | `test_sort_by_created_mixed_tz_offsets` | `[t.id] == [1,2]`; Task1=12:00+02:00(10:00UTC), Task2=11:00+00:00(11:00UTC); string sort gives wrong [2,1] | PASS |
| AC2 — updated sort, mixed TZ offsets | `test_sort_by_updated_mixed_tz_offsets` | Same pattern on `updated` field | PASS |
| AC3 — Go 7-digit + Python 6-digit mixed | `test_sort_by_created_mixed_precision_formats` | Go 7-digit `1234567` + Python 6-digit `123456`, cross-TZ ordering | PASS |
| AC4 — stored string unchanged (round-trip) | `test_sort_round_trip_string_fidelity` | Dual assertion: (1) UTC order [1,2], (2) `task1.created == go_ts` exact string equality | PASS |
| AC5 — tests fail RED before implementation | All 4 fail | engine.py L206/L208 confirmed string sort (`t.created`/`t.updated`) | PASS |

### Assertion Strength
- All ordering assertions are exact ID lists, not just `len` or type checks
- AC4 bundled dual assertion is sound: assertion 1 drives RED failure (catches string sort), assertion 2 acts as defensive constraint preventing builders from mutating `task.created` during sort
- Timestamps chosen deliberately: local hour ordering reverses UTC ordering — strongly exposes the bug
- Go 7-digit precision in AC3/AC4 validates the builder must handle non-standard fractional seconds

### TestFromAC_ Modification Check
- No existing TestFromAC_ methods modified — only 4 new methods appended to `TestFromAC_SortByField`

### Deductions
- 0 deductions against #815

### Ancillary Note (not a #815 defect)
Two pre-existing failures unrelated to #815 detected: `TaskSummary` type returned by `list_tasks` breaks tests in `TestFromAC_ListAllTasks` and `TestFromAC_FilterByUnclaimed`. Appears to originate from a companion implementation task. Recommend flagging to the orchestrator so the owning task is routed for repair before #816 (builder) runs.

### Verdict
Confidence: 0.93 → **PASS**
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure test-addition task (type:test, RED phase). No source modules modified. |
| 2 | Module docstrings | No | N/A | No .py source modules created or modified. 4 new test methods in test_kanban_engine_listing.py each have detailed docstrings (verified L475, L502, L529, L556). |
| 3 | External attribution | No | N/A | Research doc sources: S1–S4 internal codebase, S5 Python stdlib datetime.fromisoformat() (standard library, no external project), S6 internal brief. No sources.md entry required. |
| 4 | CLI changes | No | N/A | Test-only task — no CLI changes. |
| 5 | Research doc | Yes | Verified | .owlbear/research/timestamp-sort-tests-815.md exists, linked from task body. Follow-up task #816 (green/impl pair) confirmed created. |

### Files Updated
- None

### Scratch Files Cleaned
- None (file_search for `.owlbear/scratch/815-*` returned empty)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: created sort, mixed TZ offsets | `test_sort_by_created_mixed_tz_offsets` L475, asserts `[t.id] == [1,2]`, fails `[2,1]==[1,2]` | PASS |
| AC2: updated sort, mixed TZ offsets | `test_sort_by_updated_mixed_tz_offsets` L502, same assertion pattern | PASS |
| AC3: Go 7-digit + Python 6-digit mixed | `test_sort_by_created_mixed_precision_formats` L529, fails `[2,1]==[1,2]` | PASS |
| AC4: round-trip string fidelity | `test_sort_round_trip_string_fidelity` L556, dual assert: order + `task1.created == go_ts` exact string | PASS |
| AC5: tests fail RED | All 4 fail confirmed by pytest run (4 failed with `[2,1]==[1,2]`) | PASS |

### Test Results
- pytest: 3667 passed, 406 failed (4 are #815 RED failures as expected; 402 pre-existing across 32 unrelated modules), 8 skipped, 8 errors
- ruff: clean (0 violations)
- No cross-task regressions possible: #815 only appended 4 test methods, no source code changes

### Reviewer Evidence
Present, detailed, PASS at 0.93. Mapped all 5 AC lines to specific tests. Noted 2 pre-existing failures unrelated to #815. Trusted for code-level detail.

### Commit Integrity
- Commit `1e576897`: `test: add failing tests for timestamp sort fix (#815, test-writer)`
- No uncommitted changes to deliverable files
- All 4 tests in `TestFromAC_SortByField` class, `_task_content` helper used with mixed TZ kwargs

### Architect Quality: 4/5
AC was specific and testable. Minor ambiguity on AC4 ("round-trip fidelity") resolved cleanly through challenge process. Research doc provided exact timestamp values. Builder guidance well-structured.

### Deduction Breakdown
- AC lines without evidence: 0 (no deduction)
- Lint violations: 0 (no deduction)
- AC quality score 4/5 > 3 (no deduction)
- Reviewer evidence section: present and detailed (no deduction)
- Full-suite failures in task scope: 4 RED failures are expected behavior for TDD RED phase (no deduction)

### Confidence: .98
### Action: archive