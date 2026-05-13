---
id: 1527
title: 'P1-02: implement dep-status guidance in start_work (AC1-AC3)'
status: archived
priority: critical
created: 2026-05-13T12:17:51.690274+00:00
updated: 2026-05-13T16:16:40.516571+00:00
tags:
  - phase-1
  - scope:kanban
  - feature
parent: 1525
depends_on:
  - 1526
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Summary

Implement dep-status guidance in `agent_view.start_work()`: before `engine.start_work()` call, iterate deps, compute dep_status, and return guidance string if blocked.

Brief: see parent #1525

## Acceptance Criteria

- AC1: `start_work()` on a dep-blocked task returns `guidance` containing exactly one string with format `"⚠️ This task has unresolved dependencies (IDs: {comma-separated ints}). Review and confirm with the user that starting this work is intentional."`
- AC2: `start_work()` on a task with `depends_on == []` OR where no dependency is active (every dep is either archived regardless of `archival_reason`, or its lookup raised an exception) returns `guidance == []`
- AC3: When `engine.show_task(dep_id)` raises any of `(FileNotFoundError, CorruptionError, ValueError, KeyError)` during dep iteration in `start_work()`: (a) no exception propagates to the caller, (b) response is a `SingleTaskResponse` with `task` field populated and task claimed, (c) when ALL dep lookups fail `guidance == []`, (d) when some lookups fail but at least one active dep remains, guidance still fires listing the active dep IDs

## Scope

- In scope: ~15 LoC inline dep iteration in `agent_view.start_work()` before `engine.start_work()` call, passing guidance to `_to_single_response()`
- Out of scope: MCP layer, schema changes, helper extraction, redirect handling

## Context

- Mirror the dep iteration pattern from `show_task()` at L214
- Use `engine._compute_dep_status()` to determine blocked status
- Pass guidance via existing `_to_single_response(task, guidance=guidance)`
- Design rationale for active_ids gate: guidance lists "unresolved dependencies" — archived deps are lifecycle-complete and not actionable; the `dep_status` field in `show_task()` already surfaces "blocked" for orchestration visibility of archived-blocked deps

Proof bundle: behavioral
2026-05-13T15:26:37+00:00
## Architecture Review (Re-review after reviewer rejection)

### Context
Reviewer correctly identified contract drift: AC2 enumerated only `completed`, `deprecated`, `duplicate` as no-guidance archival reasons, but implementation also suppresses for `dropped`/`wontfix` via the `active_ids` gate. Routed back to architect for contract clarification.

### Resolution
The `active_ids` gate is architecturally correct and matches the Brief's design (step 3 explicitly partitions into `active_ids` vs `archived_reasons`). Guidance says "unresolved dependencies (IDs: ...)" — archived deps are lifecycle-complete, not actionable, and not listable. The `dep_status` field in `show_task()` already surfaces "blocked" for orchestration. AC2 was restated in terms of the actual gate condition rather than enumerating archival reasons.

### AC Refinements Applied
| AC | Before | After | Rationale |
|----|--------|-------|-----------|
| AC2 | Enumerated `completed`, `deprecated`, `duplicate` | "no dependency is active (every dep is either archived regardless of archival_reason, or its lookup raised an exception)" | Matches actual gate; doesn't create open-ended policy gap because the gate is about active_ids presence, not reason classification |
| AC3 | "response is a valid SingleTaskResponse" + missing mixed-failure observable | Four explicit observables: (a) no propagation, (b) SingleTaskResponse with task populated + claimed, (c) all-fail → guidance==[], (d) mixed-fail + active dep → guidance still fires | Removes banned "valid"; adds observable the tests already cover |

### Evaluation (unchanged from first pass — all criteria still PASS)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: dep-status guidance in start_work |
| Interface clarity | PASS | AC1 exact format; AC2 active_ids gate; AC3 four observables |
| Dependency correctness | PASS | #1526 archived-completed |
| Module layering | PASS | Uses existing _compute_dep_status, no upward imports |
| TDD compliance | PASS | Test task #1526 + task-scoped tests pre-exist |
| KISS/YAGNI | PASS | ~15 LoC inline, no abstractions |
| Premise challenge | PASS | Custom kanban feature, no IDE/stdlib equivalent |
| Pattern consistency | PASS | Mirrors show_task() dep iteration |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.42)
- Key findings: (1) "any archival_reason" too open-ended since reasons are policy-configurable; (2) Brief "Blocked-only scope" doesn't explicitly authorize active_ids suppression; (3) AC3 uses banned word "valid"
- Architect response: ACCEPTED findings (1) and (3) — refined AC2 to state the active_ids gate condition directly instead of enumerating reasons; refined AC3 to four explicit observables. REBUTTED finding (2) — Brief step 3 explicitly describes the active_ids partition as input to the logic; the partition enables distinguishing actionable from non-actionable deps. Guidance format "unresolved dependencies (IDs: ...)" requires listable active IDs; archived deps are not listable because they're lifecycle-complete.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (tests pre-exist; standard pipeline flow)

