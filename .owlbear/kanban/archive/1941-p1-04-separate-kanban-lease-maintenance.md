---
id: 1941
title: 'P1-04: Separate Kanban lease maintenance'
status: archived
priority: medium
created: 2026-07-17T02:32:09.437681+02:00
updated: 2026-07-17T17:17:29.918880+02:00
tags:
  - phase-1
  - scope:kanban
  - maintenance
parent: 1945
depends_on:
  - 1940
ac:
  - Given expired claims and stale activity sessions, the explicit sweep 
    operation releases eligible claims and reconciles their sessions without 
    moving archived tasks or resolving duplicate files.
  - Given task repair on a board with expired claims and activity history, claim
    fields and activity-retention content remain unchanged.
  - Until Cockpit removes its existing cleanup consumer, the Kanban public 
    maintenance surface exposes explicit claim sweep and activity compaction 
    independently; the retained cleanup aggregate is not used by health repair 
    and remains only as that migration bridge.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Establish explicit Kanban claim/session maintenance without losing expired-claim release, stale-session reconciliation, or independent activity compaction.

## Scope
In scope: Kanban engine claim/session maintenance APIs and separation of lease/session work from task health repair. The generic engine cleanup method remains temporarily only for its existing Cockpit migration caller. Out of scope: task-health detection, duplicate/archive repair algorithms, Cockpit routes, frontend controls, and final deletion of the generic cleanup contract.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted three-step maintenance migration. Task repair is supplied by dependency #1940. Cockpit consumer removal is owned by #1942; final generic Kanban cleanup deletion follows that task.

## Proof Guidance
Use focused Kanban engine behavior and a downstream-consumer inventory check. Preserve stale-session reconciliation assertions at the explicit sweep boundary so later deletion of cleanup-specific tests does not lose this proof; add durable coverage only for a meaningful separation regression.

[[2026-07-17T07:51:42+02:00]]
## Builder Notes

### Change Envelope
Expected owner: `serve/kanban/src/owlbear_kanban/engine.py` generic maintenance API and its direct public consumers. Intended behavior: remove the generic cleanup operation while retaining independently callable claim sweep and activity compaction. Cheapest falsifying check: exhaustive production search for `cleanup()` consumers plus focused Kanban API inventory.

### Finding
Source inspection shows `KanbanEngine.cleanup()` is still consumed by `serve/cockpit/src/owlbear_cockpit/view.py`, and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` exposes it as `POST /tasks/cleanup` with `CleanupResult`. Removing the engine surface while honoring this task's explicit out-of-scope rule for Cockpit routes would leave a broken production consumer. Leaving `cleanup()` in place would fail the acceptance criterion that the public maintenance surface has no generic cleanup operation combining claim release, archive reconciliation, duplicate correction, and activity work.

### Change Module Map Deviation
None. Current source confirms the contradiction at the Kanban-to-Cockpit interface.

### Proof Selected
Read-only exact search and direct source inspection; no edits made and no focused test run because the shaped scope is not implementable without either changing the excluded Cockpit route or retaining the prohibited API.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | shape | Resolve whether `/tasks/cleanup` and its `CleanupResult` contract are removed/migrated in this change, or whether the generic cleanup API remains outside this task's acceptance criteria. | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/view.py`, `serve/kanban/src/owlbear_kanban/engine.py` | Existing route at `mutation.py` exposes `POST /tasks/cleanup`; view delegates to `engine.cleanup()`; AC requires no generic cleanup operation. |

