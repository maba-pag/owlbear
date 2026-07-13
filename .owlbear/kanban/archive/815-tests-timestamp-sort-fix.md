---
id: 815
title: Tests — timestamp sort fix
status: archived
priority: medium
created: '2026-04-10T21:22:06.986868+00:00'
updated: '2026-04-13T18:11:46.502035+00:00'
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
[[2026-04-13]]
## Research

- Research doc: .owlbear/research/timestamp-sort-tests-815.md (validated 2026-04-13)
- Sources: 6 studied, 4 high-relevance (all codebase-internal)
- Recommendation: 4 test methods in existing TestFromAC_SortByField class (confidence: 0.92)
- Follow-up tasks created: none new (#816 already exists)
- Decision requests: none

### Validation Findings

- Engine fix (`datetime.fromisoformat()`) is already implemented at engine.py L252-255
- 4 tests exist in test_kanban_engine_listing.py; 3 pass GREEN, 1 has defect
- **Test defect:** `test_sort_round_trip_string_fidelity` fails with `AttributeError: 'TaskSummary' has no attribute 'created'` — `list_tasks()` returns `TaskSummary` which drops `created`/`updated`. Fix: use `show_task()` for round-trip check.
- TDD RED phase was bypassed (fix was implemented before tests)
- No Go 7-digit nanosecond timestamps exist in real task files (defensive handling only)
- Tier: T1 — bug fix, no arch/security impact
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for one bug fix only |
| Interface clarity | PASS | AC1-4 specify exact scenarios, timestamps, and expected ordering |
| Dependency correctness | PASS | No depends_on; #816 depends on this task (correct direction) |
| Module layering | PASS | Tests only — no production code changes |
| TDD compliance | PASS | This IS the test task; paired with #816 (impl) |
| KISS/YAGNI | PASS | 4 focused test methods in existing class, no new helpers needed |
| Premise challenge | PASS | Tests verify a real demonstrated bug (string sort vs UTC order) |
| Pattern consistency | PASS | Extends existing `TestFromAC_SortByField` using `_add_task` / `_make_kanban_dir` helpers |
| Security surface | N/A | Test-only task |
| Single domain | PASS | scope:mcp-kanban only |

### AC Refinement

**AC5 revision (TDD RED waiver):** The engine fix (`datetime.fromisoformat()` at `engine.py` L252-255) was implemented before tests. Requiring RED is artificial — the builder should NOT revert production code to demonstrate RED. AC5 is replaced with:

> ~~Tests fail RED before implementation~~
> AC5: Tests assert correct UTC chronological ordering (TDD RED phase waived — fix predates tests per research validation)

**AC4 defect — mandatory fix:** `test_sort_round_trip_string_fidelity` fails with `AttributeError: 'TaskSummary' has no attribute 'created'` because `list_tasks()` returns `TaskSummary` (extra="ignore", excludes `created`/`updated`). Fix: use `engine.show_task(str(task_id))` to get the full `Task` object for round-trip assertion. This is architecturally correct — `TaskSummary` is intentionally lightweight; full `Task` is needed for timestamp field verification. This fix is in-scope for #815 per research doc.

### Builder Guidance

1. Fix `test_sort_round_trip_string_fidelity`: replace `task1.created` (on `TaskSummary`) with `engine.show_task("1").created` (on `Task`)
2. Verify all 4 AC tests pass GREEN after the defect fix
3. Do NOT revert `engine.py` to demonstrate RED — waiver documented above

### Challenge Results

- Challenger: reconsider (confidence 0.62)
- Concerns: AC5 unachievable, AC4 test defect must be fixed in-task
- Architect response: accepted — AC5 reworded with TDD waiver, AC4 defect fix confirmed in-scope with explicit builder guidance. Reverse+timestamp gap noted as low-risk (list.reverse() is format-agnostic).

### Verdict: APPROVE (with inline refinement)
### Action Taken: Advanced to todo. AC5 reworded, AC4 defect fix scoped in builder guidance.
[[2026-04-13]]
## Test-Writer Notes

**Test file:** `tests/test_kanban_engine_listing.py`
**Class:** `TestFromAC_SortByField` (extended, existing class)

### Defect Fixed (AC4 — in-scope per architecture review)

`test_sort_round_trip_string_fidelity` accessed `.created` on a `TaskSummary` returned by `list_tasks()`. `TaskSummary` excludes `created`/`updated` via `extra="ignore"`. Fixed by replacing:
- `task1 = next(...); assert task1.created == go_ts`
- with: `task1_full = engine.show_task("1"); assert task1_full.created == go_ts`
`show_task()` returns a full `Task` object that carries `created`.

### AC Coverage

| AC | Test | Result |
|----|------|--------|
| AC1 — created sort, mixed TZ offsets | `test_sort_by_created_mixed_tz_offsets` | PASS GREEN |
| AC2 — updated sort, mixed TZ offsets | `test_sort_by_updated_mixed_tz_offsets` | PASS GREEN |
| AC3 — Go 7-digit + Python 6-digit mixed precision | `test_sort_by_created_mixed_precision_formats` | PASS GREEN |
| AC4 — round-trip string fidelity (defect fixed) | `test_sort_round_trip_string_fidelity` | PASS GREEN |
| AC5 — TDD RED waiver | engine fix predates tests; waiver documented in arch review | N/A |

**Total: 4 tests, all PASS GREEN (TDD RED waiver in effect — fix was pre-implemented)**

### Test Categories
- Happy path: correct UTC chronological order with same-offset timestamps (pre-existing tests)
- Edge cases: mixed TZ offsets (+02:00 vs +00:00), mixed precision (7-digit vs 6-digit)
- Boundary: Go 7-digit nanosecond timestamp not truncated after round-trip

pytest run: `4 passed, 0 failed`
[[2026-04-13]]
## Builder Notes

### Files Changed
- `tests/test_kanban_engine_listing.py` — no changes needed by builder; test-writer already applied the AC4 defect fix (`show_task("1")` → `Task` instead of `TaskSummary`)

### Test Results
- 38 passed, 0 failed (full `test_kanban_engine_listing.py` suite)
- AC-specific tests (4 in `TestFromAC_SortByField`): all GREEN
  - `test_sort_by_created_mixed_tz_offsets` PASS
  - `test_sort_by_updated_mixed_tz_offsets` PASS
  - `test_sort_by_created_mixed_precision_formats` PASS
  - `test_sort_round_trip_string_fidelity` PASS

### Lint Status
- `ruff check tests/test_kanban_engine_listing.py` → `All checks passed!` (exit 0)

### Evidence Summary
- TDD RED waiver in effect — `datetime.fromisoformat()` fix at `engine.py` L252-255 was pre-implemented before tests
- AC4 defect (`.created` on `TaskSummary`) was fixed by test-writer per architecture guidance: `engine.show_task("1").created` returns full `Task` with timestamp fields
- All 4 AC tests assert correct UTC chronological ordering over string-lexicographic ordering
- No production code changes required or made
[[2026-04-13]]
## Review Evidence

### Test Results
pytest `tests/test_kanban_engine_listing.py`: **38 passed, 0 failed** (Quality-Runner, independent run)

### Lint
`ruff check tests/test_kanban_engine_listing.py`: **clean** (exit 0)

### Coverage
engine.py: 31% overall — acceptable for a test-only task; no production code changes were in scope.

### AC Compliance

| AC | Test | Evidence | Status |
|----|------|----------|--------|
| AC1 — `created` sort, mixed TZ offsets | `test_sort_by_created_mixed_tz_offsets` | Task 1: `12:00+02:00` = 10:00 UTC; Task 2: `11:00+00:00` = 11:00 UTC. Assertion `[1,2]` fails under string sort (lexicographic gives `[2,1]`). | PASS |
| AC2 — `updated` sort, mixed TZ offsets | `test_sort_by_updated_mixed_tz_offsets` | Identical adversarial data structure on `updated` field. Assertion would fail with string sort. | PASS |
| AC3 — Go 7-digit + Python 6-digit mixed precision | `test_sort_by_created_mixed_precision_formats` | `.1234567` (7-digit) and `.123456` (6-digit) both present. `datetime.fromisoformat()` handles both; string sort would give wrong order. | PASS |
| AC4 — round-trip string fidelity | `test_sort_round_trip_string_fidelity` | Uses `engine.show_task("1")` (full `Task` object) — not `list_tasks()` (would give `TaskSummary` without `created`). Assertion `task1_full.created == go_ts` verifies no truncation. | PASS |
| AC5 — TDD RED waiver | N/A | Waiver documented by architect; engine fix predates tests. Structural waiver accepted. | N/A |

### TestFromAC_* Integrity
No TestFromAC_* methods removed or weakened. All 4 new methods are present and unmodified. Pre-existing tests unaffected.

### Engine Fix Verification
`engine.py` L252-255: `datetime.fromisoformat()` sort key confirmed for both `created` and `updated` fields.

### Deductions
None.

### Verdict
Confidence: **0.95** → **PASS**
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only task; no production code changes. `copilot-instructions.md` unchanged. |
| 2 | Module docstrings | No | N/A | Only `tests/test_kanban_engine_listing.py` modified; all 4 new `TestFromAC_SortByField` methods carry inline docstrings (verified L462–557). Test methods are not public API. |
| 3 | External attribution | No | N/A | Research doc confirms all 4 high-relevance sources are codebase-internal. `sources/overview.md` unchanged. |
| 4 | CLI changes | No | N/A | Test-only task; no CLI surface touched. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/timestamp-sort-tests-815.md` exists and is linked in task body Research section. Follow-up: #816 already existed. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `815-*` scratch files found)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — created sort, mixed TZ offsets | `test_sort_by_created_mixed_tz_offsets` L475 — adversarial timestamps (12:00+02:00=10UTC vs 11:00+00:00=11UTC), asserts [1,2] | PASS |
| AC2 — updated sort, mixed TZ offsets | `test_sort_by_updated_mixed_tz_offsets` L502 — same pattern on `updated` field | PASS |
| AC3 — Go 7-digit + Python 6-digit precision | `test_sort_by_created_mixed_precision_formats` L529 — `.1234567` and `.123456` both handled | PASS |
| AC4 — round-trip string fidelity | `test_sort_round_trip_string_fidelity` L556 — uses `engine.show_task("1")` (full Task, not TaskSummary), asserts `task1_full.created == go_ts` | PASS |
| AC5 — TDD RED waiver | Documented in architect review; engine fix predates tests | N/A |

### Test Results
- pytest (task-scoped): 38 passed, 0 failed
- pytest (full suite): 4134 passed, 379 failed, 8 skipped — all failures in unrelated files (browser MCP, lint hooks, package boundaries)
- ruff: All checks passed

### Architect Quality: 4/5
AC1-4 specific with exact timestamps and expected ordering. AC5 was initially unachievable (TDD RED when fix pre-existed), but architect caught it in review and issued a waiver with rationale. AC4 test defect identified in research and resolved with clear builder guidance. Minor upstream gaps, well-handled.

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: 0 (all 4 verified) → 0
- Lint violations: 0 → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (detailed, PASS at .95) → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: 1.00
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1e576897 | test | tests/test_kanban_engine_listing.py | #815 |