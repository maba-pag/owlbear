# First-Principles Stance — Task 1231 Archival UX

**Confidence: 0.81**

---

## Irreducible Claim

The engine needs `archival_reason` populated when a task is archived via the cockpit. That's the entire problem. One field. One write path. Everything else is solution shape, not requirement.

---

## Assumptions That Aren't Load-Bearing

### 1. The modal is inherited UI convention, not derived from the requirement

The problem is "field missing at write time." A modal is one way to collect it. So is a required inline dropdown in the context menu itself before it commits, an inline form that replaces the menu row, or a two-step confirmation panel. The modal was never derived — it was the first recognizable shape. Challenge: does an internal single-user tool with a known five-value enum need a full modal dialog? The field has a small, bounded option set. This could be an inline step.

### 2. `archival_refs` UX is disproportionate to the cases that need it

Only `deprecated` and `duplicate` require refs. These are rare archival outcomes in a personal task system. The proposed task-search/autocomplete tag-input is significant UX investment for two enum values in a single-user tool. Challenge: a plain text input for refs (comma-delimited IDs, no autocomplete) is simpler and satisfies the engine contract. Autocomplete is borrowed from multi-user PM tools.

### 3. `BoardOut` extension is assumed but not derived

The frontend needs to know the valid reason list to render the dropdown. The session notes plan to extend `BoardOut`. But `archival_reasons` has a fixed default (5 values) and config-level overrides are rare. Challenge: is it simpler to hardcode the defaults in the frontend and only surface a config-driven override when `BoardOut` already differs? This avoids a backend model change.

### 4. The `completed` precondition is invisible in the proposed shape

`completed` requires the task to already be at `terminal_status`. A modal that includes `completed` in the dropdown but rejects it server-side forces the user to learn via a 422. The framing treats this as a frontend filtering question ("filter dynamically or let server 422?") but it's actually a design smell: the engine has a meaningful precondition that the proposed shape does not surface. Challenge: does `completed` belong in the archival modal at all, or should it be a distinct "mark complete then archive" flow?

---

## What Is Actually Necessary

1. Intercept the "→ archived" transition before the HTTP call.
2. Require `archival_reason` (enum, five values) from the user.
3. Conditionally require `archival_refs` for deprecated/duplicate only.
4. Pass both fields through MoveRequest → route → `move_task()`.
5. Reject or exclude `completed` unless the engine precondition is visibly handled.

The wire-path backend fix (MoveRequest + route) is non-negotiable. The frontend shape, the `BoardOut` extension, and the refs UX complexity are all choices — not requirements.
