# Architect Debate Log — Archival UX (Task 1231)

**Date:** 2026-05-01
**Cycles:** 1 (Critic challenges resolved in one pass)

---

## Cycle 1

### Draft Position Submitted to Critic

Five claims:
1. MoveRequest extension is backwards-compatible (zero risk)
2. Route needs no guard logic; engine is the validation authority
3. OCC semantics require snapshot at modal-open time (explicit modal prop)
4. `list[int]` type is correct and safe throughout
5. No missing structural concerns

### Critic Response (Confidence: 0.23, Pressure: high)

**Claim 1 — Minor.** The backwards-compatibility claim holds for runtime behavior (existing callers still validate), but "zero risk" is too strong — the API surface expands. Evidence: mutation.py:26 MoveRequest, research-notes.md.

*Assessment: Partially correct. The Critic is right that the API surface changes — that's intentional. The claim is sound for the backwards-compatibility question (existing callers don't break). Language refined from "zero risk" to "zero backwards-compatibility risk for existing callers."*

**Claim 2 — Critical.** The Critic challenged that validation lives in `AgentView`, not engine, and questioned whether CockpitView uses it.

*Assessment: Correct and critical. Verified by reading source.*

- `KanbanEngine.move_task()` (line 1093): NO archival validation — writes archival_reason/archival_refs directly
- `_validate_move_archival_for_archive()` defined at line 1992 (AgentView method)
- Called at line 2828 (AgentView.move_task) and line 3011 (AgentView.end_work)
- `CockpitView.move_task()` (line 3292): bare pass-through, `engine.move_task()` directly, NO validation call

This means the cockpit path has zero archival validation. Sending `{status: "archived", archival_reason: null}` through the extended route would be accepted silently.

**Position update:** Claim 2 was wrong. "Engine is the validation authority" is false. Validation authority is the VIEW LAYER (AgentView). CockpitView.move_task must add archival validation inline before calling engine.move_task(). The route remains correct as a pass-through — the gap is in CockpitView, not the route.

**Claim 3 — Moderate.** Critic correctly identified that KanbanBoard.tsx already snapshots `taskUpdated` at context-menu-open time. "Modal-open time" framing was imprecise.

*Assessment: Correct refinement. The snapshot boundary is already established by the existing state machine. The architectural requirement is precise: modal receives `taskUpdated` from KanbanBoard state (frozen at context-menu open), not a live `task.updated` reference.*

**Claim 4 — Moderate.** Critic correctly flagged that "no structural risk" overstated the safety of frontend parsing. Plain text → `list[int]` normalization contract is undefined.

*Assessment: Correct. The risk is bounded at the frontend parsing step but real. Position updated to require explicit normalization contract: trim whitespace, skip empty tokens, reject non-numeric input client-side before submit.*

**Claim 5 — Moderate.** Critic correctly identified that known open questions (error locality, 409 in modal, hardcode risks) were documented but swept under "no missing concerns."

*Assessment: Partially correct. These are accepted design decisions, not open gaps. But naming them explicitly is better than claiming no concerns exist. Position updated to name them as closed accepted tradeoffs.*

**Blind spots identified by Critic:**
- Did not audit the actual cockpit move call path before asserting validation authority — VALID
- Did not define refs normalization contract — VALID
- Did not reconcile snapshot boundary with existing state machine — VALID
- Ignored non-default board config risks — VALID, documented as accepted

---

## Position Updates After Cycle 1

| Claim | Original | Revised |
|-------|----------|---------|
| 1 | "Zero risk" | "Zero backwards-compatibility risk for existing callers; surface expands as intended" |
| 2 | "Engine is validation authority; no guard" | "CockpitView.move_task has no archival validation; must add it inline. Route is correct as pass-through." |
| 3 | "Modal must snapshot at open time" | "Existing state machine already snapshots via `taskUpdated`; modal must receive that frozen value as prop" |
| 4 | "No structural risk" | "Risk is bounded at frontend parsing step; normalization contract must be defined explicitly" |
| 5 | "No missing concerns" | "Known accepted tradeoffs named explicitly: hardcoded reasons, hardcoded terminal_status, modal-local errors, 409 in modal" |

---

## Exit Condition

Exiting after Cycle 1. The Critic's most significant challenge (Claim 2) was verified directly from source code. The revised position is stable. A second cycle would not change the core findings — the CockpitView.move_task gap is confirmed by source, and the recommended fix (add inline validation to CockpitView.move_task) is clear.
