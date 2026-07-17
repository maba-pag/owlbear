---
id: 1938
title: 'P1-05: Memory storage health'
status: build
priority: medium
created: 2026-07-17T02:31:34.851802+02:00
updated: 2026-07-17T02:33:38.521227+02:00
tags:
  - phase-1
  - scope:memory
  - integrity
parent: 1945
depends_on: []
ac:
  - Given malformed memory files and three readable files sharing one UUID, 
    memory health returns unreadable paths and the complete duplicate path set 
    while normal entry loading retains its current canonical-selection behavior.
  - Given readable pending, curated, approved, contested, disputed, stale, and 
    deleted entries with unique UUIDs, memory health reports healthy.
  - A memory health read leaves memory paths, bytes, and mtimes unchanged.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Expose unreadable memory records and complete duplicate-UUID path sets without changing memory lifecycle semantics or canonical loading.

## Scope
In scope: the memory engine's read-only health result and public diagnostic method. Out of scope: memory purge, lifecycle mutation, Cockpit aggregation, and UI behavior.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the workspace-health spec and accepted design. Canonical lifecycle literals come from `MemoryState` in the memory package.

## Proof Guidance
Use a focused real-filesystem memory check plus the existing lifecycle regression surface. Add durable coverage only for a meaningful unreadable-path, duplicate-set, or non-mutation regression not already protected.