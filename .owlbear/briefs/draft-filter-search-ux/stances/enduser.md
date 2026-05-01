# End-User Stance — Filter/Search UX (Task 1232)

## User Experience Stance

The filter panel design is structurally sound — expandable panel above columns, AND combinator, badge indicator. But badge-only active-filter communication creates a **filtered-view blindness** risk at this scale (1200+ tasks). The user's primary confusion moment isn't "how do I filter" — it's "why am I seeing fewer tasks than I expect?" hours after they set a filter and forgot.

The strongest UX improvement this design can make without adding complexity: **a persistent result count** ("142 / 1,247 tasks") adjacent to the toggle button. This communicates filtered state in one glance, costs zero additional interaction, and doubles as the accessibility live-region content.

## Usability Reasoning

### 1. Discoverability — Placement is correct, awareness is the gap

The decided location (above columns, inside `KanbanBoard`) is the natural scan target — users look at the top of a content area for controls. The toggle button with badge is appropriate for access frequency (filtering is intermittent, not constant). **The gap is not finding the filter — it's recognizing that filtering is active after time passes.** Badge "(2)" communicates dimensionality but not impact. A result count communicates impact.

### 2. Interaction Flow — Immediate feedback is achievable

Expand → set → see results in columns immediately. Client-side filtering with all data in memory makes this instant. No friction in the core flow.

**Caution:** The panel should remain compact enough that columns stay visible when expanded. Not a specific pixel budget — but the principle is: the user must see at least the top cards of each column while the panel is open. If 4 controls stack vertically, that principle fails on smaller viewports. A horizontal layout (text input + priority dropdown + tag selector + blocked toggle on one or two rows) preserves column visibility.

### 3. Active Filter Communication — Result count is the minimum viable signal

The decisions log has an inconsistency (D3 says "Chips row + task count" but context.md locks "badge only"). Taking the user's stated constraint (badge only, no chips row), the result count becomes the cheapest high-value addition:

- **"142 / 1,247"** next to the toggle button — always visible when filters are active
- Communicates subset-ness without expanding the panel
- Disappears (or shows "1,247 / 1,247") when no filters are active
- Serves as the `aria-live` region content for screen reader users

This is not a chips row. It's a single text element. Compatible with the badge-only decision.

### 4. Reset/Clear — Expand-to-reset is acceptable given result count

If the result count is present, users always know filters are active. The friction of expanding-to-reset is acceptable because the user has already been informed. Without result count, expand-to-reset is hostile (user must discover a problem before they can solve it). **Recommendation:** if result count is rejected, then a clear affordance on the collapsed toggle becomes necessary.

### 5. Edge Cases

- **All-zero filtered state:** Empty columns are an intentional structural invariant — not broken. But the user needs to distinguish "no tasks match my filter" from "the board is empty." The result count ("0 / 1,247 tasks") handles this unambiguously. No board-spanning banner needed.
- **No-tags state:** Tag control hides when no tags exist in data — good progressive disclosure. No UX concern.
- **Live polling refresh:** Filtered results can change under the user without interaction (polling updates task data). The result count and column contents will shift. This is expected and acceptable — the same behavior occurs without filtering. No special handling needed beyond ensuring recomputation is cheap.

### 6. Accessibility

- **aria-live region:** Announce result count after filter changes ("Showing 142 of 1,247 tasks"). Debounce text input announcements (300ms after typing stops).
- **aria-expanded:** On toggle button, reflecting panel state.
- **Focus management:** When panel expands, move focus to first control (text input). When panel collapses, return focus to toggle button.
- **Labels:** Each filter control needs an explicit `<label>` or `aria-label`. The blocked toggle needs "Show only blocked tasks" not just "Blocked."

## Key Trade-offs

| Choice | Benefit | Cost |
|--------|---------|------|
| Result count added | Eliminates filtered-view blindness | One additional text element to maintain |
| Horizontal panel layout | Columns stay visible during filtering | Tighter space per control on narrow viewports |
| No chips row (confirmed) | Less visual noise, simpler implementation | Less detail about *which* filters without expanding |
| Badge-only dimensionality | Compact, unobtrusive | Must be paired with result count to communicate impact |

## Warnings

1. **Without result count, the badge-only design fails the "forgot I filtered" scenario.** This is the single most important UX risk in the design. A user who filtered 3 hours ago and scrolls through a sparse board will not glance at a small "(2)" badge and connect it to their missing tasks.

2. **Panel height on small viewports.** If the filter panel grows to 3+ rows (e.g., many tags wrap), it will obscure columns. Keep controls inline and tag multi-select in a dropdown/popover rather than inline chips.

3. **Tag selector at scale is deferred, not absent.** If the board eventually has 30+ distinct tags, a flat multi-select becomes a scrolling list. A type-to-filter within the tag dropdown is a trivial addition that should be noted for future work even if not built now.

## Confidence

0.76

Reduced from initial 0.85 because: (a) the decisions log inconsistency on chips/badge means the result-count recommendation may be re-litigating a settled point, and (b) the tag-overflow concern is speculative given no evidence of large tag taxonomies in current data.
