# Simplifier Stance — Task 1231 Archival UX

**Confidence: 0.80**

## Cut 1 — Drop `archival_reasons` from `BoardOut` (defer or eliminate)

Proposed change: add `archival_reasons: list[str]` to the `/api/board` response model so the
frontend can populate the dropdown dynamically.

**Cut it.** The default reason set (`completed`, `deprecated`, `dropped`, `duplicate`, `wontfix`)
is stable and hardcoded in the engine defaults. This is a single-user tool. Hardcode the 5 values
in the frontend. If the user ever customises `archival_reasons` via config, this is a one-line
follow-up. The current change adds: a new `BoardOut` field, a backend test suite addition, and a
live contract to maintain — all to solve a non-problem.

**Saving:** 1 model field, 1 schema test class, 1 API assertion, 1 frontend fetch dependency.

## Cut 2 — Replace tag-input-with-task-search with a plain text field

Proposed: refs tag-input that validates typed IDs against the task list in real time, with
autocomplete.

**Cut it.** `archival_refs` is required only for `deprecated` and `duplicate` reasons — rare paths.
Real-time task-list lookup + autocomplete + tag-input component is disproportionate to usage
frequency. Replace with a plain `<textarea>` or `<input>` accepting space- or comma-separated
integers. Server validates IDs and rejects unknowns via 422. Error surfaces in modal.

**Saving:** tag-input component (new), task-list validation fetch, autocomplete state management.

## Cut 3 — Always show refs field; remove conditional show/hide

Proposed: refs field conditionally visible based on selected reason (shown for
`deprecated`/`duplicate`, hidden for others).

**Cut it.** The forbidden/required constraint is already enforced server-side. Show the refs field
always, mark it "optional for most reasons". On submit, server returns 422 if refs are provided
for a forbidden reason or missing for a required one. The modal surfaces the error. This removes
an entire conditional rendering branch and its test cases.

**Saving:** conditional visibility logic, branch tests, client-side reason↔refs coupling.

---

## Minimal Scope That Closes the Real Gap

1. `MoveRequest`: add `archival_reason: str | None` and `archival_refs: list[int] | None`
2. Route: pass both to `view.move_task()`
3. Modal: reason `<select>` (hardcoded 5 options) + refs plain `<input>` (always visible) +
   422 error display
4. `handleTransitionClick`: intercept `"archived"`, open modal, fire on confirm

Four changes. No new API fields, no tag-input component, no conditional field logic.
