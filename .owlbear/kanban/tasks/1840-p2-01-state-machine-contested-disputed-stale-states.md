---
id: 1840
title: 'P2-01: State machine — contested, disputed, stale states'
status: research
priority: critical
created: 2026-05-24T19:00:51.542397+02:00
updated: 2026-05-24T19:00:51.542397+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on: []
ac:
  - MemoryState enum includes `contested`, `disputed`, `stale` values. 
    `_state_rank_for_list` ordering places contested at recall-visible rank 
    (same tier as curated), and disputed/stale at excluded rank (same tier as 
    deleted).
  - 'MemoryEngine supports curator-initiated resolution: contested→approved, disputed→approved,
    stale→approved via a resolve method. Attempts to resolve from non-resolvable states
    (pending, approved, curated, deleted) raise TransitionError.'
  - Recall filtering (in tools.py recall_memory) excludes entries with state 
    disputed or stale alongside existing exclusions of deleted and pending. 
    Entries with state contested remain in recall results.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Add three new lifecycle states to the memory engine and define their recall visibility and curator resolution transitions.

### In Scope
- MemoryState enum additions (contested, disputed, stale)
- state_rank ordering for new states
- Recall visibility rules (contested=visible, disputed/stale=excluded)
- Curator resolution transitions to approved

### Out of Scope
- Assessment counter fields (P2-02)
- Score computation (P2-02)
- Confirmation cycle logic (P2-06)
- Slot-efficiency auto-transition (P2-05)

## Domain
serve/memory/