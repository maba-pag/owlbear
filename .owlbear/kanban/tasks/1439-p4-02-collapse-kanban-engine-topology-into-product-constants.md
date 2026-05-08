---
id: 1439
title: 'P4-02: Collapse kanban engine topology into product constants'
status: backlog
priority: critical
created: 2026-05-08T19:31:49.034076+00:00
updated: 2026-05-08T19:34:33.954861+00:00
tags:
- phase-4
- scope:kanban
- type:refactor
- topology
- deployment-readiness
parent: 1437
depends_on:
- 1438
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: kanban engine topology authority and read APIs.
Out of scope: MCP transport, Cockpit UI, docs, and setup seed changes.

## Acceptance Criteria
1. Builder exposes one product-topology contract for statuses, priorities, status-to-agent routing, storage paths, archive reasons, default priority, claim timeout, dispatch wave policy, non-implementation tags, and enabled activity logging.
2. KanbanEngine initialises from a board directory with no config.yml and KanbanEngine.board_config returns the product topology contract for that board.
3. Given a scratch board whose config.yml changes status, priority, path, archive reason, activity_log, claim_timeout, dispatch policy, or agent routing values, KanbanEngine and AgentView expose the product topology contract instead of those file values.
4. Builder removes engine authority for configurable topology from BoardConfig, load_config, storage.save_config, KanbanEngine, AgentView, and dispatch while preserving task frontmatter parsing for task data fields.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1438 and does not use pytest or vitest as the functional proof.