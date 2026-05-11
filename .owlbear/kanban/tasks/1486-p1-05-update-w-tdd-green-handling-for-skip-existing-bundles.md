---
id: 1486
title: 'P1-05: Update w-tdd-green handling for skip/existing bundles'
status: backlog
priority: needed
created: 2026-05-11T08:59:01.954913+00:00
updated: 2026-05-11T09:03:05.472243+00:00
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

1. Builder handles skip/existing bundles: implement from AC directly (no tests to pass)
2. For `existing` bundle, builder ensures named existing tests still pass
3. Legacy td:0 pass-through check replaced with bundle-based routing

## Scope

- In: `share/skills/w-tdd-green/SKILL.md`
- Out: other skill files

Proof bundle: skip
Brief: see parent #1481