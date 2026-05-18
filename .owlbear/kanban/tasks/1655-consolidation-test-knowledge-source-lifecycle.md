---
id: 1655
title: 'Consolidation test: knowledge source lifecycle'
status: backlog
priority: needed
created: 2026-05-18T03:11:28.669033+02:00
updated: 2026-05-18T03:11:32.446726+02:00
tags:
  - scope:knowledge
  - scope:mcp-knowledge
  - consolidation-test
parent: 1650
depends_on:
  - 1651
  - 1654
  - 1652
ac:
  - 'AC-1: Integration test exercises the full source lifecycle: create source → refresh
    with known `RefreshResult` outcomes → verify `list_sources` returns honest `last_checked_at`/`last_refreshed_at`
    timestamps and health fields → `remove_source` deletes vectors and cascades SQLite
    data leaving no orphans'
  - "AC-2: Test confirms cross-outcome coherence: `last_checked_at` set by O2 conditional
    refresh logic is visible in O1's `list_sources` response; `remove_source` returns
    accurate deletion counts matching the source's document/chunk/entity footprint"
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Scope

**In-scope:** Integration verification across O2 refresh honesty (#1651), O1 health exposure (#1654), and O4 remove_source (#1652).

**Out-of-scope:** O3 retype (gated on research outcome in #1653).