---
id: 1437
title: Simplify kanban topology for deployment readiness
status: backlog
priority: important
created: 2026-05-08T19:26:13.098440+00:00
updated: 2026-05-08T19:27:25.738560+00:00
tags:
- deployment-readiness
- kanban
- needs-decomposition
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-08T19:27:25.738560+00:00
archival_reason:
archival_refs: []
---

## Context

Deployment readiness audit found that the kanban engine, MCP server, Cockpit bridge, setup seed, and agent guidance expose too much board topology as editable config. The approved direction is to remove configurable board topology, make dispatch/read behavior explicit, and split cleanup/DR mutation into named operations.

## Approved Direction

- Remove configurable statuses, priorities, paths, agent routing, archival reasons, activity behavior, and dispatch policy.
- Prefer no next_id state file: allocate IDs by scanning active + archived task filename prefixes under a create lock.
- Make pick_tasks read-only: compute expired-claim eligibility but do not sweep or resolve DRs.
- Keep start_work as the atomic writer that clears/reclaims expired claims.
- Add an explicit resolve_drs MCP tool and remove DR resolution side effects from pick_tasks.
- Keep sweep/cleanup user-triggered via Cockpit maintenance.
- Centralize destination validation for all status-changing paths.
- Correct MCP annotations/descriptions and normalize MCP errors.
- Fix list filter semantics.
- Hard-code activity logging on and emit complete mutation events, including task creation.
- Wire create_dr end-to-end for pipeline agents and guidance.

## Planning Constraints

Needs decomposition: create implementation child tasks for the full remediation, with every child task placed in backlog, not todo. Each child task must have actionable, clear, measurable acceptance criteria. Split by domain and responsibility. Use explicit dependencies. Do not create placeholder tasks.

## Acceptance Criteria

- [ ] The planner creates an implementation task graph covering engine, MCP, Cockpit, setup/seed, agent guidance, docs, migration/cleanup, and verification probes.
- [ ] Every child task is created in backlog status.
- [ ] Each child task has clear, measurable AC suitable for architect review.
- [ ] Dependencies between slices are explicit.
- [ ] The plan avoids running the test suite as deployment proof; verification tasks use isolated scratch-board probes and contract inspection.