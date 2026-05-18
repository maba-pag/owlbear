---
id: 1666
title: 'consolidation test: Ideas Notebook end-to-end'
status: backlog
priority: needed
created: 2026-05-18T17:42:19.064317+02:00
updated: 2026-05-18T17:42:26.539084+02:00
tags:
  - phase-3
  - scope:cockpit-web
  - consolidation-test
parent: 1658
depends_on:
  - 1660
  - 1662
  - 1663
  - 1664
  - 1665
ac:
  - 'End-to-end flow: IdeasPage loads content from backend, saves edits via PUT, and
    reflects saved state (dirty indicator clears, save button disables)'
  - Preview toggle renders saved markdown content correctly after a save 
    round-trip
  - 'Conflict resolution flow: external edit detected on re-fetch triggers conflict
    notice; Overwrite keeps local content, Discard adopts server content'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Integration test verifying cross-task behavior between all Ideas Notebook subtasks:
- #1660 (Backend API)
- #1662 (Core page)
- #1663 (Preview toggle)
- #1664 (Unsaved-changes guard)
- #1665 (External-edit awareness)

## In Scope

- End-to-end backend ↔ frontend integration
- Cross-feature interaction (save + preview, dirty + guard, re-fetch + conflict)

## Out of Scope

- Unit-level behavior already covered by individual task tests