### Verdict: APPROVE (REFINE path — AC2/AC3 tightened to resolve reviewer contract-drift finding)
### Action Taken: Refined AC2 from enumerated archival reasons to active_ids gate condition; expanded AC3 observables; preserved design rationale in Context section; advanced to todo
2026-05-13T15:31:52+00:00
## Test-Writer Notes
- Test file: tests/test_agent_view_1527.py
- Classes: TestFromAC_StartWorkDepStatusGuidance
- Tests per category: happy 3 (AC1 active dep statuses), edge 3 (AC2 archived/all-fail), error 2 (AC3 exception types), boundary 2 (AC3 mixed-fail + claim verification)
- Total: 10 tests
- ruff: clean
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC1 exact guidance string | test_dep_in_inprogress_status_triggers_guidance, test_dep_in_review_status_triggers_guidance, test_three_deps_two_active_one_archived_guidance_lists_both_active |
  | AC2 archived any reason → guidance==[] | test_dep_archived_wontfix_returns_no_guidance, test_two_completed_deps_return_no_guidance, test_dep_archived_dropped_returns_no_guidance |
  | AC3 exception handling | test_exception_dep_skipped_active_dep_still_triggers_guidance, test_all_key_error_deps_guidance_is_empty_list, test_response_type_after_corruption_error_dep, test_task_is_claimed_after_exception_dep_lookup |
- Note: Post-architect-refinement re-verification. Test file was previously committed; implementation is complete. All 10 tests PASS against current impl (builder already green). Header comment fixed (AC2 entry renamed from test_null_depends_on_returns_no_guidance → test_dep_archived_wontfix_returns_no_guidance to match actual test). depends_on==[] case covered by 1526 test suite (test_start_work_no_depends_on_returns_empty_guidance). Refined AC2 (archived regardless of archival_reason) and AC3 (four explicit observables) are fully covered.
2026-05-13T15:49:12+00:00
## Builder Notes
- Files changed: none (implementation already present on branch)
- Files inspected:
  - serve/kanban/src/owlbear_kanban/agent_view.py
  - tests/test_agent_view_1527.py
  - serve/kanban/tests/test_agent_view_start_work_1526.py

- RED verification note:
  - Task-scoped TestFromAC suite did not fail because the AC behavior is already implemented in current source; no contract mismatch found between AC and tests.

- Quality-runner evidence:
  1) Scoped AC proof
     - mode=scoped
     - test_paths=[tests/test_agent_view_1527.py]
     - Result: 10 passed, 0 failed, 0 skipped
     - Lint: clean=true on serve/kanban/src/owlbear_kanban/agent_view.py and tests/test_agent_view_1527.py
     - Coverage: owlbear_kanban.agent_view 11%

  2) Expanded adjacent agent_view scope
     - mode=scoped
     - test_paths=[serve/kanban/tests/test_agent_view_start_work_1526.py, tests/test_agent_view_extraction.py, tests/test_agent_view_pick_tasks_1445.py, tests/test_agentview_ac_params_1520.py, tests/test_agent_view_1527.py]
     - Result: 61 passed, 0 failed, 0 skipped
     - Lint: clean=true
     - Coverage: owlbear_kanban.agent_view 47%

- Lint status:
  - ruff clean for task scope and expanded scope

- Evidence summary:
  - AC1 format guidance string is implemented in AgentView.start_work and verified by task tests.
  - AC2 no-guidance behavior for archived/no-active deps is verified.
  - AC3 exception swallowing for dep lookups is verified with claim continuity.
  - No additional code change was necessary in this builder cycle.

- Fixes applied:
  - none

- Commit status:
  - no new commit in this cycle (no source modifications).
