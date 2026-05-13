---
id: 1526
title: 'P1-01: tests for dep-status guidance in start_work (AC1-AC3)'
status: archived
priority: critical
created: 2026-05-13T12:17:42.525688+00:00
updated: 2026-05-13T14:09:49.989451+00:00
tags:
  - phase-1
  - scope:kanban
  - test
parent: 1525
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Summary

Write unit tests in `serve/kanban/tests/` for the dep-status guidance feature in `agent_view.start_work()`.

Brief: see parent #1525

## Acceptance Criteria

- AC1: Test that `start_work()` on a task where `_compute_dep_status()` returns `"blocked"` (i.e., at least one dep is active and non-archived) returns `guidance` containing exactly one string equal to `"⚠️ This task has unresolved dependencies (IDs: {comma-separated ints}). Review and confirm with the user that starting this work is intentional."` — assert exact value (not substring/`any()`), with dep IDs as comma-separated integers matching the blocked dep set. This is dependency-derived guidance, NOT the manual `blocked=true` field path.
- AC2: Test that `start_work()` on a task with `depends_on == []` returns `guidance == []`. Same for a task where all deps are archived with `archival_reason="completed"` (dep_status resolved). Additionally, test that `start_work()` on a task with a redirect-status dependency (archived with `archival_reason` of `"deprecated"` or `"duplicate"`) returns `guidance == []` — this directly proves the redirect branch through `start_work()` does not trigger guidance. Redirect deps are a non-goal of this feature and do NOT trigger guidance (treated as resolved).
- AC3: Test that `start_work()` on a task where a dep lookup raises each of `(FileNotFoundError, CorruptionError, ValueError, KeyError)` silently continues — the failing dep is skipped (no exception propagates, response is a valid `SingleTaskResponse`). When ALL dep lookups fail, `guidance == []` (conservative no-guidance — no blocked deps can be detected).

## Scope

- In scope: unit tests for AC1-AC3 in `serve/kanban/tests/`
- Out of scope: implementation code, MCP layer, consolidation tests

## Context

- `show_task()` dep pattern at `agent_view.py` L246 shows the iteration + exception tuple to mirror
- `_compute_dep_status()` at `engine.py` L663 computes blocked/redirect/ok/None
- `_dep_effect_from_archival_reason()` at `engine.py` L652: `"deprecated"` or `"duplicate"` → redirect effect
- `_to_single_response()` already accepts `guidance` kwarg
- Manual `blocked=true` field is a SEPARATE concept (ERR_BLOCKED_NOT_CLAIMABLE) — tests must not conflate

Proof bundle: behavioral
2026-05-13T13:25:37+00:00
## Architecture Review (re-review cycle 2)

### Reviewer Finding
Second review cycle rejected AC2 proof as insufficient: no direct `start_work()` test for the redirect branch (dep archived with `archival_reason="deprecated"` or `"duplicate"`). Existing AC2 tests covered only no-deps and archived-completed, leaving the redirect path untested through the guidance entrypoint.

### AC Refinement Applied
- AC2: Added explicit requirement for a redirect-status dependency test — `start_work()` on a task whose dep is archived with `archival_reason` of `"deprecated"` or `"duplicate"` must return `guidance == []`. This directly falsifies regressions that warn on redirect deps.
- Context section: Added `_dep_effect_from_archival_reason()` reference (engine.py L652) for test-writer clarity.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: SKIP (tag: test — pass-through; builder writes tests)

### Challenge Results
- Challenger: SKIPPED — re-review cycle with single AC wording fix; no architectural change from prior approved review

### Verdict: APPROVE
### Action Taken: Refined AC2 to require direct redirect-dependency test, advanced to todo
2026-05-13T13:40:20+00:00
## Test-Writer Notes
- Test file: serve/kanban/tests/test_agent_view_start_work_1526.py
- Classes: TestFromAC_DepStatusGuidance
- Tests per category: happy 4, edge 4, error 4, boundary 1
- Total: 13 tests, all PASS (implementation pre-exists in agent_view.start_work)
- ruff: clean

### Implementation pre-exists note
All 13 tests pass against the current implementation in `agent_view.py` L962-1060.
The dep-status guidance feature (AC1-AC3) was already built before this test-writing
task ran. Builder skip applied — advancing directly to review.

