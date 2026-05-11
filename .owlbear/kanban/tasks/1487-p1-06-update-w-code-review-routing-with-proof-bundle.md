---
id: 1487
title: 'P1-06: Update w-code-review routing with proof-bundle'
status: backlog
priority: needed
created: 2026-05-11T08:59:01.968663+00:00
updated: 2026-05-11T08:59:55.564813+00:00
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

1. Reviewer scope table keyed on proof-bundle value (lint-only through full-suite)
2. Code-reader dispatch: critical by default, any bundle with +reader modifier
3. Challenger dispatch: behavioral/critical by default, any bundle with +challenge modifier

## Scope

- In: `share/skills/w-code-review/SKILL.md`
- Out: other skill files

Proof bundle: skip
Brief: see parent #1481