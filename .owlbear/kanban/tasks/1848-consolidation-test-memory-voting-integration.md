---
id: 1848
title: 'Consolidation test: memory voting integration'
status: backlog
priority: important
created: 2026-05-24T19:01:58.079687+02:00
updated: 2026-05-24T19:02:09.405964+02:00
tags:
  - phase-2
  - scope:memory
  - consolidation-test
parent: 1839
depends_on:
  - 1842
  - 1843
  - 1844
  - 1845
  - 1846
  - 1847
ac:
  - 'Integration test exercises full flow: create entries → recall with explore/challenge
    slot allocation → assess with all four bucket types → verify score updates, counter
    increments, state transitions (contested, disputed, stale), and recall exclusions
    match expected behavior.'
  - Test verifies migration on pre-existing entries (score field absent) 
    produces identical recall ordering to unmigrated confidence-based sort, and 
    subsequent assessments update scores correctly.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

End-to-end integration test verifying the full memory voting pipeline works across all subtask boundaries.

### In Scope
- Full lifecycle: save → recall (slot allocation) → assess → verify
- All bucket types exercised
- State transitions verified (contested, disputed, stale)
- Score computation verified end-to-end
- Migration scenario (legacy entries without score)
- Recall exclusion after state transitions

### Out of Scope
- Unit-level testing (covered by individual subtasks)
- Pipeline instruction verification (docs, not code)

## Domain
tests/