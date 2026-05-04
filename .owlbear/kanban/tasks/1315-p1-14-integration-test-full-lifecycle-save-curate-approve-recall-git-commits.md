---
id: 1315
title: 'P1-14: Integration test — Full lifecycle (save → curate → approve → recall
  + git commits)'
status: research
priority: important
created: 2026-05-04T01:32:27.514360+00:00
updated: 2026-05-04T01:34:54.327724+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1309
- 1311
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Integration test exercises full lifecycle: save -> list -> read -> curate (with scope) -> approve -> recall
- [ ] Verifies state at each step: pending -> curated -> approved
- [ ] Verifies recall returns the approved entry to the scoped agent in body-only format
- [ ] Verifies recall excludes the entry from non-scoped agents
- [ ] Verifies git: no commit on save, batch commit after curation, batch commit after approval
- [ ] Test passes end-to-end against the real MCP tool handlers

## Scope

- In: end-to-end integration test covering all layers
- Out: consumer wiring verification (manual), performance testing