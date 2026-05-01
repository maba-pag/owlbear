# Brief — Archival UX in Cockpit (Task 1231)

_Phase 2 — Mediation. Approved: 2026-05-01._

---

## Problem

When a user moves a task to `"archived"` in the Cockpit, no archival metadata is
collected or persisted. The engine (`KanbanEngine.move_task`) and cockpit view
(`CockpitView.move_task`) already accept `archival_reason` and `archival_refs`, but the
HTTP API (`MoveRequest`) and frontend (`handleTransitionClick`) never supply them. Every
human-initiated archival lands with `archival_reason=None` and `archival_refs=[]`.

This matters because `archival_reason` drives downstream dependency resolution:

- `dropped` / `wontfix` → dependers flagged blocked
- `deprecated` / `duplicate` → dependers flagged redirect
- `completed` → dependers ok

Without it, all human-archived tasks look like silent drops to the engine.

---

## Scope

**Project type:** `existing-feature/refactor` — engine and cockpit view are complete. HTTP
API layer (`MoveRequest`, route) and frontend (`handleTransitionClick`, new `ArchivalModal`)
need extending.

**Investment tier:** Tool — standard depth, full Brief.

**Trigger scope:** Only `status → "archived"` requires archival metadata. Moving `→ "done"`
is a plain status change with no archival semantics.

---

## Existing Code (verified baseline)

| Layer | State |
|---|---|
| `KanbanEngine.move_task()` | Complete — accepts `archival_reason: str \| None`, `archival_refs: list[int] \| None` |
| `CockpitView.move_task()` | Accepts and passes through to engine — **no archival validation block** |
| `MoveRequest` (`routes/mutation.py:26`) | Only `status` + `updated`; `extra="forbid"` |
| Route `POST /tasks/{id}/move` | Calls `view.move_task()` without archival params |
| `handleTransitionClick` (`KanbanBoard.tsx:82`) | Sends `{status, updated}` only |
| `BoardOut` (`models.py:8`) | No `archival_reasons`, no `terminal_status` |

**Reason ↔ refs validation matrix (engine-verified):**

| Reason | Refs | Engine error |
|---|---|---|
| `completed` | **forbidden** | `ERR_ARCHIVAL_REFS_FORBIDDEN`; also requires `task.status == "done"` |
| `dropped` | **forbidden** | `ERR_ARCHIVAL_REFS_FORBIDDEN` |
| `wontfix` | **forbidden** | `ERR_ARCHIVAL_REFS_FORBIDDEN` |
| `deprecated` | **required** | `ERR_ARCHIVAL_REFS_REQUIRED` |
| `duplicate` | **required** | `ERR_ARCHIVAL_REFS_REQUIRED` |

---

## Backend Changes

### B1 — `MoveRequest` extension (`routes/mutation.py`)

Add two optional fields:

```python
archival_reason: str | None = None
archival_refs: list[int] = []
```

Backwards-compatible under `extra="forbid"` — declared optional fields with defaults
do not break existing callers.

### B2 — Route pass-through (`routes/mutation.py`, move handler)

Pass `req.archival_reason` and `req.archival_refs` to `view.move_task()`. No validation
logic in the route — validation belongs in the view layer.

### B3 — `CockpitView.move_task` validation block (`engine.py`)

Add an archival validation block following the inline pattern used by
`CockpitView.edit_task`. Must cover:

- Reason required when `status == "archived"`
- Refs forbidden for `completed`, `dropped`, `wontfix`
- Refs required for `deprecated`, `duplicate`
- `completed` requires `task.status == "done"` before the move
- Refs existence — each ref ID must exist in the board
- Self-reference guard — task cannot reference itself
- Cycle guard — ref chain cannot loop back to this task

Raise the appropriate engine error codes. Route forwards these as 422 with `detail`.

---

## Frontend Changes

### F1 — `ARCHIVAL_REASONS` constant

Hardcoded ordered list (in `KanbanBoard.tsx` or a shared constants file):

```ts
const ARCHIVAL_REASONS = ["completed", "dropped", "wontfix", "deprecated", "duplicate"];
```

Order rationale: positive resolution first; refs-requiring reasons last (refs field
appears when the bottom two are selected — spatially predictable).

### F2 — `ArchivalModal` component (new file: `components/ArchivalModal.tsx`)

Structural model: `ResolveModal.tsx` — same component shape. Does **not** inherit
`ResolveModal`'s accessibility; the new modal must implement a11y independently.

**State:**

```ts
reason: string        // selected reason, "" initially
refs: string          // plain text, "" initially
error: string | null
isSubmitting: boolean
```

**Renders:**

- Visible title element (for `aria-labelledby`)
- Reason `<select>` dropdown: populated from `ARCHIVAL_REASONS`; `completed` option is
  hidden when `task.status !== "done"` (hardcoded terminal check against `"done"`)
- Refs `<input type="text">`: visible only when reason is `"deprecated"` or `"duplicate"`;
  placeholder `e.g., 1230, 1229`; hint text below: "Required — enter at least one task ID"
- Submit button: disabled when (a) no reason selected, or (b) refs required and refs
  field empty, or (c) `isSubmitting === true`
- Error display: inline below form; renders `error.detail` verbatim when present
  (verify `ResolveModal`'s detail handling; add explicit rendering to `ArchivalModal`
  if `ResolveModal` does not already surface `detail` verbatim)

