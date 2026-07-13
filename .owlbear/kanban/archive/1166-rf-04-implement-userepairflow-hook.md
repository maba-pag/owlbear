---
id: 1166
title: 'RF-04: Implement useRepairFlow hook'
status: archived
priority: medium
created: 2026-04-28T17:38:24.630886+00:00
updated: 2026-04-29T11:00:51.416480+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:build
parent:
depends_on:
- 1165
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
Implements the repair flow state machine hook.
Consumes `repairStorage()` (#1164). Accepts a re-poll callback to refresh scan data after repair.

## Acceptance Criteria

- [ ] `useRepairFlow` hook exported with state machine: idle → confirming → repairing → done/error
- [ ] Exposes: `requestRepair(count)`, `confirmRepair()`, `cancelRepair()`, `dismissResults()`, `state`, `outcomes`, `error`
- [ ] Groups outcomes by action (fixed/quarantined/failed) in done state
- [ ] Calls re-poll callback after successful repair
- [ ] All #1165 tests pass

## Scope

- **In scope:** Hook implementation, state management, API call orchestration
- **Out of scope:** Rendering, PDS components, Shell wiring
[[2026-04-29]]


## Superseded
Merged into #1165 by architect. Builder had already implemented both tests and hook in #1165. This task is redundant — do not process.

[[2026-04-29]]
## Architecture Review

### Verdict: SUPERSEDED — closed as redundant

Task #1165 ("RF-03: useRepairFlow hook — tests + implementation") already implemented both the tests and the `useRepairFlow` hook. #1165 is archived (completed). This task's body already contains a `## Superseded` note from a prior architect pass confirming the merge.

No codebase work remains. Skipping full pipeline (todo→in-progress→review→docs→done) — moving directly to done.

### Evidence
- #1165 status: archived (completed)
- #1165 title: "RF-03: useRepairFlow hook — tests + implementation"
- #1166 body contains: "Merged into #1165 by architect. Builder had already implemented both tests and hook in #1165. This task is redundant — do not process."
[[2026-04-29]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| useRepairFlow hook exported with state machine | Superseded — implemented in #1165; hook at `serve/cockpit/web/src/hooks/useRepairFlow.ts` | PASS |
| Exposes requestRepair, confirmRepair, cancelRepair, etc. | Superseded — implemented in #1165; test at `useRepairFlow_1165.test.ts` | PASS |
| Groups outcomes by action | Superseded — covered by #1165 tests | PASS |
| Calls re-poll callback after repair | Superseded — covered by #1165 tests | PASS |
| All #1165 tests pass | #1165 archived; frontend tests pass (`npm test --run` green) | PASS |

### Supersession Evidence
- Task body `## Superseded` section: "Merged into #1165 by architect"
- Architecture Review confirms redundancy with evidence
- #1165 status: archived (verified via `list_tasks(archived=true)`)
- `useRepairFlow` hook + test file exist in codebase

### Test Results
- pytest: 2997 passed, 122 failed (all pre-existing `serve/kanban/` engine failures — unrelated to this frontend task), 4 skipped
- ruff: 4 violations in unrelated packages (knowledge, mcp-knowledge, mcp-memory, orchestrator)
- No task-scoped failures

### Architect Quality: 4/5
Original AC was specific and verifiable. Supersession by architect was correctly identified and documented with evidence. Minor: could have been caught earlier to avoid redundant task creation.

### Deduction Breakdown
- No deductions — superseded task with clear evidence chain, no code changes, no task-scoped failures

### Confidence: 1.00
### Action: archive