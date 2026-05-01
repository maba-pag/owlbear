# Synthesis — Archival UX (Task 1231)

_Mode: converge. Active stances: architect (0.87), enduser (0.76). Date: 2026-05-01._

---

## Summary

Both panelists accept the core design: modal on `→ archived`, reason dropdown (conditional
`completed` filter, hardcoded list), conditional refs field (show only for
`deprecated`/`duplicate`), plain-text refs parsed at submit into `list[int]`, and
modal-local error state matching the `ResolveModal` pattern. All M1/D4/D5 decisions hold.

The architect surfaces one **critical backend finding** (CockpitView validation gap)
absent from the brief and from the enduser stance. The enduser surfaces five **frontend
spec gaps** (UX mitigations + accessibility) absent from the architect stance. Neither
finding contradicts the other; together they define what the brief is still missing.

---

## Convergences

| Topic | Agreed position |
|-------|----------------|
| Modal trigger | Only on `→ archived`; not `→ done` |
| Conditional refs show/hide | Show only for `deprecated`/`duplicate`; single ternary; UX-correct, not over-engineering |
| Refs input type | Plain text; parsed to `list[int]` at submit; client-side non-numeric guard before submit |
| Archival reasons source | Hardcoded five defaults; D4 rationale accepted |
| `terminal_status` source | Hardcode `"done"`; D5 rationale accepted (both note silent-wrong risk for non-default boards) |
| 422 error surfacing | Modal stays open; error rendered inline; `detail` string from route forwarded as human-readable message |
| OCC / 409 | Surfaced inside modal (not board-level `moveError`); matches `ResolveModal` precedent |
| ResolveModal as structural precedent | Component shape, `useState` form state, `async handleSubmit` — accepted as structural model only |
| `MoveRequest` extension safety | Adding declared optional fields with defaults is backwards-compatible under `extra="forbid"` |

---

## Disagreements

### T1 — CockpitView.move_task validation gap (architect only; enduser silent)

**Architect (critical):** `CockpitView.move_task` (engine.py:3292) is currently a bare
pass-through. The archival validation helpers (`_validate_move_archival_for_archive` etc.)
live on `AgentView` and are never called on the cockpit path. Closing only the HTTP API
gap (MoveRequest + route) leaves the view layer unenforced: any API caller can write
invalid archival data.

**Required addition to brief AC:** `CockpitView.move_task` must add a validation block —
reason-required check, refs matrix, completed-requires-done, ref existence, self-ref
guard, cycle guard — mirroring the inline pattern used by `CockpitView.edit_task`. The
route must not contain this logic.

**Enduser stance:** Does not address. Not a contradiction — outside UX scope.

**Resolution needed:** None from user — the architect finding is factually grounded (line
3292 verified) and unambiguously blocks correct archival semantics on the cockpit path.
This is a required AC addition.

---

### T2 — OCC snapshot prop wiring (architect only; enduser silent)

**Architect:** The modal must receive `taskUpdated` as a frozen prop captured at
context-menu-open time. It must NOT re-read `task.updated` from a live reference that
polling may advance while the modal is open. The existing state machine already sets up
the correct boundary; the implementation must wire it explicitly.

**Enduser stance:** Does not mention polling / snapshot isolation.

**Resolution needed:** None — architect finding is unambiguous. Brief must specify that
`expectedUpdated` is passed as a prop frozen at modal-open time.

---

### T3 — Refs field UX mitigations (enduser requires; architect partial)

**Enduser (required additions):**
1. Placeholder text on refs input (`e.g., 1230, 1229`) — zero-affordance gap in plain
   text field.
2. 422 `detail` strings rendered verbatim inside modal — self-reference and cycle errors
   are non-obvious; generic "error" state is insufficient.

**Architect:** Acknowledges client-side non-numeric guard but does not require placeholder
or verbatim error rendering.

**Tension level:** Low. Architect does not contradict these; they are additions, not
conflicts. Both items are straightforward to specify and implement.

**Resolution needed:** None — both mitigations are cheap and the enduser case is sound.
They should be added to the builder task AC.

---

### T4 — Accessibility requirements (enduser only; architect silent)

**Enduser:** `ResolveModal` is a structural precedent only; it does not provide a focus
trap, `aria-modal="true"`, `aria-labelledby`, or focus placement on open. The
`ArchivalModal` must implement these independently.

