---
id: 1841
title: 'P2-02: Model fields — assessment counters and score computation'
status: research
priority: critical
created: 2026-05-24T19:00:51.563620+02:00
updated: 2026-05-24T19:00:51.563620+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on: []
ac:
  - 'MemoryEntry has `outstanding_count: int` (default 0), `unremarkable_count: int`
    (default 0), `didnt_use_count: int` (default 0), and `score: float` fields. Named
    constants `OUTSTANDING_BOOST = 0.1`, `UNREMARKABLE_PENALTY = 0.01`, `STALE_THRESHOLD
    = 50` are defined in the memory engine module.'
  - 'Function `compute_score(confidence: float, outstanding_count: int, unremarkable_count:
    int) -> float` returns `confidence + (outstanding_count × OUTSTANDING_BOOST) -
    (unremarkable_count × UNREMARKABLE_PENALTY)`. Exported from owlbear_memory.'
  - MemoryEngine.save() initializes new entries with score = confidence and all 
    three counters = 0. Storage round-trip (write + read) preserves counter and 
    score values.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Add assessment counter fields and score computation to the memory model. Define named constants for scoring parameters.

### In Scope
- MemoryEntry fields: outstanding_count, unremarkable_count, didnt_use_count (int, default 0), score (float)
- Named constants: OUTSTANDING_BOOST=0.1, UNREMARKABLE_PENALTY=0.01, STALE_THRESHOLD=50
- compute_score() function
- MemoryEngine.save() initializes score=confidence, counters=0
- Storage serialization/deserialization of new fields

### Out of Scope
- New states (P2-01)
- Recall slot allocation (P2-04)
- Assessment tool (P2-07)
- Migration of existing entries (P2-03)

## Domain
serve/memory/