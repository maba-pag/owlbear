# End-User Debate Log — Cockpit Ideas Notebook

## Critic Cycle 1

### Draft Position Submitted

1. Include preview toggle — "~10 lines, dependencies bundled, removing saves nothing"
2. Cmd+S is essential / make-or-break
3. Empty state: "never show an error state"
4. Lightbulb icon signals AI, use "edit" instead
5. Overall pattern correct, Cmd+S is make-or-break detail

Confidence: 0.80

### Critic Challenges (Cycle 1)

| # | Severity | Challenge | Accepted? |
|---|----------|-----------|-----------|
| 1 | Critical | Preview is still marked as cut/Phase 2 in context.md. Stance promotes it to essential without evidence that revisit-in-cockpit is a proven need. | Partially — refined to "strongly recommended" with evidence gap acknowledged |
| 2 | Critical | "Never show an error state" overreaches. File absence ≠ API failure. | Accepted — distinguished file-absence (empty state) from actual errors (error feedback) |
| 3 | Critical | "Make-or-break" overstated for Cmd+S. Existing task editor uses button-only save and works. | Accepted — downgraded to "strongly recommended" then to "nice-to-have" |
| 4 | Moderate | "~10 lines" claim unsupported. Actual reuse target has mode state, dual render, toggle, tests. | Accepted — corrected cost estimate |
| 5 | Moderate | Cmd+S conflict surface is broader than just KanbanBoard. | Accepted — broadened to "document-level keyboard handlers elsewhere in the shell" |
| 6 | Moderate | TaskFieldsEditor starts in preview mode, not always-visible textarea. Claimed UX consistency is inaccurate. | Accepted — added explicit position that Ideas must default to edit mode |
| 7 | Minor | "Lightbulb = AI" claim unsupported. | Accepted — retracted specific claim |

### Blind Spots Surfaced (Cycle 1)

- External-edit coherence: what happens when ideas.md changes in VS Code while cockpit tab is open?
- Route-switch trust: unsaved changes lost on tab navigation
- Accessible naming: aria-label matters as much as visual icon

All three incorporated into revised stance.

## Critic Cycle 2

### Revised Position Submitted

1. Preview toggle recommended with honest cost estimate, argument based on revisit value
2. Cmd+S downgraded to "strongly recommended," conflict analysis included
3. File-absence vs API-failure distinguished
4. Icon claim softened, accessible label acknowledged
5. External-edit coherence and route-switch guard added
6. Overall assessment revised

Confidence: 0.78

### Critic Challenges (Cycle 2)

| # | Severity | Challenge | Accepted? |
|---|----------|-----------|-----------|
| 1 | Critical | External-edit is expected behavior (not edge case) since D5 explicitly accepts dual-surface use. But mtime/OCC was cut — staleness detection has no contract. | Accepted — upgraded to "should-have," acknowledged no-mtime constraint, proposed degraded-but-honest UX |
| 2 | Critical | Preview still promoted from Phase 2 optional to v1 critical without evidence that users revisit in cockpit vs VS Code. | Partially accepted — reframed as "should-have" not "must-have," acknowledged evidence gap explicitly |
| 3 | Critical | "Small, low-risk" assessment no longer holds if all recommendations ship — preview + Cmd+S + external-edit + route guard adds complexity beyond original scope. | Accepted — introduced tiered recommendations (must/should/nice) to separate safety from polish |
| 4 | Moderate | Cmd+S conflict surface extends beyond KanbanBoard to modals and other components. | Accepted — generalized the conflict surface description |
| 5 | Moderate | Create-on-first-save is UX intent, not agreed cross-layer contract. Backend behavior still open. | Accepted — noted as needing cross-layer agreement |

### Blind Spots Surfaced (Cycle 2)

- Browser refresh and close are data-loss channels alongside route-switch → added `beforeunload` to must-have
- Default mode matters: if preview included, does tab open in edit or preview? → added explicit "default to edit" position
- Icon argument is weak if accessible label does the clarity work → softened icon position, elevated label importance

All incorporated into final stance.

## Resolution

Two Critic cycles at high pressure. Initial confidence 0.80 → final 0.76. The drop reflects honest acknowledgment of evidence gaps (preview value, icon semantics) while the core data-safety positions strengthened. The tiered structure was the key refinement — it separates non-negotiable safety (unsaved-changes guard) from quality improvements (preview) and polish (Cmd+S).
