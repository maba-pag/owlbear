---
id: 1868
title: 'Kanban: add resolve_decision() to decisions module with unit tests'
status: done
priority: important
created: 2026-05-25T00:20:38.487099+02:00
updated: 2026-05-25T04:21:23.395027+02:00
tags:
  - scope:kanban
  - boundary-audit
parent: 1865
depends_on: []
ac:
  - resolve_decision(path, response, engine, *, notes=None, 
    resolved_by='unknown') is importable from owlbear_kanban.decisions
  - Raises ConcurrencyError('ERR_STALE', ...) when parse_dr(path) yields a 
    response that is not 'pending'
  - 'Updates frontmatter: sets response and resolved_by fields to the provided argument
    values'
  - 'Appends a ## Response markdown section to the DR body containing the response
    value'
  - 'When notes is not None, the notes text appears within the ## Response section
    (between the ## Response heading and any subsequent heading or EOF)'
  - Persists rewritten frontmatter + body to the file at path
  - A single engine.edit_task call carries both task_id (from DR frontmatter) 
    and append_body=canonical_summary(response, original_body)
  - When response is 'approved' or 'rejected', calls engine.edit_task(task_id, 
    blocked=False) to unblock the task
  - When response is 'needs-info', does NOT call engine.edit_task(task_id, 
    blocked=False)
  - FileNotFoundError from engine.edit_task() is caught internally (not 
    propagated) — preserves legacy contract for DRs referencing tasks outside 
    this engine
  - Returns the resolved Path from move_to_resolved(path, path.parent.parent / 
    'resolved')
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Add `resolve_decision(path, response, engine, *, notes=None, resolved_by="unknown")` to `owlbear_kanban.decisions`. The function encapsulates: parse DR → validate pending → update frontmatter (response, resolved_by) → append response section to body → persist rewrite → append canonical_summary to task → unblock task (if approved/rejected) → move_to_resolved(). Raises ConcurrencyError("ERR_STALE") if not pending. Returns resolved Path.

**FileNotFoundError contract:** `engine.edit_task()` may raise FileNotFoundError when DRs reference tasks outside this engine (legacy callers). The function MUST catch this internally — do NOT propagate. This preserves current Cockpit behavior (see parent #1865 architecture notes and `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` line 218).

**Implementation guidance:**
- `resolved_dir` derivable from `path.parent.parent / "resolved"` (pending lives in `decisions/pending/`)
- `_rewrite_response` helper logic currently in Cockpit — extract to kanban module (private)
- `_append_response_section` helper logic currently in Cockpit — extract to kanban module (private)
- Existing `_append_summary` helper can be reused for the task-body append step
- Difference from `resolve_pending_drs`: single-file, includes body-section append, raises on stale (batch skips both)

[[2026-05-25T00:58:02+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single function extraction with clear boundary |
| Interface clarity | PASS | Signature, raises, return type all specified in AC |
| Dependency correctness | PASS | No depends_on needed; building blocks (parse_dr, move_to_resolved, canonical_summary, ConcurrencyError) all exist in-module |
| Module layering | PASS | Domain logic moves from cockpit.routes (HTTP) → kanban.decisions (domain) — correct direction |
| TDD compliance | PASS | Task scoped for unit tests; behavioral proof bundle assigned |
| KISS/YAGNI | PASS | Extracts existing logic, no new abstractions; private helpers reuse existing patterns |
| Premise challenge | PASS | Boundary audit identified real leak; symmetric with create_dr() |
| Pattern consistency | PASS | Follows DecisionEngine protocol, ConcurrencyError(ERR_STALE) pattern, move_to_resolved reuse |
| Security surface | PASS | Internal refactor, no new system boundaries |
| Single domain | PASS | scope:kanban only — owlbear_kanban.decisions module |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| parse_dr(path) | File missing/corrupt | FileNotFoundError/ValueError | Propagated (caller's concern) | Caller handles |
| engine.edit_task (summary) | Task not in engine | FileNotFoundError | Caught internally | None — resolution completes |
| engine.edit_task (unblock) | Task not in engine | FileNotFoundError | Caught internally | None — resolution completes |
| move_to_resolved | Target dir creation | OSError | Propagated | Filesystem issue |

### Challenge Results
- Challenger: reconsider (confidence 0.62)
- Findings: (1) contract drift — task body said propagate FileNotFoundError while parent said swallow; (2) AC not persisted; (3) AC-1 combined importability with __all__; (4) compound AC lines
- Architect response: accepted all — rewrote task body to explicitly mandate swallow contract, removed __all__ requirement (module has none), split compound AC into 11 independently testable lines, persisted AC via edit_task

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (REFINE → APPROVE)
### Action Taken: Fixed FileNotFoundError contract contradiction, wrote 11 atomic AC lines, set proof_bundle=behavioral, advanced to todo

[[2026-05-25T01:10:04+02:00]]
## Test-Writer Notes
- Test file: tests/test_decisions_1868.py
- Classes: TestFromAC_ResolveDecision
- Tests per category: happy 9, edge 4, error 2, boundary 4
- Total: 19 tests, all FAIL (ImportError — resolve_decision does not exist yet)
- ruff: clean

AC coverage:
| AC | Test(s) |
|----|---------|
| ac1: importable | test_importable |
| ac2: ConcurrencyError(ERR_STALE) when not pending | test_raises_concurrency_error_when_already_approved, test_raises_concurrency_error_for_needs_info_response |
| ac3: frontmatter response + resolved_by | test_frontmatter_response_updated, test_frontmatter_resolved_by_default, test_frontmatter_resolved_by_custom_value |
| ac4: ## Response section appended | test_response_section_appended_to_body, test_response_section_contains_response_value |
| ac5: notes included / excluded | test_notes_included_when_provided, test_notes_not_present_when_none |
| ac6: file persisted | test_file_is_persisted_with_updated_frontmatter_and_body |
| ac7: canonical_summary appended via edit_task | test_appends_canonical_summary_to_task, test_canonical_summary_content_correct, test_edit_task_called_with_correct_task_id |
| ac8: unblock for approved/rejected | test_unblocks_task_when_approved, test_unblocks_task_when_rejected |
| ac9: no unblock for needs-info | test_no_unblock_for_needs_info |
| ac10: FileNotFoundError swallowed | test_filenotfounderror_from_append_body_not_propagated, test_filenotfounderror_from_unblock_not_propagated |
| ac11: returns resolved Path | test_returns_path_object, test_returns_path_in_resolved_dir, test_resolved_dir_created_when_absent, test_original_pending_file_removed |

[[2026-05-25T01:21:28+02:00]]
## Builder Notes
- Implementation: added resolve_decision(path, response, engine, *, notes=None, resolved_by="unknown") and private helpers _append_response_section/_rewrite_response in serve/kanban/src/owlbear_kanban/decisions.py.
- Files changed: serve/kanban/src/owlbear_kanban/decisions.py
- Behavioral flow implemented: parse DR -> pending-state guard -> frontmatter update (response/resolved_by) -> append "## Response" section (+optional notes) -> persist rewrite -> append canonical_summary to task -> unblock only for approved/rejected -> move to resolved dir and return resolved Path.
- Concurrency behavior: when DR response is already non-pending, raises ConcurrencyError with code ERR_STALE.
- Legacy compatibility: FileNotFoundError from engine.edit_task() is caught and not propagated.

Verification evidence (quality-runner):
- RED pre-check: tests/test_decisions_1868.py failed at collection with ImportError for missing resolve_decision (expected before implementation).
- GREEN scoped run: tests/test_decisions_1868.py -> 23 passed, 0 failed.
- Lint scoped run: clean=true for serve/kanban/src/owlbear_kanban/decisions.py and tests/test_decisions_1868.py.
- Coverage scoped run: module owlbear_kanban.decisions = 54% (task-scoped proof run).

Module-level durable baseline check:
- tests/test_decisions.py before change: 46 passed, 2 failed
- tests/test_decisions.py after change: 46 passed, 2 failed (same failures, unchanged)
- Existing failures:
  1) TestFromAC_ResolvePendingDrs_1181::test_ac8_move_failure_after_mutation_no_duplicate_summary_on_retry
  2) TestFromAC_ResolvePendingDrsCollision::test_ac4_collision_helper_uses_o_excl_exclusive_create_flag

Commit:
- c270ac0e

[[2026-05-25T01:44:22+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: FAIL #1868 -> todo | AC4 and AC10 proof is insufficient in the task-local tests.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | The task-local tests prove that a Response section and response value exist, but they do not prove the original DR body is preserved when the section is appended. An implementation that replaced the body instead of appending would still pass. | AC text [1868 task](.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md#L20), weak assertions [tests/test_decisions_1868.py](tests/test_decisions_1868.py#L171) and [tests/test_decisions_1868.py](tests/test_decisions_1868.py#L183), current helper preserves body at [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L77) and [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L85) | todo |
| 2 | AC10 | The FileNotFoundError tests only prove non-propagation. They do not prove that resolution still completes on that path, even though the task AC explicitly ties the swallow behavior to preserving the legacy contract. An implementation that swallowed FileNotFoundError and exited early could still pass these tests. | AC text [1868 task](.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md#L30), failure-mode context [1868 task](.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md#L73) and [1868 task](.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md#L74), weak assertions [tests/test_decisions_1868.py](tests/test_decisions_1868.py#L345) and [tests/test_decisions_1868.py](tests/test_decisions_1868.py#L355), current control flow catches then moves at [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L218) and [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L223) | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC4 proof to assert the original DR body content survives and appears before the appended Response section. | tests/test_decisions_1868.py | Finding 1 |
| 2 | test-writer | Strengthen AC10 proof to assert resolve_decision still returns a resolved path and removes the pending file when engine.edit_task raises FileNotFoundError. | tests/test_decisions_1868.py | Finding 2 |

## Observations
- Direct code review of [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L187) through [serve/kanban/src/owlbear_kanban/decisions.py](serve/kanban/src/owlbear_kanban/decisions.py#L223) found the implementation aligned with the 11 AC lines. This rejection is for proof quality, not for an observed source defect.
- Adjacent Cockpit route tests already show the missing AC4-style ordering proof pattern at [tests/test_cockpit_decisions_api.py](tests/test_cockpit_decisions_api.py#L473), [tests/test_cockpit_decisions_api.py](tests/test_cockpit_decisions_api.py#L998), and [tests/test_cockpit_decisions_api.py](tests/test_cockpit_decisions_api.py#L1011).
- Builder evidence was otherwise internally consistent: task-local green, scoped lint clean, and the durable decisions baseline remained unchanged.

[[2026-05-25T02:00:17+02:00]]
## Test-Writer Notes
- Retry: added 3 new tests to TestFromAC_ResolveDecision for reviewer gaps (AC4 and AC10).
- Test file: tests/test_decisions_1868.py
- New tests:
  - `test_original_dr_body_preserved_before_response_section` (AC4): asserts original body content survives and appears before `## Response`
  - `test_resolution_returns_resolved_path_when_edit_task_raises_fnf` (AC10): asserts function returns a resolved Path in resolved/ dir when FNF raised
  - `test_pending_file_removed_when_edit_task_raises_fnf` (AC10): asserts pending file removed even when FNF raised
- Quality-runner: 26 passed, 0 failed — all new tests GREEN against current implementation
- Builder skip: test-only retry, all tests green (Step 1b.1 — implementation already satisfies stronger assertions)
- ruff: clean
- Commit: cd3552fc

[[2026-05-25T02:30:05+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: FAIL #1868 -> backlog | AC5 and AC7 proof remains insufficient on the second review cycle.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC5 | The positive notes test only proves the note text appears somewhere in the resolved file. It does not prove the note is inside the appended `## Response` section, which the AC requires. A regression that writes notes outside that section would still pass. | AC text `.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md#L22`, test definition `tests/test_decisions_1868.py#L219`, assertion `tests/test_decisions_1868.py#L229`, current helper shape `serve/kanban/src/owlbear_kanban/decisions.py#L77` | backlog |
| 2 | AC7 | The suite proves `append_body` content on one `edit_task` call and the expected task id on some `edit_task` call, but it never proves those are the same call. A regression could append the canonical summary to the wrong task and still leave the suite green. | AC text `.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md#L24`, content proof `tests/test_decisions_1868.py#L280` and `tests/test_decisions_1868.py#L291`, separate task-id proof `tests/test_decisions_1868.py#L294` and `tests/test_decisions_1868.py#L303`, call site `serve/kanban/src/owlbear_kanban/decisions.py#L215` and `serve/kanban/src/owlbear_kanban/decisions.py#L74` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the proof contract for AC5 so the retry must assert that notes appear inside the appended `## Response` section, then re-queue task-local coverage accordingly. | `.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md`, `tests/test_decisions_1868.py` | Finding 1 |
| 2 | architect | Refine the proof contract for AC7 so the retry must assert `task_id` and `append_body=canonical_summary(...)` on the same `engine.edit_task` call, then re-queue task-local coverage accordingly. | `.owlbear/kanban/tasks/1868-kanban-add-resolve-decision-to-decisions-module-with-unit-tests.md`, `tests/test_decisions_1868.py` | Finding 2 |

## Observations
- Direct review of `serve/kanban/src/owlbear_kanban/decisions.py#L187` through `serve/kanban/src/owlbear_kanban/decisions.py#L223` still indicates the current implementation matches the intended behavior. This rejection is for proof quality, not for an observed source defect.
- The retry did close the prior AC4 and AC10 gaps by adding ordering and completion assertions in `tests/test_decisions_1868.py#L196`, `tests/test_decisions_1868.py#L381`, and `tests/test_decisions_1868.py#L398`.
- Builder and test-writer evidence remained internally consistent, so no independent quality-runner rerun was needed; the blocking issue is assertion strength, not contradictory execution evidence.

[[2026-05-25T03:12:08+02:00]]
## Architecture Review (AC Refinement Cycle 2)
### Reviewer Feedback Applied
Refined AC5 and AC7 per reviewer findings from second review cycle:

| AC | Before | After | Rationale |
|----|--------|-------|----------|
| AC5 | "includes notes text in the appended response section" | "the notes text appears within the ## Response section (between the ## Response heading and any subsequent heading or EOF)" | Test must prove structural placement, not just presence in file |
| AC7 | "Appends canonical_summary(response, body) to the linked task via engine.edit_task(task_id, append_body=...)" | "A single engine.edit_task call carries both task_id (from DR frontmatter) and append_body=canonical_summary(response, original_body)" | Test must join task_id and append_body on the same call object |

### Test-Writer Guidance
- AC5: Assert notes text appears after `## Response` line and before next `##` heading or EOF. Pattern: split resolved file at `## Response`, take that section, verify notes substring within it.
- AC7: Assert on a single `call_args` entry: `call.args[0] == task_id` AND `call.kwargs[\"append_body\"] == canonical_summary(response, original_body)` on the same mock call.
- All other AC lines remain unchanged and already have GREEN proof.

### Proof-Bundle Validation
- Final bundle: behavioral (unchanged)
- Test-writer: PROCEED (strengthen AC5/AC7 tests only)

### Verdict: REFINE → APPROVE
### Action Taken: Rewrote AC5 and AC7 for structural proof precision, advanced to todo for test-writer retry

[[2026-05-25T03:35:31+02:00]]
## Test-Writer Notes
- Retry: added 2 new tests to TestFromAC_ResolveDecision for reviewer gaps (AC5 and AC7).
- Test file: tests/test_decisions_1868.py
- New tests:
  - `test_notes_appear_within_response_section` (AC5): splits resolved file at `## Response`, finds end of section (next `##` or EOF), asserts note_text is within that slice — proves structural placement, not just file presence
  - `test_edit_task_carries_task_id_and_append_body_in_same_call` (AC7): iterates `call_args_list` looking for a single entry where `args[0] == 42` AND `kwargs["append_body"] == canonical_summary("approved", original_body)` — proves both are on the same call
- Quality-runner: 28 passed, 0 failed — all new tests GREEN against current implementation
- Builder skip: test-only retry, all tests green (Step 1b.1 — implementation already satisfies stronger assertions)
- ruff: clean
- Commit: 1a87f5d3

[[2026-05-25T03:57:22+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1868 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence reviewed first and remained internally consistent. The implementation packet reported quality-runner GREEN on tests/test_decisions_1868.py (23 passed), scoped ruff clean, and scoped coverage for owlbear_kanban.decisions at 54%. The test-only retry packet reported quality-runner GREEN on tests/test_decisions_1868.py (28 passed) and ruff clean after strengthening AC5 and AC7 proof. Retry commit 1a87f5d3 changed only tests/test_decisions_1868.py, and the scoped files tests/test_decisions_1868.py and serve/kanban/src/owlbear_kanban/decisions.py were clean at review time.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | serve/kanban/src/owlbear_kanban/decisions.py:187 | tests/test_decisions_1868.py:98 | PASS |
| 2 | serve/kanban/src/owlbear_kanban/decisions.py:200-205 | tests/test_decisions_1868.py:108; tests/test_decisions_1868.py:119 | PASS |
| 3 | serve/kanban/src/owlbear_kanban/decisions.py:208-209 | tests/test_decisions_1868.py:134; tests/test_decisions_1868.py:145; tests/test_decisions_1868.py:156 | PASS |
| 4 | serve/kanban/src/owlbear_kanban/decisions.py:77-85; serve/kanban/src/owlbear_kanban/decisions.py:210-211 | tests/test_decisions_1868.py:171; tests/test_decisions_1868.py:183; tests/test_decisions_1868.py:196 | PASS |
| 5 | serve/kanban/src/owlbear_kanban/decisions.py:79-81 | tests/test_decisions_1868.py:220; tests/test_decisions_1868.py:231; tests/test_decisions_1868.py:254 | PASS |
| 6 | serve/kanban/src/owlbear_kanban/decisions.py:89-95; serve/kanban/src/owlbear_kanban/decisions.py:211 | tests/test_decisions_1868.py:274 | PASS |
| 7 | serve/kanban/src/owlbear_kanban/decisions.py:71-74; serve/kanban/src/owlbear_kanban/decisions.py:213-215 | tests/test_decisions_1868.py:291; tests/test_decisions_1868.py:303; tests/test_decisions_1868.py:317; tests/test_decisions_1868.py:328 | PASS |
| 8 | serve/kanban/src/owlbear_kanban/decisions.py:216-217 | tests/test_decisions_1868.py:354; tests/test_decisions_1868.py:366 | PASS |
| 9 | serve/kanban/src/owlbear_kanban/decisions.py:216-217 | tests/test_decisions_1868.py:381 | PASS |
| 10 | serve/kanban/src/owlbear_kanban/decisions.py:215-223 | tests/test_decisions_1868.py:396; tests/test_decisions_1868.py:406; tests/test_decisions_1868.py:426; tests/test_decisions_1868.py:443 | PASS |
| 11 | serve/kanban/src/owlbear_kanban/decisions.py:114-128; serve/kanban/src/owlbear_kanban/decisions.py:222-223 | tests/test_decisions_1868.py:459; tests/test_decisions_1868.py:469; tests/test_decisions_1868.py:480; tests/test_decisions_1868.py:492 | PASS |

## Observations
- Adjacent Cockpit decision-route tests were not counted as proof for this PASS because task #1869 has not yet delegated the route to owlbear_kanban.decisions.resolve_decision; this verdict rests on the task-local suite plus direct code inspection.
- Challenger surfaced a broader input-shape question for markdown-heading notes. I treated that as non-blocking in this task because the extracted helper preserves the existing route's verbatim note rendering, and no in-scope AC or existing proof establishes escaped or normalized markdown-note handling as part of #1868's contract.

[[2026-05-25T04:21:23+02:00]]
## Docs Gate

### Convention Mapping
- `serve/kanban/src/owlbear_kanban/decisions.py` → `serve/kanban/README.md`
- `tests/test_decisions_1868.py` → `serve/kanban/README.md`

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A (pre-existing gap, no task-caused drift) | `decisions` module functions have never been documented in `serve/kanban/README.md`; README accurately describes the `__init__.py` public API only; `resolve_decision` follows the same undocumented pattern as `create_dr`, `parse_dr`, `resolve_pending_drs` — consistent pre-existing gap, nothing task-caused |
| 2. External Attribution | N/A — no external sources used | Builder notes describe extraction from existing Cockpit route logic only |
| 3. Research Doc | N/A — no research artifact | No research file referenced in task body |
| 4. Deletion Detection | N/A — no deletions | Only `decisions.py` was modified (function addition); no files deleted |

### Files Updated
None — no task-caused documentation drift detected.

### Scratch Cleanup
No `.owlbear/scratch/1868-*` files found.
