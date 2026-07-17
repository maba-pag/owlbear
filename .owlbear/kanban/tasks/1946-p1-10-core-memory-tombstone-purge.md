---
id: 1946
title: 'P1-10: Core memory tombstone purge'
status: build
priority: medium
created: 2026-07-17T03:04:09.242165+02:00
updated: 2026-07-17T03:04:43.944403+02:00
tags:
  - phase-1
  - scope:memory
  - maintenance
  - data-safety
parent: 1951
depends_on: []
ac:
  - 'AC-1: Given deleted entries at the cutoff and newer than the cutoff plus a non-deleted
    entry, the public preview operation counts the at-cutoff entry as eligible, counts
    the newer deleted entry as too_recent, reports deleted_total for those two tombstones,
    and leaves the filesystem unchanged.'
  - 'AC-2: Given min_age_days=0, the public purge operation removes the deleted entries,
    preserves the non-deleted entry, and returns purged, skipped, and failed counts
    that reconcile with the classified deleted set.'
  - 'AC-3: Given one eligible unlink failure and one eligible file already absent,
    purge continues, reports the unlink failure as failed, reports the absent desired
    state as purged, and leaves failed entry state available for retry.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
MemoryEngine previews and performs age-based best-effort tombstone purge through one eligibility authority.

## Scope
In scope: core eligibility, one UTC cutoff per request, protected physical deletion, and reconciled outcome counts.

Out of scope: cache synchronization, HTTP routes, Cockpit UI, and changes to ordinary memory deletion behavior.

## Contract Authorities
- OpenSpec capability: `memory-tombstone-purge`.
- Memory state, timestamp, path, and mutation authority: `MemoryEngine`.
- Physical deletion safety authority: `owlbear_memory.storage.delete_entry`.

Proof guidance: run focused pytest at the public MemoryEngine boundary; control clock and selected storage outcomes below the engine, then scan existing memory deletion checks for downstream impact.