[[2026-07-17T16:24:46+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: Builder rejection dated 2026-07-17 on task #1941.
- Classification: material reshape. The original AC required deletion of `KanbanEngine.cleanup` while Cockpit still consumed that method through `view.py` and `POST /tasks/cleanup`; the task simultaneously excluded Cockpit changes.
- Fact check: live source confirmed the engine method/result model and the Cockpit view/route consumer. OpenSpec already required end-state deletion with no compatibility alias.

### User Decision And Planning Revisions
- User approved a three-step runnable migration: establish explicit claim/session maintenance, remove Cockpit consumers, then delete the unconsumed Kanban cleanup contract.
- Revised `openspec/changes/redesign-workspace-health/design.md` decision 8, risk treatment, and migration order.
- Revised `openspec/changes/redesign-workspace-health/tasks.md` task 2.2 and added task 4.4.
- `uv run openspec validate redesign-workspace-health --strict` passed.

### Brief Readiness And Authorities
- Product outcome: claim/session maintenance remains explicit and outside workspace health; the completed change has no generic cleanup action or contract.
- Current-source authority: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/models.py`, `serve/cockpit/src/owlbear_cockpit/view.py`, and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`.
- Normal proof: focused Kanban maintenance behavior, assembled FastAPI route inventory, and exhaustive production-consumer/public-inventory scan.
- Completion contract: temporary engine bridge is permitted only until Cockpit consumer removal; no end-state alias is permitted.

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owning Task |
|---|---|---|---|---|
| `serve/kanban/src/owlbear_kanban/engine.py` | Claim sweep, activity compaction, and generic cleanup | Reconcile stale sessions in explicit lease maintenance, then remove cleanup | Changed then removed | #1941, #1959 |
| `serve/kanban/src/owlbear_kanban/models.py` | `CleanupResult` model | Delete after consumers are removed | Removed | #1959 |
| `serve/kanban/README.md` | Public maintenance inventory | Remove generic cleanup entry | Removed | #1959 |
| Cockpit mutation routes and view | Cleanup route and engine forwarding | Remove consumer while retaining explicit maintenance routes | Removed | #1942 |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof / Allowed Replacement |
|---|---|---|---|
| Claim sweep releases eligible claims and reconciles stale sessions without storage-health repair | #1941 | Kanban engine maintenance API | Focused real-board behavior; filesystem root replaceable |
| Cockpit exposes health/repair and explicit maintenance routes without obsolete cleanup route | #1942 | Assembled FastAPI route inventory | Real app; lower domain engines replaceable where needed |
| Kanban public surface has no generic cleanup contract at completion | #1959 | Callable/exported/documented Kanban inventory | Focused behavior plus exhaustive production-consumer scan |
| Full workspace-health workflow and removals are complete | #1945 | Running Cockpit aggregate | Aggregate child evidence plus assembled proof |

### Task And Dependency Changes
- #1941 scope and AC3 now permit the temporary bridge and route this task to build after #1940.
- #1942 remains the Cockpit consumer-removal owner and depends on #1941.
- Created #1959 in build, parent #1945, depending on #1942, to delete `cleanup`, `CleanupResult`, exports, documentation, and directly stale Kanban tests.
- Aggregate #1945 now depends on #1959 in addition to its existing children.

### Challenger And Route
- Shaper challenger decision: pass. No blocking findings.
- Incorporated non-blocking guidance: #1941 proof must preserve stale-session assertions at the explicit sweep boundary before cleanup-specific tests are removed.
- Resulting route: #1941 enters build; #1959 remains blocked in build until #1942 completes.

[[2026-07-17T17:11:14+02:00]]
## Builder Notes

### Change Envelope
- Owner: `serve/kanban/src/owlbear_kanban/engine.py`, `KanbanEngine.sweep()` maintenance boundary.
- Behavior: explicit sweep releases expired claims and reconciles stale activity sessions; archive/duplicate repair remains in the temporary aggregate `cleanup()` bridge; activity compaction remains independently callable.
- Cheapest falsifying proof: focused Kanban activity tests plus production consumer/API inventory.

### Files Changed
- `serve/kanban/src/owlbear_kanban/engine.py`

### Change Module Map Deviations
- None. Reused the existing `sweep()` and `_close_stale_active_sessions()` owners; no Cockpit route or health-repair changes were made.

### Proof
- `uv run pytest serve/kanban/tests/test_engine_activity.py -k 'sweep_released_session_visible_in_all_filter or aged_open_claim_classified_as_stuck' -q` -> `2 passed in 0.45s` (builder-challenger proof).
- `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py` -> `All checks passed!`.
- Broader focused test invocation was blocked by workspace pytest configuration referencing a missing Cockpit path; one retry exited 130 with no output and was not treated as evidence.

### Durable-Test Justification
- No new durable tests. Existing activity tests cover the shared sweep/session boundary and passed.

### Builder-Challenger Result
- `builder-challenger`: pass.

### Follow-up Risks
- `cleanup()` remains as the Cockpit migration bridge by explicit task scope; its later removal belongs to task `1942`/the planned follow-up.

[[2026-07-17T17:15:49+02:00]]
## Verify Notes

### Evidence Reviewed
- Task outcome, scope, all three AC lines, Builder Notes, and the approved Shape Notes were reviewed.
- Named planning authority: `openspec/changes/redesign-workspace-health/design.md` Decision 8 and migration step 5; `tasks.md` 2.2. They require the first runnable migration step: explicit claim/session maintenance while retaining `KanbanEngine.cleanup()` only as the existing Cockpit bridge.

### Change Module Map
- Expected owner was `serve/kanban/src/owlbear_kanban/engine.py`; committed task `8c29e6bfe` changes that owner and the task record only.
- No map deviation: `sweep()` now calls `_close_stale_active_sessions()` after expired-claim processing. The temporary Cockpit consumer still delegates to `cleanup()`; `compact_activity()` stays an independent operation.

### Normal-Path Boundaries
- Explicit sweep: real temporary-board test releases the expired claim and verifies the resulting stale session is visible as expired.
- Repair isolation: the deterministic real-filesystem repair suite exercises `repair_task_storage()` and the separate corruption owner. Its source neither invokes `sweep()` nor accesses activity logging; task repair remains distinct from lease/session maintenance.
- Consumer inventory: `serve/cockpit/src/owlbear_cockpit/view.py` and `routes/mutation.py` are the existing temporary `cleanup()` bridge; they also expose independent sweep and activity-compaction forwarding.

### Checks Run
- `uv run pytest serve/kanban/tests/test_engine_activity.py -k 'sweep_released_session_visible_in_all_filter or aged_open_claim_classified_as_stuck' -q` - 2 passed.
- `uv run pytest serve/kanban/tests/test_corruption.py -q` - 82 passed.
- `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py` - all checks passed.

### Findings And Patches
- No defects found. No verifier patch applied.

### Verifier-Challenger
- `verifier-challenger`: pass; no blockers. It confirmed revised scope permits the temporary cleanup bridge and that focused proof covers the claimed maintenance and repair boundaries.

### Final Route
- PASS: AC satisfied with explicit sweep/session maintenance, repair separation, and independent compaction verified. Advance to collect.

[[2026-07-17T17:17:29+02:00]]
## Collect Notes

- Classification: leaf. Task has no children, is parented by aggregate #1945, and carries implementation-level outcome, scope, and AC rather than aggregate intent.
- Verification evidence: `## Verify Notes` records PASS with 2 focused sweep/session tests passed, 82 corruption/repair tests passed, Ruff clean, no verifier patch, and verifier-challenger `pass`.
- Invariant coverage: explicit sweep releases expired claims and reconciles stale sessions; repair remains isolated from claim/activity state; independent activity compaction and the temporary Cockpit cleanup bridge remain available.
- Dependency closure: dependency #1940 is archived with reason `completed`; task dependency status is `ok`.
- Residual state: no child tasks, pending decision requests, block, unresolved Required Follow-up, or residual decision state.
- Rationale: leaf verification and closure evidence are complete; archive as completed.
