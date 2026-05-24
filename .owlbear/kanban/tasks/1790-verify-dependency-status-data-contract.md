---
id: 1790
title: Verify dependency status data contract
status: done
priority: critical
created: 2026-05-24T01:57:03.801111+02:00
updated: 2026-05-24T02:03:00.622664+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - scope:kanban-engine
  - data-contract
  - discussion
parent: 1773
depends_on:
  - 1794
ac:
  - The source of dependency status shown in Cockpit is identified and 
    documented.
  - If the field is not engine/API-backed, a follow-up engine/interface task is 
    created before relying on it for product behavior.
  - Cockpit does not directly interact with task files to provide or mutate 
    dependency status.
  - No implementation begins until the user approves this task.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User asked where the `Dependency status blocked` field in task detail comes from and noted they do not remember the Kanban engine providing it. We must be careful not to fake data or implement functionality directly against the filesystem.

## Current Interpretation
Potential data-contract risk. If Cockpit displays dependency status that is computed locally or inferred outside the engine/API contract, that needs to be made explicit and possibly moved into the Kanban engine/interfaces.

## Value
Cockpit must not bypass the engine or write/read task state directly from files, except notes where explicitly allowed. UI fields should reflect authoritative API/engine data or have a tracked task to add that contract.

## Discussion Questions
- Is dependency status currently provided by the backend/engine, or computed in Cockpit?
- If computed, is it a harmless display derivation from API fields or an unsupported fake contract?
- Do we need an engine/API task to expose dependency status formally before improving the UI?

[[2026-05-24T02:00:44+02:00]]
## Evidence Trace
`dep_status` is backend/engine-derived, not a Cockpit filesystem read:
- `serve/kanban/src/owlbear_kanban/models.py`: `Task` drops `dep_status` before validation/storage as a projection-only field; `TaskSummary` and `TaskFull` include `dep_status` for read output.
- `serve/kanban/src/owlbear_kanban/engine.py`: `_compute_dep_status()` computes `blocked`, `redirect`, or `ok` from dependency IDs, active IDs, and archived dependency reasons.
- `serve/kanban/src/owlbear_kanban/engine.py`: list projections attach computed `dep_status` before returning `TaskSummary`.
- `serve/kanban/src/owlbear_kanban/agent_view.py`: show-task projection computes `dep_status` for a full task by checking dependencies through the engine.
- `serve/cockpit/src/owlbear_cockpit/routes/read.py`: `/api/tasks` and `/api/tasks/{id}` delegate through Cockpit view to the Kanban agent view.
- `serve/cockpit/web/src/api/tasks.ts` and `DetailTab.tsx`: frontend only consumes `dep_status` from the API response.

## Interpretation
The field is legitimate engine/API projection data, not a fake UI field and not a direct filesystem interaction from Cockpit. Remaining concern: `AgentView.show_task` calls `engine._compute_dep_status()` as a private helper (`# noqa: SLF001`), so there may still be an engine-internal API cleanliness task if we want the projection contract to be more explicit.

[[2026-05-24T02:02:46+02:00]]
## Decision
User selected `Create engine cleanup task`. Created #1794 to formalize dependency status projection as an engine/view contract. Cockpit display of `dep_status` is accepted as safe because it is API-backed, not direct filesystem access.
