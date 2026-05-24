---
id: 1794
title: Expose dependency status projection as engine contract
status: research
priority: important
created: 2026-05-24T02:02:33.566320+02:00
updated: 2026-05-24T02:02:33.566320+02:00
tags:
  - scope:kanban-engine
  - scope:cockpit-web
  - data-contract
  - technical-debt
  - discussion
parent: 1790
depends_on: []
ac:
  - Dependency status projection has a named engine/view contract used by both 
    list and show task projections.
  - Cockpit continues to consume `dep_status` only through API responses.
  - No direct task-file reads or writes are introduced.
  - Tests cover list and show projections for blocked/ok/no dependency cases.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
#1790 traced `dep_status` and confirmed Cockpit receives it from Kanban/Cockpit API projections, not direct filesystem reads. However, `AgentView.show_task` computes full-task `dep_status` by calling `engine._compute_dep_status()` with `# noqa: SLF001`, meaning the projection path relies on a private helper.

## Decision
User chose to create an engine cleanup task rather than hide the field or treat it as unsafe.

## Goal
Make dependency-status projection an explicit engine/view contract so list and show projections use a named public/internal projection method rather than reaching into a private helper.

## Boundary
This is not approval to implement now. It exists to keep future Cockpit dependency UI work honest and engine-backed.