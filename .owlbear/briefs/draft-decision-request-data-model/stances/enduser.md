# End-User Stance — Decision Request Data Model

## User Experience Stance

The resolver is a work-unblocking tool, not a notification queue. Its job: present a real choice, capture a real answer, visibly resume blocked work. Two interaction speeds must coexist on the same surface without forcing the heavy path on clear cases or hiding deliberation tools from ambiguous ones.

---

## Usability Reasoning

### Decision Resolver

**Two modes, one surface:**

1. **Quick-confirm mode** — When a recommended option exists AND confidence spread is large (dominant option clearly ahead), the resolver pre-selects the recommendation and positions the Confirm button as the primary action. The user's path: open → verify recommendation → confirm. Two actions total.

2. **Full-compare mode** — When spread is low, no recommendation exists, or the user deselects the pre-selection, all options present at equal visual weight for deliberation. The user's path: open → read rationales → select → add notes → confirm.

The mode is determined by the data, not a toggle. The user can always override quick-confirm by selecting a different option.

**Option cards show (in priority order):**

1. Label + recommended badge (if applicable) — the first-read signal
2. Confidence value (numeric) — the user explicitly uses the spread to calibrate decision speed
3. Rationale (first sentence visible, expandable) — available for deliberation without requiring a click

**Free text** is always visible below options (a text input, not collapsed). It's optional but present — per locked decisions.

**Confirm** requires an option to be selected. Button disabled until selection exists.

### Action Resolver

Actions are fundamentally different from decisions: the user reports an outcome, not selects from agent-proposed options. Actions do NOT use option cards, confidence, or recommendation — those concepts don't apply to "what did you do?"

**Outcome buttons (direct selection, no pre-selection):**

- The specific states are an open design parameter, but the UX contract requires:
  - At least: completed-successfully, completed-with-issues, rejected/not-doing
  - All outcomes equally accessible in the initial view (no "more options" hiding)
  - Selecting an outcome that implies problems (issues, rejection) reveals a text area for explanation
  - Selecting "completed successfully" enables immediate confirm without notes

- One-step resolution: select outcome → confirm. Notes optional for success, encouraged for issues.

### Confidence Display

- **Show the number.** The user said "the higher the difference the faster I decide." They need to see 0.85 vs 0.32, not an abstract gradient.
- **Visual reinforcement:** Proportional bar or weight indicator alongside the number to make the spread scannable at a glance.
- **Three confidence states:**
  - High spread (clear winner): visual emphasis on the dominant option, quick-confirm mode activated
  - Low spread (close call): no emphasis on any option, full-compare mode, subtle "close call" indicator
  - Missing/zero confidence: hide confidence display entirely — options presented at equal weight with no numeric signal

### Information Hierarchy

| Level | Content | Purpose |
|-------|---------|---------|
| List | Title, kind badge, task ID, time-since-created, count badge (if multiple pending on same task) | Triage: which request to open first |
| Detail/resolver | Full summary, option cards OR outcome buttons, free text input, confirm button, "Show context" toggle | Resolution: make the decision |
| Extended context | Body markdown (toggle-revealed) | Deep context for complex cases only |

### Interaction Pattern

**Routed detail view.** Clicking a request navigates to a dedicated resolver page/view. The list is one back-navigation away.

Why not modal: modals interrupt spatial orientation and create dismissal anxiety ("did it save?").
Why not inline expansion: with 3+ options, rationale text, and free text, inline expansion causes severe layout churn in the list beneath.

Routed view gives: full width for option comparison, stable list when returning, clear URL-addressable state, natural keyboard flow (no trap focus management).

**Keyboard contract:** Tab through options (focus ring on cards), Space/Enter to select, Tab to free text, Tab to Confirm.

### Feedback Loop

**Immediately after confirm:**

1. Confirm button enters loading state (spinner/disabled) — the in-flight state
2. On success: view transitions to a "Resolved" confirmation state showing: selected option (or outcome), any notes entered, and conditional message:
   - If this was the last pending request on the task: "Task #{id} unblocked"
   - If sibling requests remain: "Request resolved — {n} remaining on Task #{id}"
3. After 2s or user action: navigate back to list (auto or via "Back to requests" link)

**Error handling:**

- Network/write failure: confirm button returns to enabled, inline error banner: "Resolution failed — try again"
- Stale (already resolved by another path): show "Already resolved" state with the existing resolution summary
- No silent failures, no ambiguous disappearances

---

## Key Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| Numeric confidence (not just visual) | User calibrates speed from exact spread; transparent about agent certainty | Feels more "technical"; users may over-anchor on small differences |
| Routed detail view (not modal/inline) | Stable layout, full resolution space, clear navigation | Extra navigation step; can't resolve while scanning the list |
| Quick-confirm pre-selection | Sub-5-second resolution for clear winners | Risk of rubber-stamping if user doesn't verify; agent trust assumed |
| Free text always visible | Low friction for adding judgment; honors locked decision | Adds visual weight to every resolution; might feel like a form |
| Actions without option cards | Clear semantic separation between "choose" and "report" | Two different resolver layouts to build and maintain |

---

## Warnings

1. **Quick-confirm is a trust accelerator.** If agent recommendations are frequently wrong, the pre-selection becomes a trap. Monitor: how often does the user override recommendations? If > 30%, disable quick-confirm.

2. **The "worth using" threshold is 10 seconds for clear cases.** If the routed-view navigation adds enough latency that clear-winner resolutions take longer than 10s, the system has failed its primary promise. Performance budget matters.

3. **5+ options is an agent smell, not a UI problem.** The UI should handle it (scrollable cards), but agent instructions should coach toward 2-4 options. If agents routinely generate 5+, that's a upstream quality issue.

4. **Action states are still open.** The UX contract (outcome buttons, notes-on-issue, immediate-confirm-on-success) is stable regardless of which specific states are chosen. But the states themselves must be finalized before implementation.

5. **Draft persistence is intentionally absent.** In a single-user, sub-30-second interaction system, auto-saving draft notes adds complexity for a near-zero real scenario. If the user navigates away, typed notes are lost. This is acceptable — and if it's not, it's a signal the interaction is too slow.

---

## Confidence

**0.74**

Strong position on interaction contract, information hierarchy, and feedback model. Reduced confidence from: action states still open (design parameter, not UX failure), and whether the two-mode approach (quick-confirm vs full-compare) adds implementation complexity that outweighs its value in a low-volume single-user system. The principle is sound; whether the mode-switching logic is worth building depends on request volume.
