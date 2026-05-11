---
id: 1489
title: 'P1-08: Final sweep — remove all remaining td:N annotations'
status: backlog
priority: important
created: 2026-05-11T09:00:01.191773+00:00
updated: 2026-05-11T09:03:05.489841+00:00
tags:
- pipeline
- convention
- agent
parent: 1481
depends_on:
- 1488
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. No per-AC-line `(td:N)` annotation in any active skill or procedure
2. No `td:0`, `td:1`, `td:2` references in active skills (archived tasks untouched)
3. `grep -r "td:" share/skills/ share/instructions/ share/agents/` returns zero matches for the legacy pattern

## Scope

- In: all files in `share/skills/`, `share/instructions/`, `share/agents/`
- Out: archived kanban tasks, Brief docs, research docs

Proof bundle: skip
Brief: see parent #1481