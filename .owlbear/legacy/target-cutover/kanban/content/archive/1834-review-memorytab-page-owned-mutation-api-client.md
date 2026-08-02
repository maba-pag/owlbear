---
id: 1834
title: Review MemoryTab page-owned mutation API client
status: archived
priority: medium
created: 2026-05-24T12:05:05.086598+02:00
updated: 2026-05-24T23:32:49.433010+02:00
tags:
  - scope:cockpit-web
  - memory
  - api-boundary
  - standardization
  - discussion
parent: 1773
depends_on: []
ac:
  - Inventory MemoryTab-owned fetch/error parsing against existing Cockpit api 
    client modules.
  - Decide whether a dedicated memories API client should own endpoint URLs, 
    response typing, and mutation error translation.
  - Any approved change preserves current Memory approve/edit/delete UX, OCC 
    handling, validation field messages, and pending-count updates.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
MemoryTab owns its mutation transport inside the route component. It defines `mutationFetch()`, parses mutation error payloads locally, throws an ad-hoc object containing `ApiError`, `payload`, and validation messages, and calls raw endpoint URLs for `/api/memories/{id}/approve`, `/api/memories/{id}/edit`, and `/api/memories/{id}/delete` directly from handlers.

## Evidence
- Code surface: `serve/cockpit/web/src/pages/MemoryTab.tsx` (`parseValidationErrors`, `parseMutationErrorPayload`, `mutationFetch`, `handleApprove`, `handleDelete`, `handleEditSave`).
- Existing API-client pattern: `serve/cockpit/web/src/api/tasks.ts`, `serve/cockpit/web/src/api/decisions.ts`, `serve/cockpit/web/src/api/ideas.ts`, `serve/cockpit/web/src/api/repair.ts`, and `serve/cockpit/web/src/api/cleanup.ts` keep endpoint and error translation out of page components.
- Historical context: archived #1493 centralized task/decision clients before the Memory route existed; archived #1670/#1672 added the Memory backend/frontend lifecycle but left the frontend mutation client inside `MemoryTab.tsx`.

## Observed User Impact
This is primarily a maintainability and boundary risk rather than a current visual defect. Memory is one of Cockpit's core operator workflows, and page-local transport code makes it easier for future changes to drift from the shared `ApiError`/typed-client pattern, duplicate OCC and validation handling, or test page behavior through implementation details instead of a stable API wrapper.

## Boundary
This is an audit finding only. Do not implement without explicit user approval. The review should decide whether Memory should gain a `src/api/memories.ts` module and whether list polling/error parsing should also be standardized, while preserving the current 409 refresh, 404 removal, 422 field-message, pending-badge delta, and promotion-message behavior.

## User Decision
Approved direction: extract Memory approve/edit/delete mutation transport and error translation into a dedicated frontend API client module, while keeping page-owned UI state and interaction flow in `MemoryTab`.

Implementation must preserve the current Memory UX, OCC handling, validation field messages, 404 removal behavior, pending-count updates, and promotion messaging.

## Implementation Outcome
Completed by extracting Memory approve/edit/delete mutation transport and error translation into `src/api/memories.ts`, while keeping page-owned UI state and interaction flow in `MemoryTab`.

Evidence: full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped; frontend build passed; editor diagnostics reported no errors in `MemoryTab.tsx`.
