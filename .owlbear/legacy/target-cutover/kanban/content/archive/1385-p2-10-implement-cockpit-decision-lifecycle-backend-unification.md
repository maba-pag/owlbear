---
id: 1385
title: 'P2-10: Implement Cockpit decision lifecycle backend unification'
status: archived
priority: medium
created: 2026-05-06T01:04:45.316826+00:00
updated: 2026-05-07T11:43:15.107196+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-api
- type:fix
- backend
- decisions
- lifecycle
parent: 1363
depends_on:
- 1384
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Unify Cockpit decision resolution with the canonical kanban decision lifecycle.

## Problem Evidence
- Cockpit routes manually parse and rewrite decision files while canonical lifecycle logic lives in owlbear_kanban.decisions.
- Cockpit resolve writes a response but does not immediately append the summary to the task, move the decision request to resolved, or unblock approved/rejected tasks.
- The GUI can therefore make resolution appear incomplete until later background lifecycle processing.

## Acceptance Criteria
- Cockpit decision resolution reuses or promotes shared canonical decision lifecycle helpers instead of duplicating parser/writer behavior where feasible.
- Approved and rejected resolutions immediately append the summary, move the decision request to resolved, unblock the task, and return predictable response data.
- Needs-info resolution appends the summary and moves the decision request to resolved while leaving the task blocked, matching canonical semantics.
- Already-resolved, unknown, malformed, and duplicate-response cases return the backend error envelope from #1371 with correct status codes.
- The implementation satisfies #1384 without changing unrelated decision lifecycle semantics.

## Scope
- In scope: Cockpit backend decision resolution route behavior and shared lifecycle integration.
- Out of scope: frontend decision viewport, task-detail conflict workflows, scanner/cache/SSE invalidation, and unrelated decision-system redesign.

## Counterpart
Test task: #1384.

[[2026-05-07]]


## Architecture Review

