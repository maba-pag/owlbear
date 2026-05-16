# First-Principles Stance — Cockpit Visual Redesign

## Irreducible Claims

After stripping the framing, only three claims survive as genuinely necessary:

1. **The user needs the cockpit to not look broken.** Columns must be distinguishable, cards must have boundaries, the sidecar must not be raw debug output, overlays must not reflow the page.
2. **PDS is the chosen design system.** This is a product decision, not an inherited assumption — the user chose Porsche Design System and it's already partially integrated (provider wraps the app, components hydrate locally).
3. **The existing JSX structure is correct.** Data flows, routes work, SSE updates arrive. The problem is exclusively visual presentation.

Everything else in the framing — 73 findings, 4 tiers, 7 remediation lanes, "full coordinated redesign" — is *proposed structure*, not irreducible need.

## Assumptions Challenged

### 1. "PDS foundation was never installed" is a misdiagnosis

The audit itself says: "PDS assets load from `/porsche-design-system/components/...` and custom elements hydrate. This is important: the ugly result is mostly not because PDS is absent."

So the foundation *is* installed in the sense that matters (runtime loads, components render). The actual problem is: `tokens.css` creates a parallel variable namespace (`--pds-*`) that *shadows* PDS's own theming cascade. Components render but don't pick up coherent styling because there are two competing token systems. The fix is deletion (tokens.css) + correct import path — not "foundation installation" as a large initiative.

**Test:** If you delete tokens.css and import PDS's stylesheet, does the visual score jump from 10 to 40 with zero other changes? If yes, the 73-finding audit is mostly consequences of one root cause.

### 2. "PDS + Tailwind" is inherited structure, not earned

The framing assumes Tailwind as a co-architecture without proving why PDS alone is insufficient. PDS provides spacing tokens, typography scale, and a complete component library. Tailwind adds:
- A build config to maintain
- Potential specificity conflicts with PDS component styles
- A learning surface for builder agents that already failed at "apply PDS tokens"
- Class-name bloat in JSX that competes with PDS semantic classes

**Irreducible question:** What does Tailwind provide that PDS tokens in CSS custom properties + standard CSS do not? If the answer is "utility classes for layout," that's convenience, not necessity. The first brief failed with only one abstraction layer (tokens.css). Adding a second (Tailwind) increases the ways things can go wrong.

### 3. "73 findings require a full coordinated redesign" is scope inflation

Count the findings that are *direct consequences* of tokens.css fighting PDS:
- Missing border contrast in dark mode → wrong token values
- Cards show no differentiation → surface tokens not inherited from PDS
- Sidecar unstyled → no PDS spacing cascading
- Filter panel raw → PDS form component styles not flowing

Most "findings" are instances of one structural defect expressing itself in 73 places. The remediation model should be: fix the structural defect, then *re-audit* to find what's actually left. The current framing pre-commits to 73 fixes without testing whether 60 of them disappear when the root cause is addressed.

### 4. The first brief failed because of execution feedback, not scope

The old brief produced 10/100. The framing says "scope was too narrow." But the audit contradicts this: "PDS components hydrate" and "columns are one of the better surfaces." The builder *did* execute. It produced partial results. The question the framing avoids:

**Can a builder agent produce good CSS without visual feedback?**

Builder agents read JSX, write CSS, run tests. They never *see* the result. The first brief had 15 decisions, detailed token specs, component-by-component instructions. It still produced 10/100. If the failure mode is "agent writes plausible CSS that renders badly because it can't see," then the same failure repeats regardless of brief quality, Tailwind adoption, or scope size.

**Structural risk:** If screenshot tests are added *after* the redesign (as proposed), they verify the builder's output only at review time — the builder still works blind during implementation. The real fix might be: smaller batches with human visual review between each, not a better brief.

### 5. "Desktop-only" as a scope constraint is a dodge, not a decision

The cockpit is a browser app. The audit found 320px overflow bugs. The "decision" to be desktop-only doesn't eliminate the problem — it just moves it to "someone else's brief." If the layout grid uses `minmax(200px, 1fr)` and the board has 7 columns, it *will* overflow on narrower viewports. The irreducible question is: does the CSS prevent document-level overflow (via `overflow-x: auto` on the board container), or doesn't it? That's one CSS rule, not a responsive design project.

### 6. "Visual quality gates" conflates two different failures

The framing proposes screenshot regression tests to prevent "false green." But the *actual* failure was: a human looked at 10/100 output and marked the task done. No screenshot test prevents a bad baseline from being approved. The real gate is: human approval of visual output before task completion. The test prevents *regression* from an approved state — it doesn't prevent arrival at a bad state.

## What's Actually Irreducible

If I strip to the minimum that transforms "broken" to "works visually":

| # | Action | Expected Impact |
|---|--------|-----------------|
| 1 | Delete tokens.css, import PDS v4 stylesheet (variables + normalize + font-face) | Tokens unify. PDS components inherit correct values. ~40% of findings may self-resolve. |
| 2 | Replace 3 custom overlay containers with PModal/PPopover | Fixes P0 "overlays reflow the app" bug |
| 3 | Add `overflow-x: auto` to board container, set column min-width | Board scrolls instead of wrapping |
| 4 | Add padding + PDivider to sidecar sections | Sidecar goes from "debug output" to "basic inspector" |
| 5 | Replace remaining raw `<button>` with PButton/PButtonPure | Interactive elements become visually consistent |

Five changes. Then re-audit. The current framing pre-commits to 73 fixes, 7 remediation lanes, Tailwind integration, and a "full coordinated redesign" without proving the simpler path fails.

## Confidence

**0.72** — The structural diagnosis (tokens.css as root cause) is well-supported by evidence in the audit itself. The challenge to Tailwind and "full redesign" scope is strong but could be wrong if PDS's own layout utilities are genuinely insufficient for the board grid. The challenge to builder-agent visual feedback is the weakest claim (hard to prove without experimentation) but the most important if true.

## Summary

The framing inherits three things it hasn't earned: Tailwind as co-architecture, "73 findings = 73 fixes" as scope model, and "better brief = better outcome" as theory of failure. The irreducible problem is likely: one wrong abstraction (tokens.css) expressing itself everywhere, plus 5 structural CSS bugs. Fix those first. Re-audit. Then decide whether a "full coordinated redesign" is still needed.
