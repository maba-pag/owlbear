---
id: 983
title: 'Verify: seed propagation + full regression'
status: backlog
priority: important
created: 2026-04-18T21:18:42.531388+00:00
updated: 2026-04-18T21:18:42.531388+00:00
tags:
- type:test
- scope:seed
parent: 973
depends_on:
- 982
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Final verification.

## Acceptance Criteria
- Verify seed templates in `seed/` do NOT need updates for the guidance changes (kanban server changes propagate via the existing Python package install in consuming projects; no seed template change should be needed).
- Run full test suite (`uv run pytest`) — all tests green.
- Run lint (`uv run ruff check`) — clean.
- Verify a fresh consuming-project setup picks up the new guidance behavior (manual smoke test or automated integration test).

If any seed template DOES need updates, document why in the task body before completion.