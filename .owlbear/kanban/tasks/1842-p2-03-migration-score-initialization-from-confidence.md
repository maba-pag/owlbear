---
id: 1842
title: 'P2-03: Migration — score initialization from confidence'
status: research
priority: needed
created: 2026-05-24T19:01:24.804040+02:00
updated: 2026-05-24T19:15:17.387592+02:00
tags:
  - phase-2
  - scope:memory
  - migration
parent: 1839
depends_on:
  - 1841
ac:
  - A migration function sets `score = confidence` and all assessment counters 
    to 0 for entries missing the score field. State is unchanged.
  - 'Migration is idempotent: re-running on already-migrated entries (score field
    already present) makes no changes to those entries regardless of counter values.'
  - Post-migration recall ordering (sorted by state_rank, -score, id) produces 
    identical results to pre-migration ordering (state_rank, -confidence, id) 
    when all counters are 0.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Provide a migration path for existing memory entries to gain the new score and counter fields without changing behavior.

### In Scope
- Migration function that backfills score=confidence, counters=0
- Idempotency guarantee
- Order-preservation proof (score sorts identically to confidence when counters are 0)

### Out of Scope
- Score computation logic (P2-02)
- State machine changes (P2-01)
- New recall slot logic (P2-04)

## Domain
serve/memory/