**Behaviour:**

- Focus placed on reason dropdown when modal opens
- Tab / Shift+Tab cycle within modal only (focus trap)
- Escape closes modal without firing a move
- Stale refs: when reason changes from `deprecated` or `duplicate` to any other reason,
  call `setRefs("")` to clear refs state

**On submit:**

1. Set `isSubmitting = true`
2. Parse refs: `refs.split(/[,\s]+/).filter(Boolean).map(Number)` — reject if any token
   is `NaN`; show inline error before request fires
3. POST `{status: "archived", updated: expectedUpdated, archival_reason: reason, archival_refs: parsedRefs}` to `/api/tasks/{id}/move`
4. On success: close modal, trigger board refresh
5. On 422: set `isSubmitting = false`, display `error.detail` verbatim
6. On 409 (OCC stale): set `isSubmitting = false`, display modal-local stale-snapshot error
7. On any other error (404, network): set `isSubmitting = false`, display generic modal-local error

**Accessibility:**

- `role="dialog"` + `aria-modal="true"`
- `aria-labelledby` → the visible title element's id
- Tab and Shift+Tab cycle within modal only
- Escape key closes modal

### F3 — `handleTransitionClick` intercept (`KanbanBoard.tsx`)

When `targetStatus === "archived"`: open `ArchivalModal` instead of immediately
posting the move. Pass:

- `taskId` — the task being archived
- `taskStatus` — `task.status` at intercept time (for `completed` filter)
- `expectedUpdated` — `task.updated` **frozen at context-menu-open time**; must not be
  re-read from a polling-updated reference while the modal is open

---

## Acceptance Criteria

### Backend

- [ ] `MoveRequest` has `archival_reason: str | None = None` and `archival_refs: list[int] = []`; existing callers unaffected
- [ ] Move route passes `archival_reason` and `archival_refs` to `view.move_task()`
- [ ] `CockpitView.move_task` raises `ERR_ARCHIVAL_REASON_REQUIRED` (422) when `status == "archived"` and `archival_reason` is `None`
- [ ] `CockpitView.move_task` raises `ERR_ARCHIVAL_REFS_FORBIDDEN` (422) for `completed`, `dropped`, `wontfix` when refs are non-empty
- [ ] `CockpitView.move_task` raises `ERR_ARCHIVAL_REFS_REQUIRED` (422) for `deprecated`, `duplicate` when refs are empty
- [ ] `CockpitView.move_task` raises `ERR_COMPLETED_REQUIRES_DONE` (422) for `completed` when `task.status != "done"`
- [ ] `CockpitView.move_task` raises a validation error (422) for refs containing non-existent IDs, self-reference, or cycle
- [ ] Archiving `→ archived` with a valid reason and correct refs persists both fields on the task

### Frontend

- [ ] Clicking the `→ archived` transition in the context menu opens `ArchivalModal`; no move fires immediately
- [ ] `ARCHIVAL_REASONS` constant is ordered: `completed → dropped → wontfix → deprecated → duplicate`
- [ ] `completed` is hidden from dropdown when `task.status !== "done"`; shown when `task.status === "done"`
- [ ] Refs field is visible only when reason is `deprecated` or `duplicate`; hidden for all other reasons
- [ ] When reason switches from a refs-requiring reason to any other reason, refs state is cleared (`""`)
- [ ] Submit is disabled when no reason is selected
- [ ] Submit is disabled when refs field is required and empty
- [ ] Submit is disabled while a request is in-flight (`isSubmitting === true`)
- [ ] Non-numeric refs tokens are caught client-side; inline error shown before request fires
- [ ] On 422: modal stays open; `error.detail` text is displayed verbatim
- [ ] On 409: modal stays open; modal-local stale error message shown
- [ ] On success: modal closes; board refreshes
- [ ] `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to visible title element
- [ ] Focus placed on reason dropdown when modal opens
- [ ] Tab / Shift+Tab cycle within modal only (focus trap active)
- [ ] Escape closes modal without firing a move
- [ ] `expectedUpdated` is the value of `task.updated` frozen at context-menu-open time; not re-read from a polling-updated task reference

---

## Out of Scope

- Agent archival flow — no changes; agents supply `archival_reason` and `archival_refs` through their own path
- New endpoints — no new routes; existing `POST /tasks/{id}/move` is extended
- Task detail view — no archival UI on the detail panel (future task if needed)
- `BoardOut` extension with `terminal_status` or `archival_reasons` — decided against (D4, D5)
- Full cockpit/agent backend parity — `CockpitView.move_task` validation covers the archival gap only; general move-validation parity is a separate architectural concern

---

## Known Limitations

**Hardcoded `ARCHIVAL_REASONS`:** The five reasons reflect `PolicyConfig.archival_reasons`
defaults, which are stable across standard boards. If a board adds custom reasons via
config, the frontend `ARCHIVAL_REASONS` constant must be updated manually — there is no
runtime sync.

**Hardcoded `terminal_status = "done"`:** The `completed` dropdown filter assumes the
board's terminal status is `"done"`. If a board configures a different terminal status
(e.g., `"released"`), the filter will silently show `completed` when it should be
hidden. Any such board will need a frontend constant update.
