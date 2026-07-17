---
id: 1947
title: 'P1-11: Coherent memory cache mutation'
status: build
priority: medium
created: 2026-07-17T03:04:14.374374+02:00
updated: 2026-07-17T03:04:43.890454+02:00
tags:
  - phase-1
  - scope:memory
  - concurrency
  - integrity
parent: 1951
depends_on:
  - 1946
ac:
  - 'AC-1: Given purge interleaved with an mtime-triggered public get_entries reload,
    both calls complete and the returned entries and ID lookups correspond to files
    remaining in the memory directory.'
  - 'AC-2: Given an ordinary mutation interleaved with reload, both calls complete
    and subsequent public reads expose the persisted post-mutation entry without index
    loss or duplication.'
  - 'AC-3: Given pending and non-pending delete requests after synchronization is
    introduced, pending deletion removes its file while non-pending deletion persists
    a deleted tombstone.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Shared memory cache and ID-to-path state remains coherent across reload, purge, and ordinary mutation threads.

## Scope
In scope: serialization of the mtime check, reload, index reads/replacement, and mutation paths.

Out of scope: purge eligibility, Cockpit API behavior, and frontend behavior.

## Contract Authorities
- Shared cache and index owner: `MemoryEngine`.
- Concurrency design: OpenSpec Design decision 2.

Proof guidance: run focused public-engine concurrency checks with scheduling controlled below the calls, plus an existing memory-engine downstream-impact scan.