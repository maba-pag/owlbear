---
id: 1200
title: Remove claimed_by ghost field from Task model
status: backlog
priority: needed
created: '2026-04-30 15:28:55.673059+00:00'
updated: '2026-04-30 15:32:04.089960+00:00'
tags:
- audit-kanban
parent:
depends_on:
- 1202
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove the `claimed_by` ghost field from the Task model.

## Files
- models.py (Task class)
- engine.py (verify no reads of claimed_by)

## Change
Remove `claimed_by: str | None = Field(default=None, exclude=True)` from Task. Use claim-file existence checks directly where needed.

## AC
- [ ] Task model has no claimed_by field
- [ ] No runtime references to task.claimed_by
- [ ] Claim logic still works via claim-file checks
- [ ] All tests pass

## Finding: 4.4
