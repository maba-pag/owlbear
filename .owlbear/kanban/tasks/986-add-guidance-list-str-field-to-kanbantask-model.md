---
id: 986
title: 'Add `guidance: list[str]` field to KanbanTask model'
status: backlog
priority: needed
created: 2026-04-18T21:22:36.972344+00:00
updated: 2026-04-18T21:46:01.248009+00:00
tags:
- type:feature
- scope:mcp
- scope:kanban
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D4.

## Problem
`KanbanTask` in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` has no `guidance` field. This is the foundation for all block-time guidance features.

## Acceptance Criteria
- `guidance: list[str] = Field(default_factory=list)` is the **first declared field** on `KanbanTask` (before `id`).
- Pydantic v2 declaration-order serialization places `guidance` first in JSON output.
- `_record_to_task` continues to work — engine `Task` lacks `guidance`, Pydantic defaults to `[]`.
- Unit test: field exists, defaults to empty list.
- Unit test: JSON serialization order has `guidance` as first key.
- Unit test: `model_validate` from engine Task dict (no guidance key) produces `guidance=[]`.

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- `serve/mcp-kanban/tests/test_guidance_model_973.py` (new)
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/guidance-model-field-986.md
- Sources: 6 studied, 5 high-relevance (≥0.8)
- Recommendation: Proceed with D4 as specified — Pydantic 2.12.5 declaration-order serialization verified empirically; `_record_to_task` auto-fills `guidance=[]`; no downstream breakage (confidence: .95)
- Follow-up tasks created: none (downstream #987/#985/#989/#991 already exist)
- Decision requests: none (D4 locked, T1 autonomous)