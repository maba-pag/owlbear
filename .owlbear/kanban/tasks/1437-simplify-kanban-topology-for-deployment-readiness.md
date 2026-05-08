---
id: 1437
title: Simplify kanban topology for deployment readiness
status: backlog
priority: important
created: 2026-05-08T19:26:13.098440+00:00
updated: 2026-05-08T21:51:39.878991+00:00
tags:
- deployment-readiness
- kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-08T21:51:39.878991+00:00
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

[[2026-05-08]]

## Planning
### Decomposition: Simplify kanban topology for deployment readiness
- Tasks created by this planner pass: 20 (#1438 through #1457)
- Dependency layers: 10
- Phase: 4
- Status policy: child tasks were moved to backlog; no test suite was run.
- Concurrency note: parent #1437 was observed in todo during final inspection due to a separate board update; this planner did not advance the parent.

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1438 | P4-01: Probe fixed kanban topology contract | needed | none | phase-4, scope:kanban, type:test |
| 1439 | P4-02: Collapse kanban engine topology into product constants | critical | 1438 | phase-4, scope:kanban, type:refactor |
| 1440 | P4-03: Probe setup seed without config.yml writes | needed | none | phase-4, scope:setup, type:test |
| 1441 | P4-04: Remove config.yml from setup seed and board initialization | needed | 1440, 1439 | phase-4, scope:setup, type:refactor |
| 1442 | P4-05: Probe scan-based task ID allocation and activity events | needed | none | phase-4, scope:kanban, type:test |
| 1443 | P4-06: Replace next_id config allocation and hard-code activity logging | needed | 1442, 1439 | phase-4, scope:kanban, type:refactor |
| 1444 | P4-07: Probe read-only dispatch and atomic claim reclamation | needed | none | phase-4, scope:kanban, type:test |
| 1445 | P4-08: Make pick_tasks read-only and keep start_work as claim writer | critical | 1444, 1439, 1443 | phase-4, scope:kanban, type:refactor |
| 1446 | P4-09: Probe explicit decision resolver behavior | needed | none | phase-4, scope:mcp-kanban, type:test |
| 1447 | P4-10: Add retry-safe resolve_drs MCP operation | critical | 1446, 1445 | phase-4, scope:mcp-kanban, type:build |
| 1448 | P4-11: Probe maintenance cleanup semantics | needed | none | phase-4, scope:maintenance, type:test |
| 1449 | P4-12: Add user-triggered cleanup for expired claims and archived moves | needed | 1448, 1445 | phase-4, scope:kanban, type:build |
| 1450 | P4-13: Probe MCP list filters, annotations, and error envelopes | needed | none | phase-4, scope:mcp-kanban, type:test |
| 1451 | P4-14: Normalize MCP filters, annotations, and errors | needed | 1450, 1445, 1447 | phase-4, scope:mcp-kanban, type:build |
| 1452 | P4-15: Probe create_dr guidance and pipeline integration | needed | none | phase-4, scope:agents, type:test |
| 1453 | P4-16: Wire create_dr end to end for agents and guidance | needed | 1452, 1447, 1451 | phase-4, scope:agents, type:build |
| 1454 | P4-17: Probe documentation and agent guidance contract | needed | none | phase-4, scope:docs, type:test |
| 1455 | P4-18: Update deployment docs and agent guidance | needed | 1454, 1439, 1441, 1443, 1445, 1447, 1449, 1451, 1453, 1457 | phase-4, scope:docs, type:docs |
| 1457 | P4-19: Expose maintenance cleanup through Cockpit | needed | 1448, 1449 | phase-4, scope:cockpit, type:build |
| 1456 | P4-20: consolidation test: fixed-topology deployment readiness | important | 1439, 1441, 1443, 1445, 1447, 1449, 1451, 1453, 1455, 1457 | phase-4, consolidation-test, type:test |

### Dependency Graph
Root probes: 1438, 1440, 1442, 1444, 1446, 1448, 1450, 1452, 1454.
Implementation pairs: 1438 before 1439; 1440 before 1441; 1442 before 1443; 1444 before 1445; 1446 before 1447; 1448 before 1449 and 1457; 1450 before 1451; 1452 before 1453; 1454 before 1455.
Integration gates: 1455 depends on completed implementation slices; 1456 depends on implementation and docs slices.

### Creation Commands
Created each child with create_task(title), then applied edit_task(parent=1437, priority, tags, body, dependencies) and move_task(status=backlog).
