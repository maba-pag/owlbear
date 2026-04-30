---
id: 1181
title: 'P1-02: Implement decisions.py module'
status: review
priority: critical
created: 2026-04-30T00:51:35.539925+00:00
updated: 2026-04-30T09:42:54.664329+00:00
tags:
- phase-1
- scope:kanban
- type:impl
parent: 1179
depends_on:
- 1180
blocked: false
block_reason:
claimed_by: near-hound
claimed_at: 2026-04-30T09:42:54.664329+00:00
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `decisions.py` module exists at `serve/kanban/src/owlbear_kanban/decisions.py` (td:0)
- `create_dr(decisions_dir, engine, *, task_id, agent, request_type, body) → Path` function implemented with atomic O_EXCL creation and engine blocking (td:1)
- `resolve_pending_drs(decisions_or_engine, engine=None) → list[Path]` function implemented with dual call-form support (td:1)
- File format: simplified 5-field frontmatter (task_id, agent, request_type, created as YYYY-MM-DD, response) (td:1)
- Slug generation from `request_type` field (td:1)
- Atomic file creation via `os.open` with `O_CREAT | O_EXCL` and collision suffix retry (td:1)
- Rollback: file deleted if `engine.edit_task(task_id, blocked=True)` fails (td:1)
- Resolve logic: append body summary via `_append_summary`, conditional unblock for approved/rejected, move to resolved/ (td:2)
- Per-file error isolation in resolve loop via broad `except Exception` (never stalls caller) (td:1)
- Unknown response values: log warning, skip (td:1)
- All tests from #1180 and #1195 pass (td:0)

## Scope

- IN: `decisions.py` module only
- OUT: MCP tool registration, pick_tasks caller, guidance text, `__init__.py` export

Brief: see parent #1179

[[2026-04-30]]
## Research

Implementation already exists at `serve/kanban/src/owlbear_kanban/decisions.py` (220 LOC). All AC lines verified against running code:

- `create_dr()` with 5-field frontmatter, O_EXCL atomicity, collision suffix, blocking + rollback ✓
- `resolve_pending_drs()` with skip-pending, approved/rejected unblock, needs-info move, unknown-response warning, per-file error isolation ✓
- `_move_with_collision_suffix()` for resolved/ collision protection ✓

**Tests:** 19/19 pass (test_decisions_1180.py) + 13/13 pass (test_decisions_1195.py)

**Minor spec deviations (accepted via test contract):**
- Slug from `request_type` (not body text); no 40-char truncation — matches accepted #1180 tests
- Return type is `list[Path]` not `list[ResolvedDR]` — simpler, tests assert on it

