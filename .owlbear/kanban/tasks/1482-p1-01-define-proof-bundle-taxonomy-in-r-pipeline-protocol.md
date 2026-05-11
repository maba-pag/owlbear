---
id: 1482
title: 'P1-01: Define proof-bundle taxonomy in r-pipeline-protocol'
status: backlog
priority: critical
created: 2026-05-11T08:58:34.021832+00:00
updated: 2026-05-11T08:58:52.849928+00:00
tags:
- pipeline
- convention
- scope:skills
parent: 1481
depends_on: []
blocked: true
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. `r-pipeline-protocol` defines the 5-value proof-bundle enum (skip | existing | smoke | behavioral | critical) with complete routing table (test-writer, challenger, code-reader, reviewer-scope columns)
2. Escalation modifiers (+challenge, +reader) documented with expansion rules, redundancy normalization, and invalid-token rejection
3. Legacy (td:N) compatibility mapping table for in-progress tasks present in same file

## Scope

- In: `share/skills/r-pipeline-protocol/SKILL.md`
- Out: Consumer skill changes (separate tasks)

Proof bundle: skip
Brief: see parent #1481