---
id: 1080
title: 'B-12: GREEN — end_work'
status: todo
priority: important
created: 2026-04-21T10:50:32.621365+00:00
updated: 2026-04-21T10:50:32.621365+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1077
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief B (#1044) — paper-integration.md §1.8, §3.7
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.end_work — the 4-outcome lifecycle endpoint (success, reject, release, block per D52). This is the most complex single method in the engine.

Outcomes: success (auto-advance, auto-archive from terminal per D51), reject (move_to required, archival path available), release (idempotent no-op on unclaimed per D55), block (block_reason required, optional move_to per D52).

Forbidden-parameter matrix enforced deterministically before any state mutation (D41). Multiple errors → leftmost-row, leftmost-column precedence.

## Acceptance Criteria

- [ ] All RED tests from B-11 (#1077) pass
- [ ] 4 outcomes dispatched correctly: success, reject, release, block
- [ ] Forbidden-parameter matrix: deterministic error precedence per §1.8 table
- [ ] success: auto-advance one step; from terminal → archive completed/[] (D51)
- [ ] reject: move_to required; archival path with full D37 validation
- [ ] release: idempotent on unclaimed (pure no-op per D55)
- [ ] block: block_reason required; optional move_to with predicate (D15+D41)
- [ ] All mutations atomic — predicate/validation failure → nothing written (D41)
- [ ] Note prepended with ISO 8601 timestamp (D20)
- [ ] Guidance emitted for block (AR/DR suggestion) and skip-transition (D54)