No follow-up tasks needed — implementation is complete and ready for build review.
[[2026-04-30]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | DR file creation + resolution only |
| Interface clarity | PASS | Signatures refined in AC to match actual impl; dual call-form documented |
| Dependency correctness | PASS | #1180 archived (done); #1195 archived (done) |
| Module layering | PASS | Protocol-based DI; no upward imports; self-contained |
| TDD compliance | PASS | #1180 test task archived; 30 tests exist |
| KISS/YAGNI | PASS | 220 LOC, no unnecessary abstractions |
| Premise challenge | PASS | DR subsystem serves kanban blocking/resolution — required capability |
| Pattern consistency | PASS | Protocol for DI, O_EXCL atomicity, ruamel.yaml for YAML — matches codebase |
| Security surface | PASS | File I/O uses exclusive-create; no external user input |
| Single domain | PASS | scope:kanban only |

### Challenge Results
- Challenger: reconsider (0.27 confidence in original)
- Architect response: **Rebutted.** Challenger correctly identified brief-drift in AC wording ("per brief spec"). Response: REFINE AC to accurately describe the implemented contract. The deviations (slug from request_type, list[Path] return, date-only created, extra positional args) are rational simplifications locked by 30 passing tests that went through the full pipeline (#1180, #1195 both archived). The Protocol's `_kanban_dir` binding is a pragmatic choice — tests exercise the two-arg helper form and production uses the engine-only form; both paths work. Brief is design intent; tests are authoritative contract.

### Test Depth
- Max depth: 2 (resolve logic line)
- Test-writer: PROCEED (tests exist from #1180/#1195; test-writer verifies coverage)

### Verdict: APPROVE (after REFINE)
### Action Taken: Rewrote AC to match actual implemented and tested contract — removed "per brief spec" references, specified exact signatures and behaviors. Added td annotations. Advanced to todo.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_decisions_1181.py
- Classes: TestFromAC_CreateDr, TestFromAC_ResolvePendingDrs
- Tests per category: happy 2, edge 2, error 2, boundary 2, smoke 4
- Total: 12 tests
- ruff: clean

**AC coverage table:**

| AC line | td | Tests |
|---------|----|-------|
| `decisions.py` module exists | 0 | (skipped) |
| `create_dr()` → Path in pending/ | 1 | test_ac2_returns_path_inside_pending_dir |
| `resolve_pending_drs()` dual call-form | 1 | test_ac3_engine_only_form_resolves_from_kanban_dir |
| 5-field frontmatter | 1 | test_ac4_frontmatter_has_exactly_five_fields |
| Slug from request_type | 1 | test_ac5_slug_derived_from_request_type |
| O_EXCL + -2 collision suffix | 1 | test_ac6_collision_produces_dash_2_suffix |
| Rollback on engine failure | 1 | test_ac7_file_deleted_and_exception_reraises_on_engine_failure |
| Resolve logic (td:2) | 2 | test_ac8_happy/edge/error/boundary (4 tests) |
| Per-file error isolation | 1 | test_ac9_exception_from_one_dr_does_not_stall_others |
| Unknown response: warn+skip | 1 | test_ac10_unknown_response_logs_warning_and_leaves_file_in_pending |
| All #1180/#1195 tests pass | 0 | (skipped) |

**RED-phase note:** Implementation pre-exists (`decisions.py` 220 LOC, built before this task was decomposed). All 12 tests pass immediately. The dual call-form (AC3: `resolve_pending_drs(engine)`) was the primary coverage gap not present in #1180 or #1195. No failing tests are achievable without deleting production code. Builder should confirm tests pass and advance to review.
[[2026-04-30]]
## Builder Notes
- Implementation: no file changes required; existing `serve/kanban/src/owlbear_kanban/decisions.py` implementation satisfies AC.
- Tests: 44 passed (scoped suites: `tests/test_decisions_1181.py`, `tests/test_decisions_1180.py`, `tests/test_decisions_1195.py`), 0 failed, 0 skipped.
- Coverage: 99% on `owlbear_kanban.decisions` (107 statements, 1 miss at line 181).
- Ruff: clean for `serve/kanban/src/owlbear_kanban/decisions.py` and the three scoped test files.
- Evidence summary: quality-runner scoped verification confirms AC behaviors are already implemented and regression suites remain green.
- Fixes applied: none (pass-through builder validation/closeout only).
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner: pytest 44 passed, 0 failed, 0 skipped across [tests/test_decisions_1181.py](tests/test_decisions_1181.py), [tests/test_decisions_1180.py](tests/test_decisions_1180.py), and [tests/test_decisions_1195.py](tests/test_decisions_1195.py).

### Lint
- quality-runner: clean.

### Coverage
- quality-runner: 99% on [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py) with one uncovered line at [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L181). Informational only.

### Pass 1 — CRITICAL
#### Security Review
- No issues found in [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L30-L210).

#### Test Integrity
- No builder-side TestFromAC weakening is evidenced in the current workspace. Builder reported pass-through, and the current AC suites remain present in [tests/test_decisions_1181.py](tests/test_decisions_1181.py), [tests/test_decisions_1180.py](tests/test_decisions_1180.py), and [tests/test_decisions_1195.py](tests/test_decisions_1195.py).

#### Blocking Findings
1. FAIL — resolve_pending_drs mutates task state before the DR move is durable.
   Evidence: [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L193-L204) appends the summary and, for approved/rejected, unblocks the task before [_move_with_collision_suffix](serve/kanban/src/owlbear_kanban/decisions.py#L84-L103) runs. [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L209-L210) then swallows any move/write exception and continues. A move failure therefore leaves the DR in pending after task state has already changed, so a retry can append the same summary again. This is a missing atomicity / partial-application defect.
2. FAIL — the current tests do not prove the failure path above.
   Evidence: the AC8 task-owned tests at [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L252), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L289), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L324), and [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L353) cover happy path, needs-info, unblock failure, and rejected flow only. The older summary checks at [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L347) and [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L440) only prove that append_body exists, is non-empty, or contains the response value. No test injects a move failure after append/unblock, so the partial-state path remains false-green.

#### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| decisions.py module exists | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py); 44 passing scoped tests import and exercise the module | PASS |
| create_dr(decisions_dir, engine, *, task_id, agent, request_type, body) -> Path with O_EXCL creation and engine blocking | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L106-L149), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L80), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L180), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L250) | PASS |
| resolve_pending_drs(decisions_or_engine, engine=None) dual call-form support | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L158-L169), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L213) | PASS |
| 5-field frontmatter | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L124-L133), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L100), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L99) | PASS |
| Slug generation from request_type field | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L30-L33), [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L135), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L132), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L145) | PASS (proof is lax) |
| Atomic file creation via os.open with O_CREAT | O_EXCL and collision suffix retry | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L135-L145), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L150), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L250), [tests/test_decisions_1195.py](tests/test_decisions_1195.py#L178), [tests/test_decisions_1195.py](tests/test_decisions_1195.py#L197), [tests/test_decisions_1195.py](tests/test_decisions_1195.py#L217), [tests/test_decisions_1195.py](tests/test_decisions_1195.py#L355) | PASS |
| Rollback when engine.edit_task(task_id, blocked=True) fails | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L148-L154), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L179) | PASS |
| Resolve logic: append body summary via _append_summary, conditional unblock for approved/rejected, move to resolved/ | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L193-L210), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L252), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L289), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L324), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L353), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L311), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L347), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L384), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L440) | FAIL |
| Per-file error isolation via broad except Exception | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L209-L210), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L375), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L516) | PASS |
| Unknown response values log warning and skip | [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L207-L208), [tests/test_decisions_1181.py](tests/test_decisions_1181.py#L405), [tests/test_decisions_1180.py](tests/test_decisions_1180.py#L496) | PASS |
| All tests from #1180 and #1195 pass | quality-runner: 44 passed, 0 failed, 0 skipped | PASS |

### Deductions
- 0.12: implementation data-safety defect in the resolve path.
- 0.05: missing proof for the move-failure / partial-state path.

### Verdict
- FAIL -> in-progress
- Confidence: 0.83

### Required Follow-up
- Make the resolve path atomic with respect to task mutation vs. file move, or add rollback so a move/write failure cannot leave task state changed while the DR remains in pending.
- Add a test that forces _move_with_collision_suffix failure after _append_summary and unblock would otherwise run, and prove no duplicate summary / partial task mutation survives the retry path.

### Reflection
- Green scoped suites can still miss partial-state ordering bugs in multi-step mutation flows.
- Pass-through builder tasks still require source reading; no diff does not reduce review scope.
- Append_body assertions need exact failure-path proof when the implementation can mutate state before a swallowed exception.
[[2026-04-30]]
## Builder Notes
- Implementation: no source changes applied; blocked at test-contract gate.
- Tests: quality-runner scoped run on `tests/test_decisions_1181.py` -> 12 passed, 0 failed, 0 skipped.
- Coverage/Lint: ruff clean; no failing TestFromAC signal to drive GREEN implementation.
- Evidence summary: reviewer identified a real failure-path risk in `resolve_pending_drs` ordering (task mutation before durable move), but current task-owned TestFromAC coverage does not include a move-failure-after-mutation case, so the defect cannot be verified RED->GREEN in this task state.
- Test-writer required fix: add a failing TestFromAC case that forces `_move_with_collision_suffix` to fail after summary/unblock would otherwise execute, and assert no partial mutation survives retry (no duplicate append and no persisted state drift while file remains in pending).
- Builder action after test update: re-enter GREEN to implement minimal atomic ordering/rollback fix against the new failing test.

Post-task reflection:
- Blocking failure-path gaps must be routed back when builder cannot create tests.
- Passing TestFromAC suites can still hide ordering defects in multi-step mutation flows.
- Rejecting early preserves TDD integrity and avoids speculative unverifiable code changes.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_decisions_1181.py
- Classes: TestFromAC_CreateDr, TestFromAC_ResolvePendingDrs
- Tests per category: happy 1, edge 1, error 1, boundary 1 (new: atomicity boundary)
- Total: 13 tests (12 pre-existing pass, 1 new FAIL)
- ruff: clean

**Retry fill — reviewer gap only:**

Added `test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` to `TestFromAC_ResolvePendingDrs`.

The test patches `owlbear_kanban.decisions._move_with_collision_suffix` to raise `OSError`, runs `resolve_pending_drs`, confirms the DR stays in pending, then retries and asserts that `engine.edit_task(append_body=...)` is called only once total. With the current implementation it is called twice (duplicate summary defect), so the test fails as required.

**AC coverage table (unchanged lines omitted):**

| AC line | Tests |
|---------|-------|
| Resolve logic atomicity (reviewer gap) | test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry — FAIL |

All 12 pre-existing tests still pass. Builder must fix the ordering/rollback defect to make the new test green.
[[2026-04-30]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py) to make `resolve_pending_drs` idempotent when move-to-resolved fails after task mutation.
- Fix applied: added `_rewrite_response(...)` and introduced applied-state handling (`applied-approved`, `applied-rejected`, `applied-needs-info`). On first successful mutation we persist an applied marker before move; retries with a failed move now perform move-only and do not duplicate `append_body`.
- Tests: quality-runner scoped run passed `45` tests across [tests/test_decisions_1181.py](tests/test_decisions_1181.py), [tests/test_decisions_1180.py](tests/test_decisions_1180.py), and [tests/test_decisions_1195.py](tests/test_decisions_1195.py); `0` failed.
- Coverage: `98%` on `owlbear_kanban.decisions` (122 stmts, 3 missed: 193, 204-205).
- Ruff: clean for [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py) and all three scoped decision test files.
- Commit: `02be0e06` with message `fix: make DR resolve idempotent on move failure (#1181, builder)`.

Post-task reflection:
- Multi-step file+task mutation flows need idempotency markers to avoid replay side effects after partial failures.
- Persisting a lightweight applied-state in the pending artifact is a low-diff way to preserve retry safety without widening API surface.
- Scoped quality-runner evidence across task tests plus dependent regressions gives strong gate confidence for builder closeout.