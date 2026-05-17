# Context — Cockpit Decisions Tab

## Problem Statement

The cockpit is a single-view kanban board with no multi-tab/route architecture. Decision requests (DRs/ARs) are embedded in the sidecar panel and a status-bar popover — functional but secondary. Users discover blocked tasks on the kanban board but must interact with DRs through small, embedded widgets rather than a dedicated workspace. Resolved DRs are invisible. The cockpit doesn't feel like a complete ops dashboard.

This is the pathfinder feature: establishing the multi-tab navigation infrastructure that at least two more planned tabs (Ideas Notebook, Memory) will also use.

## Current State

- **Backend:** `GET /api/decisions/pending` (pending only), `POST /api/decisions/{id}/resolve`, SSE `decisions-changed` events. No endpoint for resolved or all decisions.
- **Frontend:** `DecisionViewport` component in sidecar, `DRStatusIndicator` badge/popover in status bar, `ResolveModal` for resolution. No dedicated route, no list-detail layout, no resolved DR viewing.
- **Navigation:** Single nav-rail button (kanban), single route (`/`). No tab/route system at the top level.
- **Planned tabs behind this:** Ideas Notebook, Memory tab, possibly Search/Cross-refs.

## Active Tensions

- **Layout proportionality:** With 1–5 pending DRs, a permanent two-column split may be heavier than needed. Simpler patterns (list with click-to-detail, expandable rows) should be evaluated. This is an approach question for Phase 2.
- **Component rework:** Moving sidecar/popover components into a full-page tab layout is reimplementation, not reuse. Expect meaningful rework of DecisionViewport and potentially ResolveModal.
- **"Pluggable" scope:** Must mean a routes array + nav items list, not a dynamic plugin framework. Three planned tabs don't justify abstraction beyond that.

## Outcomes (Locked)

### Deliverable P1 — Tab Shell

1. **Multi-tab/route architecture** — nav-rail with N entries, React Router route structure, kanban moved into tab slot
2. **Skeleton decisions tab** — placeholder page, validates that future tabs slot in by adding a route + nav entry
3. **Validation gate:** other tab modules (Memory, Notebook) can start implementing in parallel

### Deliverable P2 — Decisions Content

1. **Decisions list** — pending DRs displayed in a list (pending only for V1; resolved deferred to fast-follow)
2. **Detail view** — full DR body, metadata, resolution controls
3. **Resolution flow** — response type selection, notes field, submit (reuses existing backend)
4. **Pending DR count** — badge or indicator on the decisions nav-rail entry

### Scope Boundaries

- **In:** Tab system infrastructure, decisions list + detail, pending-only filtering, resolution flow, pending count indicator
- **Out:** Task context panel, resolved DR browsing (fast-follow), kanban-side cross-nav sender, deep-link receiver, DR creation from cockpit, quick templates, threaded history

## Project Type

`existing-feature/refactor` — decisions infrastructure exists on both backend and frontend; the work is about elevating them to first-class tab status and establishing the multi-tab navigation pattern.
