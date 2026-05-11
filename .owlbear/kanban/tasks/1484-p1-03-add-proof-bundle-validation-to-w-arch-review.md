---
id: 1484
title: 'P1-03: Add proof-bundle validation to w-arch-review'
status: backlog
priority: needed
created: 2026-05-11T08:59:01.930089+00:00
updated: 2026-05-11T08:59:55.550078+00:00
tags:
- pipeline
- convention
- scope:skills
parent: 1481
depends_on:
- 1482
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. Architect validates bundle assignment (confirm, escalate, or de-escalate) as part of review verdict
2. Architect can add escalation modifiers (+challenge, +reader) to the bundle
3. `existing` bundle requires architect to verify proof-scope glob accuracy

## Scope

- In: `share/skills/w-arch-review/SKILL.md`
- Out: other skill files

Proof bundle: skip
Brief: see parent #1481