Required:
- `role="dialog"` + `aria-modal="true"`
- `aria-labelledby` → visible title element
- Focus placed on reason dropdown on open
- Focus trap: Tab cycles within modal; Escape closes

**Architect stance:** Does not mention accessibility.

**Tension level:** None — architect does not oppose. This is a required spec addition.

---

### T5 — Stale refs on reason-switch (enduser only; architect silent)

**Enduser:** If user types refs under `deprecated` then switches reason to `dropped`,
the refs field hides. The spec does not say whether the React state value clears or
persists hidden. The submit handler may incorrectly include it.

Two valid approaches:
- **Clear on switch** (`setRefs("")` when reason changes to no-refs reason) — simpler;
  recommended by enduser.
- **Preserve in state, exclude from payload** — requires explicit payload-gate code.

**Architect stance:** Does not address.

**Resolution needed:** User must choose. Enduser recommends clear-on-switch. This is a
builder-guidance decision, not a design decision — either is correct if specified.

---

### T6 — Submit-disabled inline guidance (enduser only; architect silent)

**Enduser:** Disabled submit button with no inline hint is a known anti-pattern. When
refs field is visible but empty, user sees no explanation for why Submit is blocked.

**Required:** Hint text below refs field when visible ("Required — enter at least one
task ID") and a soft hint near button when no reason is selected.

**Architect stance:** Does not address.

**Tension level:** None. Cost is minimal; should be spec'd explicitly.

---

### T7 — Dropdown ordering (enduser recommendation; architect silent)

**Enduser:** Current alphabetical order (`completed, deprecated, dropped, duplicate,
wontfix`) mixes resolution types. Recommended order: `completed → dropped → wontfix →
deprecated → duplicate` — positive resolution first, refs-requiring reasons last (refs
field appears beneath them; spatially predictable).

**Architect stance:** Does not address.

**Resolution needed:** Minor. User may accept or override. Zero implementation cost beyond
reordering the constant array.

---

### T8 — Hardcoded reason list: document limitation explicitly (enduser; architect silent)

**Enduser:** D4's "defaults are stable" rationale is accepted, but the risk of silent
config drift should be documented as an explicit known limitation in the brief, not left
implicit.

**Architect stance:** Notes the tradeoff in the trade-offs table but does not require
documentation.

**Resolution needed:** Low-stakes. Should be a single "Known Limitations" note in the
brief.

---

## Open Questions

| # | Question | Who must decide |
|---|----------|----------------|
| OQ1 | Stale refs on reason-switch: **clear-on-switch** or **preserve + payload-gate**? Enduser recommends clear-on-switch. | User |
| OQ2 | Dropdown order: current alphabetical or enduser-recommended grouped order? | User (minor) |
| OQ3 | Brief "Known Limitations" section: add one to capture D4/D5 hardcoding drift risks explicitly? | User (low-stakes) |

---

## Recommendation

**Consolidated design direction:** The brief is implementable but requires these additions
before the builder task is written:

**Required (non-negotiable):**
1. `CockpitView.move_task` validation block — reason, refs matrix, completed-requires-done,
   ref existence, self-ref, cycle (architect T1).
2. `expectedUpdated` passed as frozen prop at modal-open time; must not re-read from
   polling-updated task reference (architect T2).
3. Refs input placeholder `e.g., 1230, 1229` (enduser T3).
4. 422 `detail` strings rendered verbatim in modal, including self-reference and cycle
   errors (enduser T3).
5. `aria-modal`, `aria-labelledby`, focus placement on open, Tab focus trap, Escape
   closes (enduser T4).
6. Builder spec must explicitly choose stale-refs handling (enduser T5) — recommend
   clear-on-switch.
7. Inline guidance when submit is disabled (enduser T6).

**Recommended (low cost):**
8. Grouped dropdown order: `completed → dropped → wontfix → deprecated → duplicate`
   (enduser T7).
9. Explicit known-limitations note on D4/D5 hardcoding drift (enduser T8).

**Confidence: 0.88**

Grounded in two verified stances plus the brownfield source read (D6). The architect's
CockpitView finding is the highest-confidence addition (line 3292 verified). The enduser
items are structurally sound; the only unverified variable is whether ResolveModal's
existing error state already renders `detail` verbatim — the builder should confirm this
and close the gap if not.
