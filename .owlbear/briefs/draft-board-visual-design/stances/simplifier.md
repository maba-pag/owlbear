# Simplifier Stance: Board Visual Design

## Cut 1 — Drop the alias layer (item 2)

The plan calls for a three-tier indirection: PDS token → theme-agnostic alias → component CSS. For 6 components and ~20 distinct token references, this is premature abstraction. The alias layer saves nothing today and adds a mental-model tax on every future developer who has to trace `--board-surface` back through `--pds-theme-light-background-surface`.

**Simpler alternative:** Reference PDS tokens directly in component CSS. Use `[data-theme="dark"] { --pds-theme-light-*: <dark-value> }` overrides at root scope — the same pattern `tokens.css` already uses. If the project hits 30+ components and the token rename cost becomes real, introduce aliases then. That's a mechanical find-and-replace, not a design change.

Cost of deferral: one find-and-replace session later. Cost of building now: every contributor learns an extra indirection layer for a 6-component app.

## Cut 2 — Split dark theme into a follow-up

Generating `themeDark` tokens is mechanical (one Node script). Writing CSS that *supports* dark theme is nearly free if you use custom properties. But **verifying** dark theme across 6 components (contrast ratios, priority color legibility, DnD highlight visibility, context menu readability, filter panel controls, PDS component dark-mode behavior) is a separate QA surface that roughly doubles visual testing effort.

**Decomposition:**
- **P1 (this brief):** Light theme looks finished. Generate dark token file as a deliverable artifact. CSS uses custom properties so dark support is structurally possible.
- **P2 (follow-up):** Wire the toggle, apply dark overrides, verify dark rendering. This is where the theme-toggle UX decisions live too (localStorage? `prefers-color-scheme` fallback? toggle placement?).

The toggle mechanism is a small feature with its own state, persistence, and interaction design. Bundling it with "make the board visible" conflates a styling task with a preference-management feature.

## Cut 3 — Correct the "no JSX changes" constraint

The context.md already contradicts this: "minimal JSX changes (class names, data-theme attribute)." The actual code confirms the problem — `KanbanBoard.tsx` and `Column.tsx` use inline `style={{}}` objects, not class names. You *must* add `className` props to apply external CSS. `Card.tsx` has 12 lines of inline styles that need to become CSS classes.

This isn't a scope concern — it's a constraint that will immediately break on contact with reality. Reframe to: **no structural JSX changes** (no new components, no moved elements, no changed props/callbacks). Adding `className` and removing inline `style` objects is implementation, not restructuring.

## Not cutting

- **Per-component CSS files** — correct granularity. The components are already separate `.tsx` files; colocated CSS is standard React practice. A single `board.css` would be a 200+ line monolith mixing Column, Card, FilterPanel, and context menu concerns.
- **PDS-only token sourcing** — the right constraint. Prevents custom color invention.
- **Keeping DnD styled minimally** — D3 already locked this correctly.

## Summary

| Item | Verdict | Rationale |
|------|---------|-----------|
| Alias layer | **Cut** | Premature abstraction for 6 components |
| Dark theme verification + toggle | **Defer to P2** | Doubles QA surface; toggle is a separate feature |
| Dark token generation | **Keep in P1** | Mechanical, enables P2 |
| "No JSX changes" | **Reframe** | Inline styles must become classes; constraint is "no structural changes" |
| Per-component CSS | **Keep** | Right granularity |
| DnD styling | **Keep minimal** | Already decided |

## Confidence

**0.85** — High confidence on the alias-layer cut (clear YAGNI at this scale) and the dark-theme split (observable QA doubling). Moderate confidence on the JSX reframing — the inline-to-class migration might be larger than it looks if tests assert on `style` attributes, which would expand the diff.
