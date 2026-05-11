---
id: 1453
title: 'P4-16: Wire create_dr end to end for agents and guidance'
status: backlog
priority: needed
created: 2026-05-08T19:32:28.041895+00:00
updated: 2026-05-11T09:19:10.136980+00:00
tags:
- phase-4
- scope:agents
- type:build
- create-dr
- guidance
- deployment-readiness
parent: 1437
depends_on:
- 1452
- 1447
- 1451
blocked: false
block_reason:
claimed_at: 2026-05-11T09:19:10.136980+00:00
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: create_dr MCP exposure, guidance generation, and pipeline-agent instruction references.
Out of scope: resolve_drs internals, Cockpit decision UI, and deployment docs.

## Acceptance Criteria
1. create_dr is available in the kanban MCP tool registry with task_id, agent, request_type, and body inputs and returns a structured created/path response.
2. Blocking guidance emitted by kanban mutation paths names create_dr and includes the task_id, agent, request_type, and body fields required from a pipeline agent.
3. Pipeline agent guidance and skills that discuss decision or action requests instruct agents to call create_dr instead of writing files under decisions directories.
4. create_dr guidance remains compatible with resolve_drs from #1447 by using the same pending and resolved directory contract.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1452 and does not use pytest or vitest as the functional proof.