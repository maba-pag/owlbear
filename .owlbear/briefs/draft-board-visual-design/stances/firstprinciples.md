# First-Principles Stance — Board Visual Design

## Irreducible Core

The actual problem is **one claim**: the board is invisible because nothing renders visual boundaries. White elements on a white background. The fix is: give elements visible surfaces, borders, and text contrast.

Everything else in the framing — alias layers, dark theme, "finished product," automatic inheritance — is layered on top of that single irreducible need.

---

## Assumptions Challenged

### 1. "PDS tokens are the right design authority" — Already settled, not open

The codebase imports `PButton`, `PMultiSelect`, `PSelect` from `@porsche-design-system/components-react`. `tokens.css` extracts 17 PDS light-theme values. `Shell.css` uses them for layout. Questioning PDS now means ripping out existing code. This is a **false open question** — the decision was made implicitly and should be acknowledged as locked, not re-evaluated.

**Impact on framing:** None. Remove from open questions; it wastes research cycles.

### 2. "Theme-agnostic alias layer is needed" — Premature abstraction

The framing assumes a two-tier token system: semantic aliases (`--board-surface`) → PDS primitives (`--pds-theme-light-background-surface`). But `tokens.css` already **is** the alias layer — CSS custom properties are inherently overridable per selector. A `[data-theme="dark"]` block that reassigns the same 17 properties in `tokens.css` achieves full theme switching with zero additional indirection.

The "alias layer" smuggles in an abstraction tier that serves future scale (dozens of components, design-system-level naming) that doesn't exist yet. At 6 components with ~20 token references total, the extra naming layer adds cognitive overhead without reducing duplication.

**What's actually needed:** Override the existing custom properties for dark theme. That's it.

**Confidence:** 0.82 — the existing token file structure already supports theming without a new layer.

### 3. "Both themes must ship together" — Bundles a feature with the fix

The irreducible problem is visibility in **the current theme** (light). Dark theme is additive — it doesn't fix the "white on white" problem; it's a second delivery. Shipping both together:
- Doubles the CSS surface area to test
- Doubles visual QA (every component × 2 themes)
- Delays the fix for the actual pain ("I can't see the board")

The brief's own "minimum viable win" acknowledges this by accepting "thinner polish" — but doesn't question whether dark theme belongs in this brief at all versus a follow-up.

**What's actually needed:** One theme, done well. Dark can follow as a thin additive pass once the visual vocabulary is proven.

**Confidence:** 0.72 — user explicitly said "both themes" so this may be intentional scope, but the irreducible need doesn't require it.

### 4. "No structural changes to JSX" — Self-defeating constraint

`Card.tsx` has **16 lines of inline style objects** including conditional logic (`selected ? X : Y`). These cannot be replaced with external CSS without either:
- Adding `className` (trivial 1-line JSX change per component), or
- Targeting via `data-testid` attributes (couples styling to test infrastructure — anti-pattern), or
- Targeting via `data-priority`/`data-selected` attributes (workable but limited)

The "CSS-only" constraint creates incentive to write brittle selector chains (`[data-testid="task-card"][data-selected="true"]`) that are harder to maintain than the simple JSX change they're avoiding. The constraint doesn't protect anything valuable — the JSX structure, props, and behavior stay identical. Only selector hooks change.

**What's actually needed:** Allow `className` additions. That's a minimal JSX change, not a structural one. The constraint should be "no new components, no new props, no behavior changes" — not "zero JSX edits."

**Confidence:** 0.88 — the inline styles make pure-CSS replacement impractical without selector hooks.

### 5. "Future features inherit automatically" — Conflates two different claims

This framing bundles two distinct things:
1. **Theme switching is automatic** — new CSS using tokens automatically works in both themes. True and achievable.
2. **Future feature styling is automatic** — new components inherit a visual system without writing CSS. False and impossible.

No token system makes new components self-styling. A new "Decisions Tab" or "Board Grouping" feature will need its own CSS regardless. What tokens give you is **consistency** (same colors, same spacing) and **theme coverage** (both themes work if you use tokens). That's valuable, but it's not "automatic."

**What's actually needed:** Use PDS tokens consistently. That's the whole contract. The word "automatically" over-promises and could drive over-engineering (trying to build a CSS framework for 6 components).

**Confidence:** 0.85

### 6. "Finished product" is the wrong frame — "usable and coherent" is the irreducible bar

"Finished product" implies: hover microinteractions, focus ring polish, elevation/shadow hierarchy, transition animations, empty state illustrations, responsive refinements. "Usable and coherent" implies: visible surfaces, readable text, correct spacing, priority colors work, hover states exist.

The gap between these two is 3-5× the CSS effort. The brief straddles both by defining "best realistic outcome" as finished-product and "minimum viable win" as coherent — but doesn't commit. This ambiguity will cause scope creep during implementation ("is this card shadow polished enough?").

**What's actually needed:** Commit to "usable and coherent" as the acceptance bar. If the result looks better than that, great. But the bar should be "I can see and use the board in both themes" not "it looks like a Porsche shipped it."

**Confidence:** 0.76 — the user said "finished product" explicitly, but the minimum viable win tells the real story.

---

## Summary

| Assumption | Verdict | Load-bearing? |
|---|---|---|
| PDS is the right system | Already settled — not an assumption | N/A |
| Alias layer needed | Not at this scale; existing tokens suffice | No |
| Both themes together | Bundles additive feature with the fix | Partially — user intent, but not irreducible |
| No JSX changes | Self-defeating; allow classNames | No |
| Automatic inheritance | Conflates two claims; only one is real | No |
| Finished product bar | Over-scoped; "usable and coherent" is the real bar | No |

**Overall confidence:** 0.80 — the framing is ~60% inherited complexity around a simple core problem. The strongest intervention is to separate "make the board visible" from "build a theming system."
