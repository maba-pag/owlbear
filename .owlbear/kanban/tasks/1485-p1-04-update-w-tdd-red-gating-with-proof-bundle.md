---
id: 1485
title: 'P1-04: Update w-tdd-red gating with proof-bundle'
status: backlog
priority: needed
created: 2026-05-11T08:59:01.942836+00:00
updated: 2026-05-11T09:03:05.465193+00:00
tags:
- pipeline
- convention
- scope:skills
- agent
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

1. Test-writer reads `Proof bundle:` from task body/verdict to determine action
2. skip/existing → pass-through (no tests written, advance to in-progress)
3. smoke → one smoke test per AC line; behavioral/critical → full TDD mapping

## Scope

- In: `share/skills/w-tdd-red/SKILL.md`
- Out: other skill files

Proof bundle: skip
Brief: see parent #1481