2026-05-13T16:00:11+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1527 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence reviewed first: builder notes include quality-runner summaries for task scope (`tests/test_agent_view_1527.py`: 10 passed, lint clean, coverage snapshot 11%) and adjacent scope (`serve/kanban/tests/test_agent_view_start_work_1526.py`, `tests/test_agent_view_extraction.py`, `tests/test_agent_view_pick_tasks_1445.py`, `tests/test_agentview_ac_params_1520.py`, `tests/test_agent_view_1527.py`: 61 passed, lint clean, coverage snapshot 47%).

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 exact one-entry guidance string for active deps | [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L991), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1004), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1010), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1016) | [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L166), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L181), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L185), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L197), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L201), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L224) | PASS |
| AC2 empty/no-active deps return `guidance == []` | [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L663), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L681), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1010) | [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L230), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L251), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L255), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L279), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L283), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L303), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L256), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L268), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L295), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L321), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L462) | PASS |
| AC3 swallowed dep-lookup exceptions preserve response/claim semantics and mixed-fail guidance | [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L996), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1010), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1022), [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1047), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1612), [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L680) | [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L309), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L334), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L339), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L365), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L370), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L392), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L397), [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L409), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L371), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L402), [serve/kanban/tests/test_agent_view_start_work_1526.py](serve/kanban/tests/test_agent_view_start_work_1526.py#L431), [tests/test_agentview_ac_params_1520.py](tests/test_agentview_ac_params_1520.py#L82), [tests/test_agentview_ac_params_1520.py](tests/test_agentview_ac_params_1520.py#L88) | PASS |
- Challenger cross-check: `proceed` at confidence 0.82; no blocking code or proof defect surfaced.
- Safety/security check: PASS. The change path introduces no new IO boundary, dependency, auth, shell, path, or credential surface; the only new behavior is local dependency-state guidance computed from existing task records.

## Observations
- AC3(b) claim continuity is asserted directly on the `FileNotFoundError` path in [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L397) and [tests/test_agent_view_1527.py](tests/test_agent_view_1527.py#L409). The `CorruptionError`, `ValueError`, and `KeyError` variants are still sufficiently covered because they share the same caught-exception fall-through in [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L996) into the claim path at [serve/kanban/src/owlbear_kanban/agent_view.py](serve/kanban/src/owlbear_kanban/agent_view.py#L1022) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1612), but one explicit `claimed_at` assertion on a patched exception branch would make future proof packets more local.
- No independent `quality-runner` rerun was needed because the builder evidence was complete, internally consistent, and matched the inspected implementation and adjacent tests.
2026-05-13T16:03:06+00:00
## Docs Gate

**Verdict: PASS**

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | ✓ Updated | `serve/kanban/README.md`: expanded `start_work` table row to mention `SingleTaskResponse` + `guidance` list; replaced `> **TODO:** missing — document guidance field … [#1526]` with a paragraph accurately describing the dep-status warning behavior (active vs archived deps, exception swallowing). Content verified against implementation at `agent_view.py` L991–L1022. |
| External Attribution | N/A | No external sources cited; implementation mirrors existing `show_task()` dep iteration pattern |
| Research Doc | N/A | No research artifact exists for this task |
| Deletion Detection | N/A | Builder: "Files changed: none"; no deletions, no orphaned references |

### Files Updated
- `serve/kanban/README.md` — commit `a9897e89`

### Scratch Cleanup
- No `.owlbear/scratch/1527-*` files found
2026-05-13T16:16:40+00:00
## Audit
### Regression Detection
- quality-runner mode full: 5040 passed, 14 skipped, lint clean
- 187+ failures ALL in `tests/test_engine_accessor_migration.py` — promoted RED tests from tasks #1173/#1174 (engine accessor migration), last modified in unrelated commits (a5183f5c, 01d2d771). Pre-existing, not caused by #1527.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changes confined to `serve/kanban/src/owlbear_kanban/agent_view.py`, `tests/test_agent_view_1527.py`, `serve/kanban/README.md` — all kanban domain)
- purpose match: PASS (dep-status guidance in start_work matches stated task purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC refined twice (original + post-reviewer-rejection re-review). Final AC is specific: AC1 exact format string, AC2 clear active_ids gate condition, AC3 four explicit observables. Challenger dispatched and findings incorporated. Minor gap: initial AC2 enumerated archival reasons instead of using the gate condition — caught and corrected via reviewer rejection cycle. Score 4 (adequate, gaps filled by pipeline feedback).

### Commit Integrity
- upstream commit presence: PASS
  - test-writer: a8e728c4, 465fa185
  - builder #1526 implementation: 9a29e420 (builder #1527 confirmed no changes needed — implementation pre-existed)
  - doc-writer: a9897e89
- kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied.
### Confidence: 1.00
### Action: archive