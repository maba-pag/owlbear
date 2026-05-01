# Research Notes — Archival UX (Task 1231)

_Phase 1 output for mediator. Separates verified findings, implications, and open
research questions._

---

## Verified Findings

### V1 — Three-layer API gap

| Layer | State | File |
|-------|-------|------|
| `KanbanEngine.move_task()` | Accepts `archival_reason`, `archival_refs` | `serve/kanban/src/owlbear_kanban/engine.py` |
| `CockpitView.move_task()` | Accepts and passes them through | same |
| `MoveRequest` | Only `status` + `updated`; `extra="forbid"` | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:26` |
| Route `POST /tasks/{id}/move` | Never passes archival params | `mutation.py:~130` |
| `BoardOut` | No `archival_reasons`, no `terminal_status` | `serve/cockpit/src/owlbear_cockpit/models.py:8` |
| `handleTransitionClick` | Sends `{status, updated}` only | `serve/cockpit/web/src/KanbanBoard.tsx:82` |

### V2 — Archival trigger

Only `status == "archived"` triggers archival in the engine. Moving to `"done"` is a
plain status change. The archival prompt should only appear when target is `"archived"`.

### V3 — Reason ↔ refs validation matrix (engine-verified)

| Reason | Refs allowed? | Notes |
|--------|--------------|-------|
| `completed` | **forbidden** | Also requires task at `terminal_status` first |
| `dropped` | **forbidden** | |
| `wontfix` | **forbidden** | |
| `deprecated` | **required** | Non-empty |
| `duplicate` | **required** | Non-empty |

Engine errors: `ERR_ARCHIVAL_REASON_REQUIRED`, `ERR_ARCHIVAL_REFS_REQUIRED`,
`ERR_ARCHIVAL_REFS_FORBIDDEN`, `ERR_COMPLETED_REQUIRES_DONE`.

### V4 — Frontend modal precedent: `ResolveModal`

`serve/cockpit/web/src/components/ResolveModal.tsx` is an existing modal:
`useState` for form state, `async handleSubmit` with inline fetch, error state, `role="dialog"`.
The new `ArchivalModal` should follow the same structural pattern.

### V5 — Frontend already has `task.status`

`KanbanBoard.tsx:46` uses `task.status` to look up valid transitions. The modal can
receive the task object and compare its status against `terminal_status` to filter
`completed` from the dropdown.

### V6 — Default archival reasons (config-verified)

Default set from `PolicyConfig.archival_reasons`: `completed`, `deprecated`, `dropped`,
`duplicate`, `wontfix`. These are stable. User chose to hardcode them in the frontend.

---

## Candidate Implications (for mediator deliberation)

### I1 — `MoveRequest` field addition is safe under `extra="forbid"`

Adding `archival_reason` and `archival_refs` as explicit optional fields will not break
existing callers — optional fields default to `None`/`[]`. The `extra="forbid"` only
blocks *undeclared* extra fields; adding declared optional fields is backwards-compatible.

### I2 — Refs text input: parse on submit, not on change

Comma/space-separated IDs entered as plain text should be parsed and trimmed at submit
time, not on every keystroke. `"1230, 1229"` → `["1230", "1229"]`. Server validates
existence; client doesn't need a pre-submit round-trip.

### I3 — Refs conditional show/hide is UX-correctness, not complexity

Showing the refs field when reason is `completed`/`dropped`/`wontfix` and the user fills
it in will cause a `ERR_ARCHIVAL_REFS_FORBIDDEN` 422. This is a bad UX. The conditional
show/hide is not over-engineering; it's correct behavior. Cost: one ternary.
(Simplifier recommended "always show"; this implication overrides that stance.)

### I4 — `terminal_status` needs frontend visibility

For the `completed` filter (filter it from dropdown when `task.status ≠ terminal_status`),
the frontend needs to know what `terminal_status` is. Two options:

**A) Add `terminal_status: str` to `BoardOut`** — trivially cheap (1 field from existing
`board_config()` call). Correct for all board configs.

**B) Hardcode `"done"` in the frontend** — same rationale as hardcoding reasons, but
riskier: if a board's terminal_status differs from "done", the filter is silently wrong.

**My read:** Option A is safer and costs almost nothing. But the user already chose to
hardcode reasons; mediator should confirm which pattern governs here.

---

## Open Research Questions (for mediator)

### Q1 — `terminal_status` in `BoardOut`: expose or hardcode?

See I4 above. Mediator should confirm whether `terminal_status` follows the
"hardcode stable defaults" decision (Option B) or gets added to `BoardOut` (Option A).

### Q2 — Refs parsing: strings or integers?

The engine's `archival_refs` is typed as `list[str]` in the view layer
(`CockpitView.move_task` signature). But the UI operates on task IDs which may be
displayed as numbers. Should `MoveRequest.archival_refs` be `list[int]` or `list[str]`?
Check the engine's actual internal type for refs.

### Q3 — Error handling scope in ArchivalModal

If the move fails with a 422, should the modal stay open (user can correct) or close
(user must retry)? `ResolveModal` closes on success; on error it stays open and shows
the error. Same pattern here.

### Q4 — 409 Conflict (OCC) in archival modal context

`KanbanBoard.tsx:92` handles move errors with `setMoveError`. If an OCC conflict
occurs mid-archival-modal, should it surface inside the modal or collapse to the
board-level error? `ResolveModal` does modal-local error; recommend same.

---

## Implementation Shape (confirmed post-M2)

**Backend:**
1. `MoveRequest` → add `archival_reason: str | None = None`, `archival_refs: list[str] = []`
2. Route → pass `req.archival_reason`, `req.archival_refs` to `view.move_task()`
3. `BoardOut` → add `terminal_status: str` (pending Q1 resolution)
4. `get_board` route → extract from `board_config()`

**Frontend:**
1. Hardcoded `ARCHIVAL_REASONS` constant (5 values)
2. `ArchivalModal` component (modelled on `ResolveModal`):
   - Reason dropdown (filtered: hide `completed` when task not at terminal_status)
   - Refs plain text input (conditional: visible only for `deprecated`/`duplicate`)
   - Submit → fires POST with `{status: 'archived', updated, archival_reason, archival_refs}`
   - Error display (modal-local, same as `ResolveModal`)
3. `handleTransitionClick` → intercept `targetStatus === "archived"`, open modal

**No changes to:**
- Agent archival flow
- `KanbanEngine` or `CockpitView` (already complete)
- Any new endpoints
