# End-User Debate Log — Filter/Search UX (Task 1232)

## Cycle 1

### Draft Position Summary

Six-point UX stance covering discoverability (badge-only insufficient), interaction flow (panel must be compact ~60-80px), active filter communication (need result count), reset/clear (badge should quick-clear), edge cases (all-zero board looks broken, 50+ tag overflow), accessibility (aria-live, aria-expanded, labels).

### Critic Challenges (6 challenges, 5 blind spots)

1. **Critical — Decision inconsistency.** Draft argues badge-only is insufficient, but the brief artifacts disagree with each other: context.md locks badge-only, decisions.md D3 records "Chips row + task count update." Stance is arguing from an inconsistent authority set.

2. **Moderate — Location asserted not demonstrated.** "Right location" claim is ungrounded. No toolbar region exists today; Shell already has a status bar with a task-count slot. Certainty is unfounded.

3. **Moderate — Panel height threshold arbitrary.** 60-80px claim has no user evidence. Board already scrolls at multiple levels (workspace, horizontal board, vertical columns). Viewport measurements absent.

4. **Moderate — Quick-clear overreach.** Clear-all is noted as still open in research notes, not a settled requirement. Draft escalates "expand-to-reset friction" without evidence this user base needs it.

5. **Moderate — All-zero "broken" framing overstated.** Empty columns are a designed structural invariant, tested and locked. Calling it "broken" smuggles a different semantic model.

6. **Moderate — Tag overflow speculative.** No evidence of 50+ tags or long tag names in actual data. Tag control hides when no tags exist — the verified edge case is absence, not abundance.

**Blind spots identified:**
- Live polling changes filtered results without user action
- Performance/rerender cost at 1200+ tasks with text input debounce
- Task 1225 board-split sequencing risk
- No-tags state (tag control disappears) unaddressed
- Keyboard focus management for panel expand/collapse missing

### Refinements Applied

| Original claim | Revision | Reason |
|----------------|----------|--------|
| Badge-only insufficient (absolute) | Badge-only creates risk; result count is cheapest mitigation | Acknowledge decision lock; recommend rather than demand |
| Toggle above columns is "right location" | Location is decided; focus on whether it works structurally | Stop asserting correctness of a locked decision |
| Panel must be 60-80px max | Panel should keep columns visible (principle, not pixel value) | Arbitrary threshold removed |
| Badge should quick-clear | Expand-to-reset acceptable IF result count is present | Conditional rather than absolute |
| All-zero board looks broken | All-zero is designed; result count distinguishes empty-board from empty-filter | Respect structural invariant |
| 50+ tags need sub-search | Noted as future defensive measure, not current requirement | Acknowledged speculation |
| (missing) Focus management | Added: focus to first control on expand, return to toggle on collapse | Incorporated blind spot |
| (missing) Live polling | Added: result count shifts under polling — acceptable, no special handling | Incorporated blind spot |

### Critic Confidence in Original Position

0.38 (high pressure)

### Post-Refinement Assessment

Position is now grounded in decisions, acknowledges authority conflicts, makes recommendations conditional on trade-offs rather than absolute demands. Confidence raised from speculative ~0.85 to calibrated 0.76.
