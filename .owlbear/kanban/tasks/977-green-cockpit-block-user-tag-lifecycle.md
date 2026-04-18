---
id: 977
title: 'GREEN: Cockpit block:user tag lifecycle'
status: backlog
priority: needed
created: 2026-04-18T21:18:03.821522+00:00
updated: 2026-04-18T21:18:03.821522+00:00
tags:
- scope:cockpit
- type:build
parent: 973
depends_on:
- 975
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. GREEN phase per w-tdd-green. Makes #975 tests pass.

## Acceptance Criteria
File: `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`

Per Brief decision D3:
- Block path (`edit_task` route when transitioning to blocked) adds `block:user` to task tags. Idempotent — no duplicates if already present.
- Unblock path removes `block:user` from task tags. No-op if not present.
- No new arguments to the route. No MCP routing change. Cockpit continues to call the engine directly.

All tests in #975 pass; all existing cockpit tests still pass.