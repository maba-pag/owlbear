# Decisions — Archival UX (Task 1231)

_Append-only. Chosen and rejected options with rationale._

## D1 — 2026-05-01 — Project Type

**Status quo:** Task 1231 says "design and implement".
**Decision:** `existing-feature/refactor` — engine + cockpit view are complete.
HTTP layer (`MoveRequest`, route) and frontend (`handleTransitionClick`, `BoardOut`)
need extending. No new engine work required.

**Chosen:** existing-feature/refactor
**Rationale:** Verified by reading `engine.py` (CockpitView.move_task already accepts
archival params), `mutation.py` (MoveRequest lacks them), `KanbanBoard.tsx` (no archival
collection), and `models.py` (BoardOut has no archival_reasons).

---

## D2 — 2026-05-01 — Investment Tier

**Status quo:** Scope is a 3-layer fix to one flow path (→ archived), internal tool.
**Decision:** Tool tier — standard M2, selective early-challenge panel (simplifier + firstprinciples), full Brief.
**Rationale:** Not throwaway (needs a real Brief). Not multi-consumer (Shared). Not external-facing (Production). Bounded but non-trivial because it touches API contract, route, and frontend UX state machine.

---

## D3 — 2026-05-01 — Confirmed M1 Answers

- **Trigger**: Only `"→ archived"` in context menu (not `"→ done"`)
- **Reason**: Required (user must select from configured list before move fires)
- **Refs**: Include with task search/autocomplete (not plain text input)
- **Scope**: Full stack — MoveRequest + route + frontend + BoardOut

---

## D4 — 2026-05-01 — Post-challenger decisions

**Refs UX:** Changed to plain text (comma-separated IDs, server validates).
**Chosen:** Plain text. **Rejected:** Tag-input with autocomplete.
**Rationale:** Rare path (only deprecated/duplicate); proportionality challenge from both
early challengers accepted. Server 422 for bad IDs is sufficient feedback.

**Reason list source:** Hardcoded in frontend (5 stable defaults).
**Chosen:** Hardcode. **Rejected:** Expose via BoardOut.
**Rationale:** Config-defined defaults are stable. Removing a backend model change and
API contract aligns with the scope-reduction stance.

**Completed filter:** Filter `completed` from dropdown when task.status ≠ terminal_status.
**Chosen:** Dynamic filter. **Rejected:** Always show + let server 422.
**Rationale:** User hits 422 after filling a form = bad UX. Cheap frontend guard.

**Conditional refs show/hide:** KEEP the conditional (override simplifier Cut 3).
**Chosen:** Show refs only for deprecated/duplicate. **Rejected:** Always show.
**Rationale:** Showing refs for reasons where they're forbidden risks ERR_ARCHIVAL_REFS_FORBIDDEN
422 after the user fills the field. One ternary is UX-correctness, not over-engineering.

---

## D5 — 2026-05-01 — terminal_status source for completed-filter

**Status quo:** `PipelineConfig.terminal_status` defaults to `"done"` but is configurable.
**Decision to make:** Frontend needs to know `terminal_status` to filter `completed` out of
the archival dropdown when the task has not yet reached terminal status.

**Options considered:**

- A: Add `terminal_status: str` to `BoardOut` — 1 read-only field, unconditionally correct
- B: Hardcode `"done"` in frontend — zero backend change; consistent with D4 "hardcode stable defaults" stance

**Chosen:** B — hardcode `"done"` in frontend
**Rationale:** Consistent with D4 decision to hardcode archival_reasons. OwlBear boards
use `"done"` as terminal status by convention. No backend contract change needed.

**Rejected:** A — adds a field not required today; D4 pattern covers this scope.

---

## D7 — 2026-05-01 — M4 direction confirmation

**All 6 required panel additions accepted:**
1. `CockpitView.move_task` validation block (reason-required, refs matrix, completed-requires-done, ref existence, self-ref, cycle guard)
2. `expectedUpdated` frozen prop at modal-open (not re-read from polling-updated reference)
3. Refs input placeholder text (`e.g., 1230, 1229`)
4. 422 `detail` strings rendered verbatim in modal
5. a11y: `aria-modal="true"`, `aria-labelledby`, focus on reason dropdown on open, Tab focus trap, Escape closes
6. Submit-disabled inline hint: "Required — enter at least one task ID" below refs field

**OQ1 — Stale refs:** clear-on-switch (`setRefs("")` when reason changes to no-refs reason)
**OQ2 — Dropdown order:** grouped: `completed → dropped → wontfix → deprecated → duplicate`
**OQ3 — Known Limitations:** add a paragraph to the brief noting frontend constants require update if config changes

---

## D8 — 2026-05-01 — Critic O15 pass results

**Pass 1 findings:**
- F1 minor: synthesis structural ambiguity (422 detail in convergences and tensions). Brief resolves by specifying explicitly. No design change.
- F2 minor: Brief should include conditional — verify if ResolveModal renders `detail` verbatim; add to ArchivalModal if not present.
- F3 nonsense: T5 stale-refs escalation vs de-escalation contradiction — resolved by D7 (clear-on-switch).
- F4 material: submit-disable contract never fully defined. **Added to Brief AC:** Submit disabled when (a) no reason selected, or (b) reason requires refs AND refs field is empty.

**Pass 2 findings:**
- P2-1 minor: CockpitView/AgentView backend parity gap — out of scope (D1). Brief notes validation block covers archival gap only.
- P2-2 material: No in-flight submit guard → double-submit risk. **Added to Brief AC:** `isSubmitting: boolean` state disables Submit during fetch.
- P2-3 minor: Network error after server commit — existing pattern limitation; board refresh handles reconciliation. No special AC.
- P2-4 minor: 404/task-gone — caught at route layer; falls to generic modal-local error. Existing pattern; no special AC.

**Net Brief additions from Critic:** isSubmitting guard, explicit submit-disable contract, conditional detail-rendering verification note.

---

## D6 — 2026-05-01 — archival_refs type correction (M3 brownfield read)

**Finding:** research-notes Q2 incorrectly stated CockpitView.move_task accepts `list[str]`.
**Corrected:** All layers use `list[int]`:
  - `models.py:453,487` — `archival_refs: list[int]`
  - `engine.py:978,1099` — `archival_refs: list[int] | None`
  - `CockpitView.move_task` — `archival_refs: list[int] | None`

**Impact:** `MoveRequest.archival_refs` → `list[int]`. Frontend parses comma-separated
plain text into integers at submit time. No other flow change required.
