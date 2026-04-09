---
id: 724
title: 'P3-12: GREEN — claiming protocol and agent-name generation'
status: backlog
priority: needed
created: 2026-04-09T03:26:31.782724+02:00
updated: 2026-04-09T03:26:31.782724+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 723
class: standard
---

## Objective
Implement claiming, release, and session-stable agent-name generation on KanbanEngine.

Brief: see parent #712

## AC
- [ ] `agent_name` property: generated adjective-noun once per engine instance, stored, reused
- [ ] `claim_task(task_id)`: sets claimed_by=agent_name, claimed_at=now; rejects if blocked or already claimed by another agent
- [ ] `release_task(task_id)`: clears claimed_by and claimed_at
- [ ] Claim timeout: configurable from config.yml `claim_timeout`
- [ ] All #723 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (edit — add claim methods, agent_name property)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/agent_names.py` (new — word pool and generation)
