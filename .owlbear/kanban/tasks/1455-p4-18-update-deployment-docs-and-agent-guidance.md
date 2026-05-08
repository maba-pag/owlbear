---
id: 1455
title: 'P4-18: Update deployment docs and agent guidance'
status: backlog
priority: needed
created: 2026-05-08T19:32:33.602172+00:00
updated: 2026-05-08T19:40:40.074461+00:00
tags:
- phase-4
- scope:docs
- type:docs
- docs
- guidance
- deployment-readiness
parent: 1437
depends_on:
- 1454
- 1439
- 1441
- 1443
- 1445
- 1447
- 1449
- 1451
- 1453
- 1457
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: repository docs, handbook skills, and instruction guidance describing kanban deployment topology.
Out of scope: source behavior changes, Cockpit UI code, and test-suite execution.

## Acceptance Criteria
1. Documentation describes fixed product topology for statuses, priorities, status-to-agent routing, storage paths, archive reasons, claim timeout, dispatch policy, and enabled activity logging.
2. Setup documentation states that setup creates board directories and does not seed or overwrite .owlbear/kanban/config.yml.
3. MCP/agent guidance states that pick_tasks is read-only, start_work performs expired-claim reclamation, resolve_drs handles DR resolution, create_dr creates decision/action requests, and Cockpit maintenance triggers cleanup.
4. Documentation or guidance that previously described next_id config state, automatic sweep, automatic DR resolution in pick_tasks, configurable topology, or idempotent move_task behavior is updated or removed.
5. Doc-writer verifies AC-1 through AC-4 using the probe artifacts from #1454 and does not use pytest or vitest as the functional proof.