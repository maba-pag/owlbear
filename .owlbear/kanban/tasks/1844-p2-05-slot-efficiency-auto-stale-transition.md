---
id: 1844
title: 'P2-05: Slot-efficiency — auto-stale transition'
status: research
priority: needed
created: 2026-05-24T19:01:24.904500+02:00
updated: 2026-05-24T19:01:24.904500+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on:
  - 1840
  - 1841
ac:
  - 'Engine function `check_slot_efficiency(entry: MemoryEntry) -> bool` returns True
    when `entry.didnt_use_count > STALE_THRESHOLD × max(entry.outstanding_count +
    entry.unremarkable_count, 1)`. Uses the named constant STALE_THRESHOLD (50).'
  - When check_slot_efficiency returns True and entry state is in {approved, 
    curated, contested}, a transition method moves state to stale. Entries 
    already in stale, disputed, deleted, or pending state are unaffected (no 
    error raised).
  - The transition method returns the updated MemoryEntry (with state=stale and 
    updated_at refreshed) when a transition occurs, or the unchanged entry when 
    no transition is needed.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Implement the slot-efficiency check that auto-transitions entries to stale when didnt_use dominates.

### In Scope
- check_slot_efficiency() predicate function
- Auto-transition to stale when predicate fires
- Guard against double-transition or invalid-state transition
- Uses STALE_THRESHOLD constant from P2-02

### Out of Scope
- Defining the stale state itself (P2-01)
- Counter increment logic (P2-07)
- Assessment tool integration (P2-07)

## Domain
serve/memory/