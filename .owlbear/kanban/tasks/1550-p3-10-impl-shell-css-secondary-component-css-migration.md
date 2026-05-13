---
id: 1550
title: 'P3-10: impl — Shell.css + secondary component CSS migration'
status: research
priority: important
created: 2026-05-13T18:43:23.937036+00:00
updated: 2026-05-13T18:43:23.937036+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1542
  - 1543
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Shell.css token migration to agnostic names, context menu PDS surface/shadow/radius styling, filter panel PDS token styling, DetailTab/ActivityTab token migration, `styles.ts` `rowStyleForState()` deletion and replacement with `[data-state]` CSS selectors
- **Out:** Token architecture (done in P1-02 #1543), PDS component adoption for native inputs

## Acceptance Criteria

- AC-1: Shell.css migrated to agnostic `--pds-*` token names with existing responsive breakpoints preserved
- AC-2: Context menu styled with PDS `background-surface`, `shadow-md`, `radius-md` tokens; filter panel styled with PDS tokens for background, border, and spacing
- AC-3: DetailTab and ActivityTab styled with agnostic tokens; `styles.ts` `rowStyleForState()` replaced by CSS `[data-state]` selectors and the file deleted
- AC-4: Board container uses `gap: var(--pds-spacing-md)` between columns and `overflow-x: auto` for horizontal scroll

Complexity waiver: 4 AC covers one failure domain (CSS token migration across secondary components). Splitting individual component token renames into separate tasks would make the migration less verifiable as a coherent pass.

Proof bundle: behavioral