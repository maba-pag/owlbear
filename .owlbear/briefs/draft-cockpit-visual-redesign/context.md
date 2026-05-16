# Context — Cockpit Visual Redesign

## Problem

The cockpit frontend is structurally functional — data flows, routes work, SSE updates arrive — but visually scores ~10/100. The root cause is not cherry-picking from PDS: the PDS foundation was never installed. The required stylesheet imports (variables, font-face, normalize) are missing. A hand-rolled `tokens.css` with non-standard `--pds-*` prefix partially duplicates PDS but misses key systems (typography scale, fluid spacing, font weights, transitions). Some referenced variables resolve to nothing.

Of 73 available PDS React components, 14 are used (19%). Nine raw `<button>` elements, five raw `<option>` elements, seven raw `<ul>` lists, five raw headings, and six raw PDS web-component elements remain where React wrappers exist. Three custom modal overlays bypass PDS `PModal`. Fifteen inline `style={{}}` occurrences bypass theming and breakpoints.

The board layout wraps into a multi-row grid instead of horizontal scroll. The sidecar has zero internal padding. Cards show almost no metadata. Dark mode has no border contrast. The filter panel is largely unstyled.

A comprehensive audit (`.owlbear/research/cockpit-visual-audit-comprehensive.md`) catalogues 73+ findings across 16 sections with resolved decision gates.

## Project Type

Existing-feature/refactor — redesigning visual presentation of existing JSX structure using PDS components, tokens, and CSS.

## Scope Signal

- Frontend only (no backend changes)
- PDS foundation install + component migration + layout CSS + polish
- An existing brief (`draft-board-visual-design/`) covers an earlier, narrower framing; this discovery encompasses the full audit scope
- Decision gates already resolved in the audit: styling architecture (PDS + Tailwind), tokens.css fate (delete/replace), sidecar architecture (accordion sections), mobile contract (desktop-only), visual regression (baselines after redesign), ESLint bans (explicit + regex)

## Relationship to Existing Brief

`draft-board-visual-design/` was drafted before the comprehensive audit. Its scope is "apply PDS design tokens to make the board look like a finished product." The comprehensive audit revealed the problem is deeper — PDS foundation is missing entirely, not just under-applied. That brief produced the current 10/100 state. This discovery supersedes it.

## Locked Outcomes

**Best realistic outcome:** The cockpit looks and feels like a finished PDS v4 application. PDS foundation installed (fonts, variables, normalize). All interactive elements use PDS React components. Layout uses PDS tokens via Tailwind utilities. Light and dark themes work from a single attribute change. Cards show enough metadata to be scannable. Sidecar has structured sections with typography hierarchy. Modals, popovers, and overlays use PDS overlay components. A PDS-familiar visitor would recognize the system immediately.

**Minimum viable win:** PDS foundation installed and rendering correctly. Board layout scrolls horizontally. Cards and columns visually differentiated. Sidecar has padding and section dividers. Raw web components replaced with React wrappers. Custom modals replaced with PModal. Dark mode has border contrast. Usable, not polished.

**Scope boundary:** No new features (grouping, search, notes tab have own briefs). No backend changes. No responsive/mobile (desktop-only per audit decision gate #4). DnD stays with minimal styling. No screenshot regression baselines until after redesign. No performance optimization.

## Active Tensions

- The old brief failed at execution. What structural factors caused a 10/100 despite having a brief? Risk of repeating the pattern.
- Audit has 73+ findings — decomposition complexity is high. Risk of a too-large Brief that can't be executed incrementally.
- Six decision gates already resolved in the audit. Phase 2 mediation should validate these rather than re-open them.
- PDS Tailwind integration is recommended but unproven in this codebase. Research needed on integration mechanics.

## Early Challenge Summary

Both challengers (simplifier, first-principles) converge on:

1. **Root-cause-first:** The 73 findings are likely one defect (tokens.css shadow namespace) expressed everywhere. Fix the root cause, re-audit, then plan remaining work. Don't pre-commit to 73 remediations. **(Accepted — re-audit after foundation is a good checkpoint.)**
2. **Scope to Tier 1 only for the brief:** Install PDS foundation (3-5 tasks). Component migration is mechanical (task batch, no brief). Layout evaluates after Tier 1. Polish is backlog. **(Partially accepted — re-audit checkpoint yes, but don't use it as an excuse to skip PDS-recommended tooling.)**
3. **Tailwind is unearned:** The audit resolved this as a decision gate, but no evidence that PDS tokens in plain CSS are insufficient. **(OVERRIDDEN — PDS recommends the Tailwind integration. Questioning design system recommendations is the exact pattern that produced the 10/100 failure. See D4.)**
4. **Builder visual feedback:** The old brief's failure may not be a scope problem — builder agents write CSS blind. Smaller batches with human visual review may matter more than a better brief. **(Accepted — process constraint for Phase 2 decomposition.)**
5. **"Desktop-only" is one CSS rule:** `overflow-x: auto` on the board container, not a responsive design project. **(Accepted.)**
6. **Visual gates need human checkpoints:** Screenshot tests prevent regression, not bad baselines. The real gate is human approval between implementation batches. **(Accepted.)**

**Key user directive:** Follow PDS v4 documentation recommendations as closely as possible. The previous failure came from agents being reductive about the design system. This time, adopt the full recommended stack.
