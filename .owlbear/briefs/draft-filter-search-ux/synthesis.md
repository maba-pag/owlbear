# Synthesis — Filter/Search UX (Task 1232)

_Converge mode. Active stances: architect, enduser._

## Summary

Both stances agree on the core architecture: filter state as inline `useState` in `KanbanBoard`, a pure `filterTasks()` function as the single authority for filter semantics, a controlled `FilterPanel` component, and derived data computed inline (React Compiler handles memoization). The structural boundaries are clean and testable at every layer.

The primary tension is **active-filter communication**. The architect computes a dimension count (`activeCount`) for the badge but does not address how the user knows the *impact* of filtering. The enduser identifies "filtered-view blindness" as the top UX risk and proposes a result count ("142 / 1,247 tasks") as the minimum viable signal. Secondary tensions exist around accessibility requirements, panel layout orientation, and reset affordance.

## Convergences

| Point | architect | enduser |
|-------|-----------|--------|
| State placement | Inline `useState<FilterState>` in `KanbanBoard`, no custom hook | Does not challenge; implicitly accepts |
| Pure filter function | `filterTasks()` in `lib/filterTasks.ts`, unit-testable without React | Accepts; maps to "instant feedback" requirement |
| Controlled `FilterPanel` | Props-driven, owns only expand/collapse internally | Accepts; focuses on interaction details within the panel |
| Tags from full task set | `availableTags` derived from unfiltered `tasks` array | Endorses — prevents dead-end UX where AND-filtered tags vanish |
| Empty columns visible | Existing "No tasks" placeholder renders; no change needed | Agrees; notes result count disambiguates "filtered to zero" from "board empty" |
| Cancel drag / dismiss context menu on filter change | `useEffect` watching `filter` clears both | Not addressed, but no objection |
| No manual `useMemo` | React Compiler auto-memoizes; 1200 items × `.includes()` ≈ 0.1ms | Agrees filtering is instant at current scale |
| Polling refresh | Derived data recomputes automatically; no stale-filter bug | Agrees; same behavior as unfiltered board |
| Column height CSS is fragile | Warns `calc(100vh - 56px)` breaks when panel is added | Warns panel must not obscure column tops; same underlying concern |
| Testing layers | Unit (filterTasks), Component (FilterPanel), Integration (board flow) | Not detailed, but compatible with this strategy |

## Disagreements

### T1 — Result count display (high impact)

- **architect** (L56–60): Computes `activeCount` (number of active dimensions) for the badge. No mention of filtered-task count or total-task count displayed to the user.
- **enduser** (L23–33, L45–53): Identifies "filtered-view blindness" as the top UX risk. Proposes a persistent result count ("142 / 1,247 tasks") adjacent to the toggle button. Argues the badge communicates dimensionality but not impact, and that without result count, the design fails the "forgot I filtered 3 hours ago" scenario.

**Structural cost of adoption:** Low. The architect's inline derivation already has access to `tasks.length` (total) and `filteredTasks.length` (filtered). Displaying these is a single text element, no new state or component.

### T2 — Accessibility requirements (medium impact)

- **architect**: Not addressed. No `aria-live`, no focus management, no label guidance.
- **enduser** (L65–70): Specifies `aria-live` region for result count announcements (300ms debounce after typing), `aria-expanded` on toggle button, focus-to-first-control on expand, focus-return-to-toggle on collapse, explicit labels ("Show only blocked tasks" not just "Blocked").

**Note:** These are additive requirements that do not conflict with the architect's component structure. The controlled `FilterPanel` props interface accommodates them without modification.

### T3 — Panel layout orientation (low-medium impact)

- **architect** (L47–55): Specifies vertical flex container (panel above columns scroller) but does not prescribe internal panel layout.
- **enduser** (L37–39): Explicitly recommends horizontal control layout (one or two rows) to ensure column tops remain visible when panel is expanded. Warns that vertical stacking of 4 controls fails on smaller viewports.

**Note:** Not a structural conflict — the architect's outer layout is vertical (panel, then columns), which is compatible with a horizontal *internal* panel layout. The enduser is adding a constraint the architect left unspecified.

### T4 — Reset/clear affordance (low impact)

- **architect**: No mention of how users clear all filters.
- **enduser** (L55–58): Argues expand-to-reset is acceptable *only if* result count is present (user knows filters are active). If result count is rejected, a visible clear button on the collapsed toggle becomes necessary.

### T5 — decisions.md inconsistency (procedural)

- **enduser** (L41–43): Notes D3 says "Chips row + task count" but context.md locks "badge only." This is an artifact inconsistency, not a stance disagreement.
- **architect**: Does not mention the inconsistency.

**Resolution needed:** The brief author should reconcile D3 with context.md before the brief is finalized. Context.md (the later, confirmed artifact) should govern.

## Recommendation

Adopt the architect's structural design (state placement, `filterTasks()`, controlled `FilterPanel`, layout wrapper, testing strategy) as the implementation skeleton. Layer in the enduser's three additive requirements:

1. **Result count** — Display `"{filtered} / {total} tasks"` next to the toggle button when any filter is active. Structurally trivial given the architect's existing derivation. Addresses the highest-risk UX gap (filtered-view blindness) at near-zero implementation cost.

2. **Accessibility contract** — Add `aria-live` on result count, `aria-expanded` on toggle, focus management (expand → first control, collapse → toggle), explicit labels. These are standard a11y patterns that the controlled component boundary already supports.

3. **Horizontal panel layout** — Constrain the `FilterPanel` internal layout to one or two horizontal rows. This is a CSS concern within the component, not a structural change.

The enduser's reset-affordance concern (T4) is resolved by adopting the result count — expand-to-reset becomes acceptable per the enduser's own conditional argument.

**Confidence: 0.82** — High structural convergence. The one material tension (result count) is low-cost, well-motivated, and self-consistently resolves the secondary tension (reset affordance). Accessibility requirements are additive and uncontested.

## Open Questions

1. **D3 artifact inconsistency.** Should the brief lock "badge + result count" (incorporating the enduser's recommendation) or "badge only" (context.md status quo)? The synthesis recommends the former, but the decision belongs to the brief author.

2. **Column height CSS strategy.** Both stances flag the fragile `calc(100vh - 56px)`. Should the brief specify CSS custom properties, or leave the implementation approach to the builder? The architect suggests a CSS variable or fixed known height; no firm recommendation from either stance.

3. **PDS 3.34.0 component availability.** The architect notes task 1230 (PDS migration) may provide filter/chip components. Should the brief block on PDS availability or specify fallback plain inputs? The `FilterPanel` props interface is stable either way — this is an internal implementation detail.

4. **Tag selector at scale.** The enduser flags that 30+ distinct tags would need type-to-filter within the dropdown. Is this in scope or noted as future work?
