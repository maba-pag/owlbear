---
id: 915
title: Scoped TestFromAC immutability conventions
status: archived
priority: needed
created: 2026-04-17T11:52:08.016899+00:00
updated: 2026-04-17T20:04:08.505239+00:00
tags:
- test-quality
- type:docs
- scope:copilot
parent: 912
depends_on:
- 914
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #912

## AC

- `w-tdd-red` updated: TestFromAC immutability rule explicitly scoped to active pipeline (task creation through archive); post-archive authority noted as delegated to curator
- `w-code-review` updated: reviewer validates TestFromAC immutability during active pipeline; acknowledges curator authority post-archive
- Scoping language is precise — no ambiguity about when immutability starts/ends
- No behavioral changes to test-writer or reviewer — purely clarifying temporal scope