### Problem Evidence Correction
The original problem evidence is stale. The cockpit route currently implements all lifecycle side effects correctly (file move, task unblock, summary append — matching #1384 assertions). The actual problem is **code duplication**: `_parse_dr` and `_canonical_summary` are reimplemented in the cockpit module nearly identically to their counterparts in `owlbear_kanban.decisions`. This creates drift risk and violates DRY.

### Refined Acceptance Criteria
The original AC is replaced by the following:

- [ ] `routes/decisions.py` imports DR file parsing from `owlbear_kanban.decisions` (promoted to public API) instead of maintaining a local `_parse_dr` implementation. (td:1)
- [ ] Task summary formatting uses the shared function from `owlbear_kanban.decisions` instead of a local `_canonical_summary`. (td:1)
- [ ] `owlbear_kanban.decisions` exposes the shared helpers as public API (rename from underscore-prefix or create thin public wrappers). (td:1)
- [ ] Cockpit-specific HTTP concerns remain in the cockpit module: decision ID validation (`_validate_decision_id`), `resolved_by` marker writes, duplicate-response classification (`resolved_by == "cockpit-api"` guard), HTTP error mapping, and `_extract_title` for the list endpoint. (td:1)
- [ ] Error format contract preserved per #1384/#1371: already-resolved → 409 with domain envelope `{code, message}`; duplicate-response → 404 with FastAPI `{detail}`; unknown ID → 404 `{detail}`; malformed ID → 422 `{detail}`. (td:1)
- [ ] All tests in `tests/test_cockpit_decisions_api_1384.py` pass without modification. (td:1)
- [ ] All tests in `tests/test_decisions_1181.py` pass without modification. (td:1)

### Builder Guidance
- **Boundary principle:** The cockpit route is a thin HTTP adapter with cockpit-specific metadata (`resolved_by`, duplicate detection). The kanban module owns domain logic (file parsing, summary format, lifecycle effects). The `_append_response_section` and `_rewrite_response` helpers handle DR file mutation during resolution — these may stay in cockpit if they serve only the HTTP-triggered resolution flow, or move to kanban if batch sweep would benefit.
- **Scope note:** `_parse_dr` is used by both `resolve_decision` and `list_pending_decisions` in the same file. Sharing the parser naturally covers both call sites without expanding scope.
- **Do NOT refactor `resolve_pending_drs`** (batch sweep) or change its semantics. This task is about sharing low-level helpers, not redesigning the batch lifecycle.
- **Existing consumers of kanban.decisions:** `mcp-kanban/server.py` calls `create_dr`; `agent_view.py` calls `resolve_pending_drs`. New public helpers must not break these.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Eliminate parser/summary duplication — one concern |
| Interface clarity | PASS (after refinement) | Each AC line is code-review verifiable |
| Dependency correctness | PASS | #1384 done (archived); #1371 envelope exists |
| Module layering | PASS | cockpit → kanban (correct direction, already exists) |
| TDD compliance | PASS | #1384 tests exist as regression guards |
| KISS/YAGNI | PASS | Removes duplication, no speculative features |
| Premise challenge | PASS | Duplication is real and measurable (near-identical _parse_dr in both modules) |
| Pattern consistency | PASS | Follows existing cross-package import pattern (cockpit already imports from owlbear_kanban.errors) |
| Security surface | PASS | No new user-input boundaries; existing validation preserved |
| Single domain | PASS | Cockpit API + shared domain helpers — one logical change |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| New public kanban helper | Signature mismatch with cockpit caller | TypeError at import/call time | No (startup or first-request crash) | Test-caught |
| Removed cockpit _parse_dr | Kanban helper returns different error type | ValueError vs custom | Yes (cockpit catches both) | None if mapped correctly |
| list_pending_decisions using shared parser | Kanban parser stricter than cockpit's was | ValueError for edge-case files | Existing try/except catches it | Silently skips malformed file (existing behavior) |

### Challenge Results
- Challenger: reconsider (confidence 0.41)
- Critical findings: stale problem evidence, AC4 contradiction, boundary ambiguity
- Architect response: ALL addressed. Problem evidence corrected. AC4 split into precise per-case format assertions. Boundary explicitly documented (resolved_by stays in cockpit, parse/summary shared from kanban). Scope spill addressed (parser sharing covers list endpoint naturally). Canonical debt noted as out-of-scope constraint (do not refactor resolve_pending_drs).

### Test Depth
- Max depth: 1
- Test-writer: PROCEED (structural verification tests for import delegation)

### Verdict: APPROVE
### Action Taken: Refined stale problem evidence, rewrote all AC to be precisely verifiable, added builder guidance addressing boundary ownership and scope constraints. Original AC replaced by 7 testable criteria aligned with #1384 assertions.

[[2026-05-07]]
Architecture review complete. Refined stale problem evidence (behavior already implemented — actual issue is code duplication). Rewrote 5 vague/contradictory AC lines into 7 precisely verifiable criteria aligned with #1384 test assertions and #1371 error envelope contracts. Added builder guidance on boundary ownership (cockpit keeps HTTP concerns + resolved_by; kanban owns parse/summary helpers). Challenger reconsider addressed: all 3 critical findings resolved.
[[2026-05-07]]
## Test-Writer Notes
- Test file: tests/test_cockpit_decisions_api_1385.py
- Classes: TestFromAC_PublicAPIExposure, TestFromAC_ImportDelegation, TestFromAC_CockpitBoundary, TestFromAC_ErrorFormatPreserved
- Tests per category: happy 0, edge 0, error 1, boundary 0 (structural: 6)
- Total: 7 tests, all FAIL
- ruff: clean

### AC Coverage Table

| AC | Test(s) | Failure Mode |
|----|---------|--------------|
| AC1: cockpit delegates _parse_dr to kanban | `test_cockpit_does_not_define_local_parse_dr`, `test_cockpit_retains_validate_decision_id_and_removes_local_parse_dr` | AssertionError: cockpit still defines _parse_dr |
| AC2: cockpit delegates _canonical_summary to kanban | `test_cockpit_does_not_define_local_canonical_summary`, `test_cockpit_retains_extract_title_and_removes_local_canonical_summary` | AssertionError: cockpit still defines _canonical_summary |
| AC3: kanban exposes parse_dr + canonical_summary as public API | `test_parse_dr_importable_from_kanban_decisions`, `test_canonical_summary_importable_from_kanban_decisions` | ImportError: cannot import name from owlbear_kanban.decisions |
| AC4: cockpit retains _validate_decision_id, _extract_title | `test_cockpit_retains_validate_decision_id_and_removes_local_parse_dr`, `test_cockpit_retains_extract_title_and_removes_local_canonical_summary` | Compound: positive retention + negative removal; fails on removal assertion |
| AC5: error format contract preserved (409 {code, message}) | `test_already_resolved_returns_409_domain_envelope` | ImportError on AC3 prerequisite import |
| AC6: test_cockpit_decisions_api_1384.py passes unmodified | (existing suite) | No new RED test possible for meta-AC; suite is the regression contract |
| AC7: test_decisions_1181.py passes unmodified | (existing suite) | No new RED test possible for meta-AC; suite is the regression contract |
[[2026-05-07]]
## Builder Notes
- Implementation: delegated cockpit decision parsing/summary to shared kanban helpers by changing [serve/cockpit/src/owlbear_cockpit/routes/decisions.py](serve/cockpit/src/owlbear_cockpit/routes/decisions.py) and [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py).
- Fixes applied:
  - Promoted `parse_dr` as a public helper in kanban decisions module (replacing private `_parse_dr` internal usage).
  - Added public `canonical_summary(response, body)` in kanban decisions module.
  - Updated kanban internal summary append helper to call `canonical_summary`.
  - Removed cockpit-local `_parse_dr` and `_canonical_summary` implementations and imported shared helpers from `owlbear_kanban.decisions`.
  - Kept cockpit-specific HTTP concerns untouched (`_validate_decision_id`, `_extract_title`, error mapping, duplicate-response handling).
- Tests (RED -> GREEN):
  - quality-runner scoped RED on [tests/test_cockpit_decisions_api_1385.py](tests/test_cockpit_decisions_api_1385.py): 0 passed / 7 failed.
  - quality-runner scoped GREEN on [tests/test_cockpit_decisions_api_1385.py](tests/test_cockpit_decisions_api_1385.py): 7 passed / 0 failed.
- Regression checks:
  - quality-runner on [tests/test_cockpit_decisions_api_1384.py](tests/test_cockpit_decisions_api_1384.py): passed.
  - [tests/test_decisions_1181.py](tests/test_decisions_1181.py): 1 pre-existing failure remained (`test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` expecting `_move_with_collision_suffix` symbol). This same failure was present in pre-edit baseline and is unchanged by this task.
- Coverage evidence:
  - `owlbear_kanban.decisions`: 98% in regression-scoped run.
  - `owlbear_cockpit.routes.decisions`: 72% in regression-scoped run.
- Lint: clean (ruff via quality-runner).
- Commit: `52191e2d` — feat: unify cockpit decision helper delegation (#1385, builder)

### Post-task Reflection
- Primary risk was accidental behavior drift while removing duplicate helpers; mitigated by preserving cockpit-only HTTP concerns and reusing existing control flow.
- Shared helper promotion was the smallest change to satisfy AC1-AC4 without touching batch lifecycle semantics.
- Validation surfaced an unrelated existing regression in [tests/test_decisions_1181.py](tests/test_decisions_1181.py); explicitly baselined before edits to confirm no new breakage.
- Task-scoped proof is strong (7/7 -> green), but broader module coverage for cockpit decisions remains below 90% in the selected scoped verification set.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped run:
  - `tests/test_cockpit_decisions_api_1385.py`: 7 passed, 0 failed
  - `tests/test_cockpit_decisions_api_1384.py`: 23 passed, 0 failed
  - `tests/test_decisions_1181.py`: 15 passed, 1 failed
- Failing regression: `tests/test_decisions_1181.py::TestFromAC_ResolvePendingDrs::test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry`
- Failure summary: `AttributeError: <module 'owlbear_kanban.decisions'> does not have the attribute '_move_with_collision_suffix'`

### Lint Results
- `ruff` clean on:
  - `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
  - `serve/kanban/src/owlbear_kanban/decisions.py`
  - `tests/test_cockpit_decisions_api_1385.py`

### Coverage Data
- `owlbear_kanban.decisions`: 98%
- `owlbear_cockpit.routes.decisions`: 72% overall
- Coverage note: the 72% module figure is informational here. The changed helper-delegation lines are directly exercised by the task-owned suite and the #1384 regression suite; the missed lines are broader route branches outside the touched surface.

### Source Review
- Cockpit now imports shared helpers from `owlbear_kanban.decisions` at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:16`.
- Cockpit keeps HTTP-specific concerns local: `_extract_title` at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:36`, `_validate_decision_id` at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:69`, duplicate-response classification at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:134-140`, and `resolved_by` write at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:171`.
- Cockpit uses the shared summary helper when appending task summaries at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:177` and preserves unblock behavior at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:179`.
- Kanban now exposes `parse_dr` at `serve/kanban/src/owlbear_kanban/decisions.py:36` and `canonical_summary` at `serve/kanban/src/owlbear_kanban/decisions.py:63`, with internal reuse via `_append_summary` at `serve/kanban/src/owlbear_kanban/decisions.py:76` and `resolve_pending_drs` at `serve/kanban/src/owlbear_kanban/decisions.py:168`.
- No security findings in the reviewed change surface. No diagnostics found in the changed files.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: cockpit delegates DR parsing to kanban | `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:16,85,125,150` import/call sites use `parse_dr`; task suite green | `tests/test_cockpit_decisions_api_1385.py:190` | PASS |
| AC2: cockpit delegates canonical summary formatting to kanban | `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:16,177` uses `canonical_summary`; `serve/kanban/src/owlbear_kanban/decisions.py:63,76` defines/reuses it | `tests/test_cockpit_decisions_api_1385.py:203` | PASS |
| AC3: kanban exposes shared helpers as public API | Public functions exist at `serve/kanban/src/owlbear_kanban/decisions.py:36,63`; import assertions in task suite pass | `tests/test_cockpit_decisions_api_1385.py:171,179` | PASS |
| AC4: cockpit-specific HTTP concerns remain local | `_extract_title` and `_validate_decision_id` remain local at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:36,69`; duplicate-response guard still local at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:134-140` | `tests/test_cockpit_decisions_api_1385.py:225,243` | PASS |
| AC5: error format contract preserved | 422 malformed-id at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:72`; malformed-file 422 at `:127,156`; duplicate-response 404 at `:134-135`; already-resolved domain error at `:140,163`; task suite and #1384 regression suite both green | `tests/test_cockpit_decisions_api_1385.py:270`; `tests/test_cockpit_decisions_api_1384.py` | PASS |
| AC6: `tests/test_cockpit_decisions_api_1384.py` passes unmodified | quality-runner: 23 passed, 0 failed | `tests/test_cockpit_decisions_api_1384.py` | PASS |
| AC7: `tests/test_decisions_1181.py` passes unmodified | quality-runner: 15 passed, 1 failed. Failing test at `tests/test_decisions_1181.py:464` explicitly targets `resolve_pending_drs` and patches `owlbear_kanban.decisions._move_with_collision_suffix` at `tests/test_decisions_1181.py:480`. The task scope explicitly says `Do NOT refactor resolve_pending_drs` at `.owlbear/kanban/tasks/1385-p2-10-implement-cockpit-decision-lifecycle-backend-unification.md:72`. | `tests/test_decisions_1181.py:464,480` | FAIL |

### Test Quality / Integrity Assessment
- The task-owned `TestFromAC_*` suite is strong enough for AC1-AC5: it uses importability assertions, explicit absence checks for local helper duplication, and exact status/envelope assertions.
- No weakened task assertions were observed in the live test file.
- Limitation: I could not diff the test-writer commit against the builder commit, so `TestFromAC_*` immutability is lower-confidence than normal.

### Deductions
- `-0.08` AC7 is unmet by an existing durable-suite failure that targets an out-of-scope `resolve_pending_drs` path.
- `-0.02` Dirty-tree contamination check could not be completed because `git status --porcelain` was unavailable from this tool surface.
- `-0.01` Test immutability could not be proven via commit diff; assessment is based on live file inspection plus task history only.

### Verdict
- FAIL
- Confidence: 0.89
- Routing: `backlog`
- Reason: the implementation satisfies the helper-delegation contract (AC1-AC6), but AC7 currently requires a green durable suite whose remaining failure is tied to `resolve_pending_drs`, a codepath the refined task scope explicitly forbids changing. That is an AC/scope-quality problem, not a builder-local implementation defect.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine or replace AC7 so this task is gated by regression evidence that matches the helper-delegation scope, or explicitly spin out the `resolve_pending_drs` durability failure as a separate dependency/task. | `.owlbear/kanban/tasks/1385-p2-10-implement-cockpit-decision-lifecycle-backend-unification.md`, `tests/test_decisions_1181.py` | AC7 at task file line 67 conflicts with out-of-scope guard at line 72; failing durable-suite test targets `resolve_pending_drs` at `tests/test_decisions_1181.py:464,480`. |
[[2026-05-07]]

## Architecture Review (Cycle 2)

### Reviewer Return Reason
AC7 required all tests in `test_decisions_1181.py` to pass, but `test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` fails with `AttributeError: module does not have attribute '_move_with_collision_suffix'`. This is a pre-existing defect (test targets unimplemented atomicity in `resolve_pending_drs`) confirmed unrelated to helper delegation.

### AC7 Refinement
Original AC7: "All tests in `tests/test_decisions_1181.py` pass without modification."
Refined AC7: "All tests in `tests/test_decisions_1181.py` pass without modification, excluding the known pre-existing failure `test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` (which targets unimplemented `_move_with_collision_suffix` in `resolve_pending_drs` — explicitly out-of-scope per builder guidance). (td:1)"

### Verdict
APPROVE — AC/scope contradiction resolved. The implementation satisfies AC1–AC6 with direct evidence, and AC7 is now properly scoped to the touched surface. The pre-existing atomicity defect in `resolve_pending_drs` is a separate concern (existing task debt, not a regression).

### Action
Advance to `review` for re-verification with corrected AC7.
[[2026-05-07]]
Cycle 2 architecture review: refined AC7 to exclude known pre-existing failure (`test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` patches non-existent `_move_with_collision_suffix` — pre-dates this task). Implementation evidence from cycle 1 is valid for AC1–AC6. Advancing to review for re-verification with corrected gate.
[[2026-05-07]]
## Test-Writer Notes
- Retry cycle: reviewer Required Follow-up was for the architect (AC7 scope refinement), not for new tests.
- Architect resolved it in Cycle 2 Architecture Review: refined AC7 to exclude pre-existing failure `test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` (pre-dates this task, targets unimplemented `_move_with_collision_suffix` in out-of-scope `resolve_pending_drs`).
- No new tests added: the existing 7 tests in `tests/test_cockpit_decisions_api_1385.py` remain valid and unchanged; they cover AC1–AC5 directly and AC6/AC7 are meta-ACs covered by running the existing regression suites.
- Builder: implementation is already complete (commit `52191e2d`). No code changes needed — pass through to review.
[[2026-05-07]]
## Builder Notes
- Implementation status: no additional code changes in this cycle; using existing builder implementation/commit `52191e2d` for verification handoff.
- Fresh quality-runner evidence (this cycle):
  - `tests/test_cockpit_decisions_api_1385.py`: 7 passed, 0 failed
  - `tests/test_cockpit_decisions_api_1384.py`: 23 passed, 0 failed
  - `tests/test_decisions_1181.py`: 15 passed, 1 failed
- Known failure remains pre-existing and out-of-scope: `TestFromAC_ResolvePendingDrs::test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` (`AttributeError` on missing `_move_with_collision_suffix` patch target).
- AC7 handling: conforms to Cycle 2 architecture refinement (exclude the known pre-existing `test_ac8_*` failure from gate semantics).
- Lint: `ruff` clean for touched/task-owned files:
  - `serve/kanban/src/owlbear_kanban/decisions.py`
  - `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
  - `tests/test_cockpit_decisions_api_1385.py`
- Coverage evidence from quality-runner:
  - `owlbear_kanban.decisions`: 98%
  - `owlbear_cockpit.routes.decisions`: 72% (informational; task-owned delegation paths covered by passing suites)
- Evidence summary:
  - AC1-AC6 remain satisfied by passing task and regression suites.
  - AC7 is satisfied under refined scope (excluding known pre-existing out-of-scope failure in `resolve_pending_drs`).

### Post-task Reflection
- Validation was straightforward because implementation was already in place and previously committed.
- Main risk was false-negative gating from the persistent durable-suite failure; mitigated by applying architect-refined AC7 scope exactly.
- Re-running quality-runner in-cycle provided fresh, canonical evidence without changing code.
- No additional implementation drift introduced in this pass.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped run (task contract + durable suite gate): 45 passed, 1 failed, 0 skipped.
- Passing task-owned/regression suites in that run: `tests/test_cockpit_decisions_api_1385.py`, `tests/test_cockpit_decisions_api_1384.py`.
- The single failing test in that run was `tests/test_decisions_1181.py::TestFromAC_ResolvePendingDrs::test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` with `AttributeError` on patch target `owlbear_kanban.decisions._move_with_collision_suffix`.
- quality-runner adjacent envelope regression run: 52 passed, 0 failed, 0 skipped across `tests/test_cockpit_decisions_api_1385.py`, `tests/test_cockpit_decisions_api_1384.py`, `tests/test_cockpit_decisions_api_1189.py`, and `tests/test_cockpit_error_envelope_1371.py`.
- The adjacent run provides fresh live proof for the unknown-ID 404 and malformed-ID 422 envelope branches named in AC5.

### Lint Results
- `ruff` clean on:
  - `serve/kanban/src/owlbear_kanban/decisions.py`
  - `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
  - `tests/test_cockpit_decisions_api_1385.py`
- VS Code diagnostics: no errors in the changed source files or the task-owned test file.

### Coverage Data
- Scoped run including `tests/test_decisions_1181.py`: `owlbear_kanban.decisions` 98%, `owlbear_cockpit.routes.decisions` 72%.
- Adjacent envelope regression run: `owlbear_cockpit.routes.decisions` 93%, `owlbear_kanban.decisions` 32%.
- Coverage interpretation: the lower alternate percentages are suite-selection artifacts. The changed cockpit route surface clears the 90% bar under the adjacent regression set, and the shared kanban helper surface clears it when the durable `resolve_pending_drs` suite is included. The changed delegation lines are directly exercised by the green task suite plus the green adjacent regression suites.

### Source Review
- Cockpit imports shared helpers from `owlbear_kanban.decisions` and delegates parsing at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:15`, `:85`, `:125`, `:150`.
- Cockpit keeps HTTP-specific concerns local: `_extract_title` at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:36`, `_validate_decision_id` at `:69`, duplicate-response classification at `:134-135`, and `resolved_by` write at `:171`.
- Cockpit appends task summaries through the shared helper at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:177`.
- Kanban exposes the shared public API at `serve/kanban/src/owlbear_kanban/decisions.py:36` (`parse_dr`) and `:63` (`canonical_summary`), with internal reuse via `_append_summary` at `:72-76`.
- Workspace usage sweep shows no unexpected caller expansion: `parse_dr` is used only by `owlbear_kanban.decisions` and the cockpit route; `canonical_summary` is used only by `_append_summary` and the cockpit route.
- No security findings in the changed surface. Decision IDs remain allowlist-validated before filesystem access.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: `routes/decisions.py` imports DR file parsing from `owlbear_kanban.decisions` instead of maintaining a local `_parse_dr` implementation. | Cockpit delegates through `parse_dr` at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:85`, `:125`, `:150`; no local `_parse_dr` definition remains in the file. | `tests/test_cockpit_decisions_api_1385.py:190`, `:225` | PASS |
| AC2: Task summary formatting uses the shared function from `owlbear_kanban.decisions` instead of a local `_canonical_summary`. | Cockpit appends summaries via `canonical_summary` at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:177`; shared helper defined at `serve/kanban/src/owlbear_kanban/decisions.py:63`; no local `_canonical_summary` remains. | `tests/test_cockpit_decisions_api_1385.py:203`, `:243` | PASS |
| AC3: `owlbear_kanban.decisions` exposes the shared helpers as public API. | Public functions exist at `serve/kanban/src/owlbear_kanban/decisions.py:36` and `:63`; importability assertions are green. | `tests/test_cockpit_decisions_api_1385.py:165`, `:173` | PASS |
| AC4: Cockpit-specific HTTP concerns remain in the cockpit module. | `_extract_title` remains local at `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:36`; `_validate_decision_id` remains local at `:69`; duplicate-response guard remains local at `:134-135`; `resolved_by` write remains local at `:171`. | `tests/test_cockpit_decisions_api_1385.py:225`, `:243` | PASS |
| AC5: Error format contract preserved per #1384/#1371. | Already-resolved 409 `{code,message}` proven by `tests/test_cockpit_decisions_api_1385.py:270` and `tests/test_cockpit_decisions_api_1384.py:546-563`; duplicate-response 404 `{detail}` proven by `tests/test_cockpit_decisions_api_1384.py:648-669`; unknown-ID 404 proven by `tests/test_cockpit_decisions_api_1189.py:308-317`; malformed-ID 422 `{detail}` proven by `tests/test_cockpit_error_envelope_1371.py:293-311`. Adjacent quality-runner regression run was fully green. | `tests/test_cockpit_decisions_api_1385.py:270`; `tests/test_cockpit_decisions_api_1384.py:648`; `tests/test_cockpit_decisions_api_1189.py:308`; `tests/test_cockpit_error_envelope_1371.py:293` | PASS |
| AC6: All tests in `tests/test_cockpit_decisions_api_1384.py` pass without modification. | quality-runner included the file in both review runs with no failures attributed to it. | `tests/test_cockpit_decisions_api_1384.py` | PASS |
| AC7 (refined): All tests in `tests/test_decisions_1181.py` pass without modification, excluding the known pre-existing `test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` failure. | Refined AC7 is binding at `.owlbear/kanban/tasks/1385-p2-10-implement-cockpit-decision-lifecycle-backend-unification.md:223`; the same task file also keeps `resolve_pending_drs` out of scope at line 72. The only live failure is the excluded `test_ac8_*` case, which targets patch string `owlbear_kanban.decisions._move_with_collision_suffix` at `tests/test_decisions_1181.py:480`; that symbol is absent from `serve/kanban/src/owlbear_kanban/decisions.py`, matching the architecture note’s carve-out. No additional failures were observed. | `tests/test_decisions_1181.py:467`, `:480`; `.owlbear/kanban/tasks/1385-p2-10-implement-cockpit-decision-lifecycle-backend-unification.md:223` | PASS |

### Test Quality / Integrity Assessment
- The task-owned `TestFromAC_*` suite is strong enough for AC1-AC5: the assertions are discriminating and would fail on the intended regressions (missing public exports, retained local helpers, wrong error-envelope shape).
- No weakened task assertions were observed in the live `tests/test_cockpit_decisions_api_1385.py` file.
- Residual limitation: test immutability could not be proven with a commit diff from this tool surface; commit presence for builder hash `52191e2d` was confirmed from `.git/logs/HEAD`.

### Deductions
- `-0.02` Dirty-tree contamination check could not be executed from this tool surface.
- `-0.02` `TestFromAC_*` immutability / exact changed-file ownership could not be proven with `git diff`; assessment relies on live file inspection, task history, and commit-log presence.

### Verdict
- PASS
- Confidence: 0.94
- Routing: `docs`
- Reason: the cycle-2 architecture refinement resolves the earlier AC7 scope defect, and the current implementation fully satisfies AC1-AC7 under that refined contract. The shared helper promotion is in place, cockpit-only HTTP concerns remain local, all named error-envelope branches have fresh live regression proof, and no new security or quality defects were found.

### Action
- Advanced to `docs`.
[[2026-05-07]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified / No change | `serve/cockpit/README.md` Decisions API section describes endpoint *behavior* (unchanged). The refactor only changed internal helper delegation, not HTTP contracts or endpoint semantics. Accurate as-is. |
| 2 | Module docstrings | Yes | Verified / No change | All public functions in `serve/kanban/src/owlbear_kanban/decisions.py` (`parse_dr`, `canonical_summary`, `create_dr`, `resolve_pending_drs`) have accurate docstrings. All functions in `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` (`_extract_title`, `_append_response_section`, `_rewrite_response`, `_validate_decision_id`, `list_pending_decisions`, `resolve_decision`) have accurate docstrings. No updates needed. |
| 3 | External attribution | No | N/A | Internal refactor; no external patterns used. |
| 4 | Research doc | No | N/A | No research phase for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` (describes `serve/cockpit/src/**`) and `share/diagrams/kanban.excalidraw` (describes `serve/kanban/src/**`) both matched. Footers updated to "Last verified: 2026-05-07 (c61b2907)". Commit: `fe381774`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted; refactor only (removed private helpers, promoted to public). |

### Scope Classification
- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` → IN-scope (Python docstrings)
- `serve/kanban/src/owlbear_kanban/decisions.py` → IN-scope (Python docstrings)
- `tests/test_cockpit_decisions_api_1385.py` → OUT-scope (test file)

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer updated (2026-05-07, c61b2907)
- `share/diagrams/kanban.excalidraw` — footer updated (2026-05-07, c61b2907)

### Scratch Files
None found for task 1385.
[[2026-05-07]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: cockpit delegates DR parsing to kanban | `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:15` imports `parse_dr` from `owlbear_kanban.decisions`; no local `_parse_dr` in file; task suite green 7/7 | PASS |
| AC2: cockpit delegates canonical summary to kanban | `serve/cockpit/src/owlbear_cockpit/routes/decisions.py:15` imports `canonical_summary`; no local `_canonical_summary` in file | PASS |
| AC3: kanban exposes shared helpers as public API | `parse_dr` at `serve/kanban/src/owlbear_kanban/decisions.py:36`, `canonical_summary` at `:63` (spot-checked, confirmed public) | PASS |
| AC4: cockpit-specific HTTP concerns remain local | `_extract_title`, `_validate_decision_id`, duplicate-response guard, `resolved_by` write all remain in cockpit module (reviewer mapped lines, spot-check confirmed) | PASS |
| AC5: error format contract preserved | Task suite + 1384 regression suite + adjacent envelope suites all green (reviewer ran 52 tests across 4 envelope files) | PASS |
| AC6: test_cockpit_decisions_api_1384.py passes | 23/23 passed (confirmed in my scoped run) | PASS |
| AC7 (refined): test_decisions_1181.py passes excluding pre-existing test_ac8 | 15/16 passed; sole failure is the carved-out `test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry` (targets unimplemented `_move_with_collision_suffix`) | PASS |

### Test Results
- pytest (task-scoped): 45 passed, 1 failed (known pre-existing, excluded by refined AC7)
- pytest (full suite): 221 failures, 0 in task scope or caused by this task
- Decisions-related "failures" confirmed pre-existing: test_decisions_1218.py (RED phase for #1218), test_decisions_1181.py::test_ac8 (unimplemented atomicity)
- ruff: clean on task-scoped files
- vitest (frontend): 992 passed, 0 failed

### Commit Integrity
- Builder: `52191e2d feat: unify cockpit decision helper delegation (#1385, builder)` confirmed
- Doc-writer: `fe381774 docs: update diagram footers for decision helper delegation (#1385, doc-writer)` confirmed
- Working tree: clean for all task-scoped files

### Architect Quality: 4/5
Initial AC7 had a scope contradiction (required all durable tests to pass while explicitly forbidding changes to `resolve_pending_drs`). Caught by cycle 1 reviewer, properly resolved by cycle 2 architect refinement. Post-refinement AC is precise, testable, and complete. Builder guidance is excellent (boundary ownership, scope constraints, consumer awareness).

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (no deduction)
- Lint violations in scope: 0 (no deduction)
- AC quality 4/5 (above threshold): no deduction
- Reviewer evidence: present and detailed (no deduction)
- Full-suite failures in task scope: 0 (no deduction)
- Minor: -0.02 for high background failure count (221) reducing cross-task regression signal fidelity

### Confidence: 0.98
### Action: archive