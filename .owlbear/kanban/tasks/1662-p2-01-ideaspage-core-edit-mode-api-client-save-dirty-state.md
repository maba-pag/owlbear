---
id: 1662
title: 'P2-01: IdeasPage core — edit mode, API client, save, dirty state'
status: backlog
priority: critical
created: 2026-05-18T17:42:08.330672+02:00
updated: 2026-05-18T18:13:22.053660+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1658
depends_on:
  - 1638
  - 1660
ac:
  - IdeasPage mounts a textarea that loads content from GET `/api/ideas` and 
    defaults to edit mode (textarea visible and focused)
  - Save button triggers PUT `/api/ideas` with current textarea content; button 
    is disabled when content matches the last-saved baseline
  - Dirty-state indicator is visible when local textarea content differs from 
    the last-saved baseline; indicator clears after successful save
  - Empty textarea shows placeholder text (e.g. 'Capture ideas here...') when 
    content is empty — visible on first use and after clearing content
  - Cmd+S / Ctrl+S keyboard shortcut triggers save when textarea is focused and 
    content is dirty
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Includes creating the API client module at `serve/cockpit/web/src/api/ideas.ts` with `fetchIdeas()` and `saveIdeas()` functions using the existing `ApiError` pattern.

Page state is 100% local — no CockpitProvider extension required.

Route config entry for the tab system (#1638): path `/ideas`, lazy-loaded `IdeasPage`, nav-rail label "Ideas".

## In Scope

- `IdeasPage` component with textarea and save button
- API client module (`fetchIdeas`, `saveIdeas`)
- Dirty-state tracking (`content !== lastSavedContent`)
- Route config entry in #1638's route config array
- Loading state during initial fetch

## Out of Scope

- Preview toggle (separate task)
- Unsaved-changes guard (separate task)
- External-edit awareness (separate task)
- CockpitProvider modifications