# Simplifier Stance — Cockpit Decisions Tab

## Scope Cuts

### Cut 1: Deep-link receiver (Outcome 4) → Defer

No sender exists in V1. A deep-link receiver with no sender is speculative infrastructure. It's a one-line route-param check — trivially added when the kanban cross-nav sender ships. Building and testing it now adds scope for zero user value.

### Cut 2: Resolved DRs and backend expansion (Outcome 5, half of Outcome 2) → Defer to V1.1

The primary user need is *acting on pending DRs*. Resolved DRs are read-only history — nice-to-have, not the pain point. Deferring this means:

- No new `GET /api/decisions` endpoint — reuse existing `GET /api/decisions/pending`
- List panel shows pending DRs only (the actionable set)
- Resolved-DR viewing and status filtering ship as a fast follow once the tab works

This cuts backend work and halves the list-panel rendering complexity (no mixed states, no sort-order logic for pending-first).

## Decomposition Pressure

Split into two sequential deliverables:

| Phase | Scope | Validates |
|-------|-------|-----------|
| **P1: Tab shell** | Nav-rail with two entries, React Router route structure, kanban moved into tab slot | Tab system works, future tabs can plug in |
| **P2: Decisions content** | List+detail split layout, resolution flow, SSE integration | Decisions tab delivers user value |

P1 can be validated with kanban as tab 1 and a skeleton decisions tab. P2 fills in the content. This lets the pathfinder question ("does the tab system work?") be answered before investing in the decisions UI.

## Hidden Scope Warning

The brief says resolution flow "reuses existing `ResolveModal` patterns." Moving components from a sidecar/popover context into a full split-layout tab is not reuse — it's reimplementation in a new layout paradigm. The existing `DecisionViewport` and `ResolveModal` were designed for constrained spaces. Expect meaningful rework, not copy-paste.

## Over-Engineering Risk

"Pluggable tab system" risks creating an abstraction layer (route registry, dynamic discovery, plugin contracts) when React Router already provides the mechanism. Three planned tabs do not justify a plugin framework. A simple routes array and a nav-rail items list is sufficient. If tab 4 needs dynamic registration, build it then.

## Recommended Minimum V1

1. Tab shell: nav-rail + routes (kanban + decisions)
2. Decisions list panel: pending DRs only
3. Detail panel: full DR body + resolution controls
4. Resolution: reuse backend, rebuild UI for the new layout context

That's it. Deep-links, resolved-DR history, and status filtering are fast-follows with near-zero architectural risk once the shell exists.

## Confidence

**0.82** — The cuts are clean deferral boundaries with no architectural debt. The decomposition into tab-shell vs. content is the natural seam. The main uncertainty is whether "resolved DRs" are actually needed for V1 user workflows — if they are, Cut 2 gets reversed, but the brief's own framing ("pending first") suggests they're secondary.
