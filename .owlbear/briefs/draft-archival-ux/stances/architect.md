# Architectural Stance — Archival UX (Task 1231)

**Architect:** ideation-architect
**Date:** 2026-05-01
**Mode:** Stance (late domain panel)

---

## Architectural Stance

The proposed design is structurally sound at the MoveRequest and route layers, but contains a real validation gap in `CockpitView.move_task` that must be closed. The HTTP route pass-through is the correct architecture; the gap is one layer lower.

---

## Structural Reasoning

### 1. MoveRequest extension is backwards-compatible

Adding `archival_reason: str | None = None` and `archival_refs: list[int] = []` to a Pydantic model with `extra="forbid"` is safe for existing callers. `extra="forbid"` blocks undeclared fields; adding declared optional fields with defaults is transparent to clients that send only `{status, updated}`. The API surface expands as intended — this is not accidental and requires no guard.

### 2. The route must pass through — but CockpitView.move_task must validate

**This is the critical finding.** `CockpitView.move_task` (engine.py:3292) is a bare pass-through to `KanbanEngine.move_task()`, which also has no archival validation — it writes `archival_reason` and `archival_refs` directly to the task record without checking them.

The validation helpers (`_validate_move_archival_for_archive`, raising `ERR_ARCHIVAL_REASON_REQUIRED`, `ERR_ARCHIVAL_REFS_REQUIRED`, `ERR_ARCHIVAL_REFS_FORBIDDEN`, `ERR_COMPLETED_REQUIRES_DONE`) exist on `AgentView`, called from `AgentView.move_task` (line 2828) and `AgentView.end_work` (line 3011). They are **never called** on the cockpit path.

Therefore:
- The route MUST NOT contain validation logic (separation of concerns; the route is a serialization boundary)
- `CockpitView.move_task` MUST add archival validation before calling `engine.move_task()`
- The pattern to follow is `CockpitView.edit_task`, which already duplicates archival validation from `AgentView.edit_task` inline

The correct implementation adds a validation block to `CockpitView.move_task`:
- When `status == "archived"`: validate reason required, refs matrix, completed-requires-done, ref existence, self-ref guard, cycle guard
- When `status != "archived"`: raise `ERR_ARCHIVAL_FIELDS_FORBIDDEN` if archival fields are present

The task description says "pass those fields through to `view.move_task()`." This is correct at the route layer. But the view itself is incomplete.

### 3. OCC snapshot is already handled — but the modal must not break it

`KanbanBoard.tsx` already captures `taskUpdated` at context-menu-open time (stored in state). The `ArchivalModal` must receive this frozen value as a prop at modal-open time. It must NOT re-read `task.updated` from a live task reference that polling may update. If the board re-fetches while the modal is open and the modal uses the new `updated` value, the OCC guard is silently advanced — the concurrent update goes undetected.

The existing state machine already sets up the correct snapshot boundary. The implementation must wire it correctly.

### 4. Refs parsing normalization contract must be explicit

`archival_refs: list[int] = []` is correct throughout. Frontend parses comma-separated plain text at submit time. The normalization contract must be defined explicitly:
- Trim whitespace from each token
- Skip empty tokens
- Reject non-numeric tokens client-side before submit (prevent a 422 after form completion)

"No structural risk" in the initial draft was overclaimed. The risk is real but bounded at the frontend parsing step.

### 5. Known accepted tradeoffs are architectural decisions, not gaps

The following are documented and closed:
- **Hardcoded archival reasons**: consistent with D4; stable defaults
- **Hardcoded `terminal_status = "done"`**: accepted per D5; silently wrong for non-default boards, accepted as proportionate
- **Modal-local error state**: correct; board-level `moveError` doesn't apply to modal flows; matches `ResolveModal` precedent
- **409/OCC surfaced inside modal**: correct per research-notes Q4; modal stays open on error

---

## Key Trade-offs

| Decision | Chosen | Rejected | Risk |
|----------|--------|----------|------|
| Validation in route vs view layer | View layer (CockpitView) | Route guard | Coupling archival logic to HTTP layer |
| Validation duplication vs extraction | Duplicate inline (CockpitView pattern) | Extract to shared helper | Code drift between AgentView and CockpitView validators |
| Refs input | Plain text + client parse | Tag-input autocomplete | Non-numeric input reaches submit; mitigated by client-side guard |
| `terminal_status` source | Hardcode `"done"` | Expose via BoardOut | Silent filter failure on non-default boards |

---

## Warnings

1. **`CockpitView.move_task` must be extended, not just the route.** Closing only the HTTP API gap (MoveRequest + route) while leaving CockpitView.move_task as a bare pass-through means the archival validation contract is unenforceable via the cockpit. Any API caller (including tests) can write invalid archival data.

2. **Inline validation in CockpitView.move_task may drift from AgentView.** If new archival reason types are added to config, both AgentView and CockpitView validators must be updated. This is the cost of the existing duplication pattern.

3. **`expected_updated` in `CockpitView.move_task` is a required parameter** (line 3299). The route must pass `req.updated` as `expected_updated`. The MoveRequest field `updated: str` already exists; it must be wired through.

---

## Confidence

**0.87**

The gap in `CockpitView.move_task` is verified from source (line 3292 — no validation, bare engine pass-through). The backwards-compatibility claim is analytically solid. The OCC concern is real but the existing state machine already provides the snapshot boundary. Minor uncertainty: the exact shape of inline validation code that CockpitView.move_task needs is implementation detail, not architectural decision.
