# End User Stance — Archival UX (Task 1231)

_Produced by the End User panelist. Reviewed through one Critic cycle._

---

## User Experience Stance

The modal trigger, the conditional refs show/hide, and the parse-on-submit approach are all correct UX decisions. However the spec leaves five concrete user-facing risks either unaddressed or under-specified. The design is implementable but will create friction and accessibility failures if these are not resolved before the builder task is written.

---

## Usability Reasoning

### 1. Plain-text refs: the in-modal discovery gap (not the lookup cost)

The D4 reversal from autocomplete to plain text is defensible on proportionality grounds — this flow is rare. The framing error in my initial draft was "user must look up IDs externally." That is unproven; the task list is already in memory client-side.

The actual concern is narrower: **the plain-text input field gives the user zero discovery affordance from within the modal.** There is no list, no hint, no example format. The user staring at an empty text box marked "refs" must already know: (a) task IDs are integers, (b) multiple IDs are comma-separated, and (c) what the target task's ID actually is.

The 422 path through the engine is specific (`archival_refs required`, `task not found`, `self-reference`, `cycle detected`), and the route forwards these via `detail=exc.user_message`. But that only helps if the frontend surfaces the error message string — not just an error state. The spec does not require the modal to render the error message text.

**Required spec addition:** placeholder text on the refs input ("e.g., 1230, 1229") and a requirement that 422 `detail` strings are rendered as human-readable text inside the modal (same pattern as ResolveModal's `setError` renders).

Additionally: the engine checks for self-reference and dependency cycles in archival_refs. Both produce specific 422 errors that users will encounter when typing their own task's ID or entering a chain that would form a loop. The modal must render these messages verbatim — they are not generic validation errors.

### 2. Stale refs on reason-switch: implementation must explicitly clear

If the user selects `deprecated`, types refs "1230", then changes reason to `dropped`, the refs field hides. The spec does not say whether the refs value clears from React state or persists hidden.

This is a contingent implementation bug hypothesis, not a proven contract hole — the submit handler *may* correctly exclude hidden-field refs from the payload. But "may" is not enough. The builder needs explicit guidance on one of two approaches:
- **Clear on switch:** `setRefs("")` whenever reason changes to a no-refs reason. User loses their typed value. Simple.
- **Preserve in state, exclude from payload:** Keep the value, but submit logic must gate on `fieldVisible`. Risk: the payload exclusion must be explicitly coded.

Either works. The spec must pick one. The simpler (clear on switch) is recommended because it eliminates the hidden-state complexity entirely and cannot accidentally send stale refs.

### 3. Submit-disabled without inline guidance: discoverability failure

The user prompt spec confirms: "Submit button (disabled until form is valid)." This is a common pattern but a known anti-pattern when unaccompanied by any inline signal.

A user who selects `deprecated` but has not yet typed refs will see a grey button and no explanation. The cognitive model is broken at exactly the step where refs appear — first-time users will not know why submit is blocked.

**Minimum required:** a hint below the refs field when it is visible, such as "Required — enter at least one task ID." This costs one line of UI and eliminates the guessing loop. A soft inline message near the button ("Please select a reason" when no reason is chosen) covers the other disabled state.

### 4. Accessibility: ResolveModal is a structural precedent, not an a11y model

The ResolveModal precedent correctly establishes the component pattern: `useState` for form state, async submit, inline error state, `role="dialog"`. It does not provide a focus trap, `aria-modal="true"`, or `aria-labelledby`. Calling ResolveModal a sound a11y baseline would be wrong.

The ArchivalModal must implement independently:
- `role="dialog"` + `aria-modal="true"` (prevents screen readers from escaping the overlay)
- `aria-labelledby` pointing to a visible modal title element
- Focus placed on the reason dropdown on open (first interactive element)
- Focus trap: Tab cycles within the modal; Escape closes it

This is not a breaking departure from the ResolveModal pattern — it is an improvement over it. The spec should name these requirements explicitly rather than delegating to "model on ResolveModal."

### 5. Dropdown ordering: minor, but reducible cognitive cost

Current proposed order: `completed, deprecated, dropped, duplicate, wontfix`

This mixes positive-resolution (completed), redirection (deprecated, duplicate), and rejection (dropped, wontfix) in an order that is neither frequency-ranked nor semantically grouped. The refs-requiring reasons (deprecated, duplicate) land in the middle — when a user picks one and sees the refs field appear, they must scan back to understand the relationship.

Recommended order: `completed → dropped → wontfix → deprecated → duplicate`
- Positive resolution first (most common end state)
- No-refs rejection reasons grouped
- Refs-requiring reasons last — the conditional field appears beneath them, which is spatially predictable

This is a minor UX improvement with zero implementation cost beyond reordering a constant array. Not a blocker.

### 6. Hardcoded reason list: silent config drift risk

D4 chose to hardcode the five default reasons in the frontend to avoid the BoardOut API change. The engine reads `config.pipeline.archival_reasons`, which can be overridden per project. If a board's config differs from the hardcoded frontend list, users will see incorrect dropdown options and potentially trigger unknown-reason 422 errors.

This is a known, accepted tradeoff (D4's rationale: "defaults are stable"). The brief should explicitly document this as a deferred limitation, not leave it implicit, so it surfaces in future reviews.

---

## Key Trade-offs

| Decision | UX Impact | Stance |
|----------|-----------|--------|
| Plain text refs over autocomplete | Known friction, acceptable for rare flow — but needs placeholder and error surfacing | Accept with mitigation required |
| Hardcoded frontend reason list | Silent drift risk if config customized | Accept with explicit limitation documented |
| Conditional refs show/hide | UX-correct (avoids ERR_ARCHIVAL_REFS_FORBIDDEN) | Strong support |
| Submit-disabled pattern | Requires inline guidance to be usable | Accept with guidance required |
| ResolveModal as precedent | Structural only — a11y must be independently implemented | Partial; not an a11y model |

---

## Warnings

1. **Self-reference and cycle 422 errors must be rendered verbatim.** These are non-obvious errors that users will hit. Generic "error" state is insufficient.
2. **Stale refs on reason-switch must be resolved in the builder task spec.** Pick clear-on-switch or explicit payload exclusion. Do not leave it to builder inference.
3. **Focus trap is not optional.** A modal without a focus trap is keyboard-inaccessible for all users who tab-navigate.
4. **D4 hardcoding assumption should be documented as a known limitation** in the brief, not treated as permanent.

---

## Confidence

**0.76**

High confidence on items 3, 4, and the stale-refs spec gap. Moderate confidence on plain-text friction (the actual severity depends on whether the board's task-list is surfaced near the modal — not confirmed from the code evidence). Item 6 (hardcoded list drift) is low-severity but structurally valid.
