---
id: 1658
title: Cockpit Ideas Notebook — freeform markdown tab backed by 
  .owlbear/ideas.md
status: backlog
priority: nice-to-have
created: 2026-05-18T17:38:48.428527+02:00
updated: 2026-05-18T17:42:39.149432+02:00
tags:
  - feature
  - cockpit
parent:
depends_on:
  - 1638
  - 1666
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief

Add an \"Ideas\" tab to the Cockpit — a freeform markdown scratchpad backed by `.owlbear/ideas.md`. Provides capture and re-reading of pre-task ideas without leaving the dashboard. Value is cockpit co-location alongside VS Code.

## Scope

**Backend:** GET/PUT `/api/ideas` endpoints, `atomic_write` import from kanban, create-on-first-write, `get_ideas_path` DI dependency.

**Frontend:** `IdeasPage` with textarea + preview toggle, explicit save, dirty-state indicator, unsaved-changes guard (route nav + beforeunload), default-to-edit mode.

**External-edit awareness:** Re-fetch on `visibilitychange` + route activation. Clean → silent update. Dirty → conflict notice with Overwrite / Discard & Reload buttons.

**Housekeeping:** Update `atomic_write` docstring to generic framing.

## Dependencies

- #1638 (Tab System) must land first

## Out of Scope

- Auto-save, multiple files, agent integration, CockpitProvider isolation (owned by #1638), file-watcher/real-time sync

## Source

Brief: `.owlbear/briefs/draft-cockpit-ideas/brief.md`
Decisions: `.owlbear/briefs/draft-cockpit-ideas/decisions.md`

[[2026-05-18T17:42:39+02:00]]
## Planning
### Decomposition: Cockpit Ideas Notebook
- Tasks created: 7 (6 implementation + 1 consolidation test)
- Dependency layers: 3
- Phase: 1–3

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1660 | P1-01: Backend Ideas API — GET/PUT /api/ideas with DI and atomic_write | needed | #1638 | phase-1, scope:cockpit, backend |
| 1661 | P1-02: atomic_write docstring — generic framing | important | #1638 | phase-1, scope:kanban, housekeeping |
| 1662 | P2-01: IdeasPage core — edit mode, API client, save, dirty state | critical | #1638, #1660 | phase-2, scope:cockpit-web, frontend |
| 1663 | P2-02: IdeasPage — markdown preview toggle | important | #1638 | phase-2, scope:cockpit-web, frontend |
| 1664 | P2-03: IdeasPage — unsaved-changes guard | important | #1638 | phase-2, scope:cockpit-web, frontend |
| 1665 | P2-04: IdeasPage — external-edit awareness and conflict resolution | important | #1638 | phase-2, scope:cockpit-web, frontend |
| 1666 | consolidation test: Ideas Notebook end-to-end | needed | #1660, #1662, #1663, #1664, #1665 | phase-3, scope:cockpit-web, consolidation-test |

### Dependency Graph
```mermaid
graph TD
  1638[#1638 Tab System]
  1660[#1660 Backend API]
  1661[#1661 atomic_write docstring]
  1662[#1662 IdeasPage core]
  1663[#1663 Preview toggle]
  1664[#1664 Unsaved-changes guard]
  1665[#1665 External-edit awareness]
  1666[#1666 Consolidation test]
  1658[#1658 Parent]

  1638 --> 1660
  1638 --> 1661
  1638 --> 1662
  1638 --> 1663
  1638 --> 1664
  1638 --> 1665
  1660 --> 1662
  1662 --> 1666
  1663 --> 1666
  1664 --> 1666
  1665 --> 1666
  1660 --> 1666
  1666 --> 1658
```
