---
id: 1544
title: 'P1-04: impl — card signal data model: type extension, DR cross-reference,
  signal computation'
status: research
priority: needed
created: 2026-05-13T18:42:22.319464+00:00
updated: 2026-05-13T18:42:22.319464+00:00
tags:
  - phase-1
  - scope:cockpit
  - data
  - frontend
parent: 1534
depends_on:
  - 1536
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Add `dep_status` to frontend `Task` type, implement `computeSignal()` function, wire DR cross-reference, remove `PRIORITY_COLORS` map and emoji badges
- **Out:** Card CSS rendering (separate task), backend API changes

## Acceptance Criteria

- AC-1: Frontend `Task` type includes `dep_status` field (string or null) consumed from the tasks API response
- AC-2: `computeSignal()` function accepts task data and pending-DR ID set, returns one of `"dr-pending"`, `"blocked"`, `"claimed"`, `"deps-unmet"`, `"ready"` following the specified precedence order
- AC-3: `PRIORITY_COLORS` map and emoji badges (⛔, ▶) removed from card rendering logic

Proof bundle: behavioral