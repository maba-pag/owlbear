---
id: 1527
title: 'P1-02: implement dep-status guidance in start_work (AC1-AC3)'
status: todo
priority: critical
created: 2026-05-13T12:17:51.690274+00:00
updated: 2026-05-13T15:27:10.496975+00:00
tags:
  - phase-1
  - scope:kanban
  - feature
parent: 1525
depends_on:
  - 1526
blocked: false
block_reason:
claimed_at: 2026-05-13T15:27:10.496975+00:00
archival_reason:
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