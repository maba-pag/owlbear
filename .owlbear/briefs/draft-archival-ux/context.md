# Context — Archival UX in Cockpit (Task 1231)

_Phase 1 — Discovery snapshot. Updated at moment boundaries._

## Problem

When a cockpit user moves a task to status `"archived"`, no archival metadata is
collected or persisted. The engine (`KanbanEngine.move_task`) and the cockpit view
(`CockpitView.move_task`) already accept `archival_reason` and `archival_refs`
parameters, but the HTTP API layer (`MoveRequest`) and the frontend
(`handleTransitionClick`) never supply them. The result: every human-initiated
archival lands with `archival_reason=None` and `archival_refs=[]`.

This matters because `archival_reason` drives downstream dependency resolution:
- `dropped`/`wontfix` → dependers flagged blocked
- `deprecated`/`duplicate` → dependers flagged redirect
- `completed` → dependers ok

Without it, all human-archived tasks look like silent drops to the engine.

## Existing Code — Verified

| Layer | State |
|-------|-------|
| `KanbanEngine.move_task()` | Accepts `archival_reason`, `archival_refs` |
| `CockpitView.move_task()` | Accepts and passes them through |
| `MoveRequest` (HTTP model) | Only `status` + `updated`; `extra="forbid"` blocks extra fields |
| Route `POST /tasks/{id}/move` | Calls `view.move_task()` without archival params |
| `handleTransitionClick` (frontend) | Sends `{status, updated}` only |
| `BoardOut` (`/api/board`) | Does **not** expose `archival_reasons` config list |

## Project Type

`existing-feature/refactor` — engine is complete; HTTP API and frontend need extending.

## Archival Reasons (config-defined)

Default set: `completed`, `deprecated`, `dropped`, `duplicate`, `wontfix`

Loaded from `config.pipeline.archival_reasons`; frontend needs this list to build a dropdown.

## Trigger Scope (verified)

Only moving to `"archived"` requires archival metadata. Moving to `"done"` is a regular
status transition with no archival semantics. The task description's mention of "moving
to 'done'?" is a mislabelling — the engine only archives on `status == "archived"`.

## Reason ↔ Refs Validation Matrix (from engine, verified)

| reason | refs allowed? |
|--------|--------------|
| `completed` | forbidden (ERR_ARCHIVAL_REFS_FORBIDDEN); also requires task at terminal_status |
| `dropped` | forbidden |
| `wontfix` | forbidden |
| `deprecated` | **required** (ERR_ARCHIVAL_REFS_REQUIRED) |
| `duplicate` | **required** |

UX implication: refs input must be **conditionally shown** — visible only when reason
is `deprecated` or `duplicate`.

## M1 — Confirmed Choices

- **Trigger**: Only `"→ archived"` selection (not `"→ done"`)
- **Reason field**: Required — user must pick before move fires
- **Refs field**: Include with task search/autocomplete (not plain text)
- **Scope**: Full stack — `MoveRequest` + route + frontend + `BoardOut`

## M2 — Outcomes (Locked)

### Best realistic outcome
- "→ archived" click opens a modal dialog
- Modal has: reason dropdown (all configured reasons), refs tag-input (visible only for `deprecated`/`duplicate`)
- Refs tag-input: type an ID, press Enter, validate against task list; can add multiple
- Move fires only when form is valid (reason selected, refs non-empty when required)
- Backend: `MoveRequest` extended with `archival_reason` + `archival_refs`; route passes them through
- `BoardOut` extended with `archival_reasons` list so frontend populates dropdown from config
- `completed` reason: shown in dropdown; if invalid (task not at terminal status), server returns 422 and modal surfaces the error

### Minimum viable win
- Modal collects reason (required) and refs (conditionally required)
- API gap closed (MoveRequest + route)
- BoardOut exposes archival_reasons
- Tag-input validates IDs exist (client-side or on-submit)

### Scope boundary
- No change to agent archival flow
- No new endpoint; extend existing `MoveRequest` and route
- No archival UI on the task detail view (out of scope for this task)

## Active Tensions (entering early challenge lane)

*Resolved — see decisions.md and research-notes.md I3, I4.*
