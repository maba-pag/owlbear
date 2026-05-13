# Architect Debate Log — Board Visual Design CSS Architecture

## Cycle 1

### Draft Position Summary

1. Theme-agnostic token rename is structurally correct (not a new alias layer)
2. Per-component CSS is the correct granularity (6 files)
3. Data attributes for state, BEM classes for structure
4. DOM-level theme via `useTheme` hook, no React Context
5. Card height removal with CSS `line-clamp` guard
6. Flexbox column header, not position-sticky

### Critic Challenges (6 challenges, 3 blind spots, confidence 0.41)

| # | Challenge | Severity | Verdict |
|---|-----------|----------|---------|
| 1 | Token rename IS the alias layer — research notes say so; calling it "not indirection" is contradicted by repo evidence | moderate | **Accepted.** Reframed: it IS an alias layer, and it's justified because light-encoded names are semantically wrong in dark mode. |
| 2 | Token coverage under-scoped — only color/state addressed, brief needs shadow, border-radius, spacing, typography | critical | **Accepted.** Expanded token architecture to include all non-color PDS categories. |
| 3 | Bootstrap/FOWT problem — useEffect sets data-theme after mount, causing flash for saved dark preference | critical | **Accepted.** Added synchronous inline script in index.html pattern. |
| 4 | Line-clamp guard doesn't apply — Card only renders title + 2 badges, no body text to clamp | critical | **Accepted.** Retracted line-clamp. Card content is inherently bounded. Replaced with overflow-wrap guard. |
| 5 | Shared styles.ts helper exists — not actually "6 isolated CSS files" topology | moderate | **Accepted.** Added styles.ts migration to per-component CSS plan. |
| 6 | Nested scroll hierarchy — flex-column claim doesn't address workspace → board → column scroll stack | moderate | **Accepted.** Added scroll hierarchy analysis and board-as-own-scroll-container pattern. |

**Blind spots surfaced:**
- Toggle UI placement not addressed → Deferred as UI concern, not CSS architecture
- Dark token sourcing from manual extract → Addressed in token generation strategy
- Additional states (filter-expanded, activity-filter pressed, context-menu open) → Added to state model

---

## Cycle 2

### Refined Position Summary

1. Token rename acknowledged as alias layer — justified by semantic correctness
2. Per-component CSS with styles.ts migration
3. Data attributes for all dynamic state (expanded list)
4. DOM-level theme with synchronous bootstrap script in index.html
5. Card height removal safe as-is (retracted line-clamp)
6. Flexbox column with scroll hierarchy awareness

### Critic Challenges (5 challenges, 3 blind spots, confidence 0.46)

| # | Challenge | Severity | Verdict |
|---|-----------|----------|---------|
| 1 | Manual override toggle UI is unowned | critical | **Rejected.** CSS architecture defines the `data-theme` contract and `useTheme` hook. Where the button lives is a UI/feature decision, not a structural CSS concern. The architecture works regardless of button placement. |
| 2 | Token generation mechanism is contradictory — says themeDark doesn't exist then says extract it | critical | **Accepted.** Fixed: PDS exports individual dark-suffixed tokens (`colorSurfaceDark`, `colorErrorDark`), not a `themeDark` object. Generation script maps these individual exports to agnostic custom property names. |
| 3 | Alias-layer cost understated — tests also reference light-suffixed names | moderate | **Partially accepted.** Scope estimate updated to include test file references. Still mechanical find-and-replace, not an architectural concern. |
| 4 | Card title can grow unbounded without height constraint | moderate | **Acknowledged as acceptable risk.** Human-written kanban titles are typically 5-15 words. Degenerate cases don't break layout because columns scroll independently. No guard needed beyond overflow-wrap. |
| 5 | Scroll hierarchy fix relies on unspecified layout invariants | moderate | **Refined.** Board component owns its height (`height: 100%`) and manages scroll internally. Workspace keeps `overflow: auto` unchanged. No conditional parent mutation needed. |

**Blind spots surfaced:**
- Shell/sidecar surfaces outside 6 board components → Noted; token layer serves them but their CSS treatment is a separate task
- Runtime OS theme changes after first paint → **Accepted.** Added `matchMedia` change listener to useTheme hook
- Context menu x/y stays as inline style → **Accepted.** Position coordinates are runtime-computed; CSS handles visual treatment only

### Assessment

Position is solid after two cycles. Remaining Critic challenges are either out of scope (toggle UI placement), acceptable risk (long titles), or already addressed. Confidence improved from the genuine refinements: bootstrap script, token generation correction, runtime theme listener, styles.ts migration.
