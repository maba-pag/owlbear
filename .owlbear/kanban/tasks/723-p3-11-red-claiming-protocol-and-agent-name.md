---
id: 723
title: 'P3-11: RED — claiming protocol and agent-name generation'
status: backlog
priority: needed
created: 2026-04-09T03:26:15.7601787+02:00
updated: 2026-04-09T03:26:15.7601787+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 722
class: standard
---

## Objective
Write failing tests for claim/release protocol and session-stable agent-name generation.

Brief: see parent #712 — session-stable identity (intentional improvement over per-call)

## AC
- [ ] Test agent_name property: generated once, reused across calls
- [ ] Test agent_name format: adjective-noun from same word pool as kanban-md
- [ ] Test claim_task: sets claimed_by + claimed_at, rejects if already claimed by another
- [ ] Test release_task: clears claimed_by + claimed_at
- [ ] Test claim on blocked task is rejected
- [ ] Test claim_timeout behavior (claim expires after configured duration)
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_claims.py` (new)