### AC coverage
| AC | Tests |
|----|-------|
| AC1 — active dep → exact guidance string | test_start_work_active_dep_returns_guidance_exact_string, test_start_work_multiple_active_deps_guidance_lists_all_ids, test_start_work_guidance_has_exactly_one_entry, test_start_work_dep_ids_in_guidance_match_blocked_set_only |
| AC2 — no deps / archived-completed / redirect deps → guidance==[] | test_start_work_no_depends_on_returns_empty_guidance, test_start_work_dep_archived_completed_returns_empty_guidance, test_start_work_dep_archived_deprecated_returns_empty_guidance, test_start_work_dep_archived_duplicate_returns_empty_guidance |
| AC3 — exceptions silently skipped / all-fail → guidance==[] | test_start_work_dep_lookup_file_not_found_silently_continues, test_start_work_dep_lookup_corruption_error_silently_continues, test_start_work_dep_lookup_value_error_silently_continues, test_start_work_dep_lookup_key_error_silently_continues, test_start_work_all_dep_lookups_fail_guidance_is_empty |
2026-05-13T13:57:04+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1526 -> docs | AC mapped to code and evidence sufficient.
- Builder-skip evidence was thinner than a normal behavioral task, so I independently verified the proof surface with quality-runner.
- quality-runner scoped rerun on `serve/kanban/tests/test_agent_view_start_work_1526.py` and `tests/test_start_work_dep_guidance_1526.py`: 24 passed, 0 failed, ruff clean, pytest=0, ruff=0, Errors=none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/kanban/src/owlbear_kanban/agent_view.py:996-1016` computes dep status and appends exactly one warning only when `dep_status == "blocked"` and `active_ids` is non-empty. | `serve/kanban/tests/test_agent_view_start_work_1526.py:168`, `serve/kanban/tests/test_agent_view_start_work_1526.py:188`, `serve/kanban/tests/test_agent_view_start_work_1526.py:208`, `serve/kanban/tests/test_agent_view_start_work_1526.py:226` assert exact string, ordered multi-id formatting, single-entry shape, and exclusion of archived-completed deps. | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:652-681` maps `deprecated`/`duplicate` to redirect and `completed` to ok; `serve/kanban/src/owlbear_kanban/agent_view.py:1010` only emits guidance for `blocked`. | `serve/kanban/tests/test_agent_view_start_work_1526.py:256`, `serve/kanban/tests/test_agent_view_start_work_1526.py:272`, `serve/kanban/tests/test_agent_view_start_work_1526.py:295`, `serve/kanban/tests/test_agent_view_start_work_1526.py:321` assert `guidance == []` for no deps, completed dep, deprecated dep, and duplicate dep. | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/agent_view.py:996` catches `(FileNotFoundError, CorruptionError, ValueError, KeyError)` and continues; `serve/kanban/src/owlbear_kanban/agent_view.py:1010` warns only when surviving `active_ids` remain. | `serve/kanban/tests/test_agent_view_start_work_1526.py:348`, `serve/kanban/tests/test_agent_view_start_work_1526.py:371`, `serve/kanban/tests/test_agent_view_start_work_1526.py:402`, `serve/kanban/tests/test_agent_view_start_work_1526.py:431`, `serve/kanban/tests/test_agent_view_start_work_1526.py:462` prove no exception propagation, valid `SingleTaskResponse`, and conservative no-guidance when all lookups fail. `tests/test_start_work_dep_guidance_1526.py:333` provides the direct mixed-case proof that a failing dep is skipped while a surviving active dep still triggers guidance. | PASS |

## Observations
- The task body's AC coverage table names only `serve/kanban/tests/test_agent_view_start_work_1526.py`, but the strongest explicit AC3 continuation proof currently lives in `tests/test_start_work_dep_guidance_1526.py:333`. The pass stands because the executed proof packet covers the behavior, but future notes should either reference that adjacent proof or consolidate the duplicated task-scoped suites.
- quality-runner reported `owlbear_kanban.agent_view` coverage at 11%. That is not blocking here because this is a test-only review targeting the `start_work()` dependency-guidance branch inside a large module; branch-level AC proof was sufficient.
2026-05-13T14:01:31+00:00
## Docs Gate

### Checklist

**Item 1 — README Verification** (`serve/kanban/README.md`)
- Changed files: `serve/kanban/tests/test_agent_view_start_work_1526.py`, `tests/test_start_work_dep_guidance_1526.py` (test-only; no new public API introduced by this task)
- Layer 1 (grep): No symbols/flags/commands added or removed by this task. No task-caused drift detected.
- Layer 2 (LLM editorial): `start_work(task_id)` entry accurate for claim semantics. The `guidance` field in `SingleTaskResponse` (implemented before this task) was undocumented — pre-existing gap. TODO marker added after the KanbanEngine methods table.
- File updated: `serve/kanban/README.md` — TODO marker inserted (pre-existing gap, gate passes).

**Item 2 — External Attribution**: N/A — test-writing task; no external sources used.

**Item 3 — Research Doc**: N/A — no research artifact for this task.

**Item 4 — Deletion Detection**: N/A — no files deleted; two test files added.

### Files Updated
- `serve/kanban/README.md`: added `> **TODO:** missing — document guidance field...` after KanbanEngine methods table.

### Scratch Cleanup
No `.owlbear/scratch/1526-*` files found — nothing to clean.
2026-05-13T14:09:49+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4550 passed, 19 failed (pre-existing), 5 collection errors (timeouts in cockpit PDS compat), ruff clean
- 19 failures in unrelated domains: cockpit_view (5), ideation_diagram (1), server (2), engine_accessor_migration (8), end_work_success (1) — none in kanban start_work guidance domain
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS — all 3 commits touch only `serve/kanban/tests/test_agent_view_start_work_1526.py` and `tests/test_start_work_dep_guidance_1526.py`
- purpose match: PASS — test-only task delivering unit tests for dep-status guidance in start_work(), matching stated AC1-AC3
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
- AC specificity: excellent — exact string assertions, comma-separated ID format, explicit exception type enumeration, clear distinction from manual blocked field
- Edge case coverage: strong — redirect deps (deprecated/duplicate) explicitly required after cycle 2 refinement; all-fail conservative behavior specified
- Design direction: AC refinement in cycle 2 (adding redirect branch coverage) was responsive and precise

### Commit Integrity
- upstream commit presence: PASS — 523c28d7 (test-writer, main suite), 86de7a7f (retry tests), abebfd9a (RED-phase tests)
- kanban commit packaging: pending (this archival)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive