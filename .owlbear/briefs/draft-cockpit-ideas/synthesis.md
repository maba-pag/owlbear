# Synthesis — Cockpit Ideas Notebook

**Mode:** converge | **Stances:** architect, enduser | **Date:** 2026-05-18

## Summary

The architect and enduser stances are broadly aligned on the structural shape of the Ideas Notebook: a lightweight tab plugging into the #1638 tab system, backed by two API endpoints, with page-local state and explicit save. The architect focuses on package topology, dependency flow, and DI patterns; the enduser focuses on the save trust contract, data-loss prevention, and dual-surface (cockpit + VS Code) editing reality. Most divergence is not conflict but complementary coverage — the architect defers frontend UX specifics to #1638, while the enduser fills that gap with concrete interaction requirements. The two substantive tensions are around external-edit awareness (enduser wants it; architect is silent) and the unsaved-changes guard (enduser calls it non-negotiable; architect doesn't scope it).

## Convergences

### 1. Empty-state semantics — agreed

Both stances converge on the same behavior: GET returns empty content when the file is absent; PUT creates the file on first save. The architect grounds this in avoiding init noise (context.md Q2); the enduser grounds it in putting the user directly into the editor with placeholder text. Same outcome, different justifications.

*Sources: architect.md §Q2, enduser.md §2*

### 2. Explicit save with dirty-state tracking — agreed

Both accept D3 (explicit save button). The architect treats this as settled. The enduser extends it: explicit save only works if the dirty-state contract is enforced on every exit path. They agree on the mechanism; the enduser specifies the full scope of enforcement.

*Sources: architect.md §Q4 (page-local state with dirty flag), enduser.md §1*

### 3. No OCC / last-write-wins — agreed

The architect explicitly rules out OCC for the near-zero-probability concurrent-tab scenario. The enduser acknowledges the limitation and proposes a pragmatic re-fetch heuristic (see Disagreements §2) rather than version tracking.

*Sources: architect.md Key Trade-offs row 3, enduser.md §5*

### 4. Page-local state, no CockpitProvider extension — agreed

Both agree the Ideas page holds all state locally and does not consume board, task, or DR data. The architect flags CockpitProvider eager polling as a cost the ideas page shouldn't pay (a #1638 concern). The enduser doesn't contradict this.

*Sources: architect.md §Q4, enduser.md (implicit — no mention of shared state)*

### 5. Cross-package `atomic_write` import — no objection

The architect's position on importing `atomic_write` from `owlbear_kanban.storage_io` is uncontested. The enduser doesn't address backend internals but the data-safety emphasis (enduser §1, warnings) is consistent with using the existing crash-safe write primitive.

*Sources: architect.md §Q1*

### 6. #1638 as critical dependency — agreed

Both stances accept the tab system dependency. The architect defers frontend placement to #1638's conventions. The enduser's recommendations (route-switch guard, default edit mode, nav-rail icon) assume the tab system is in place.

*Sources: architect.md Warning 1, enduser.md (throughout — recommendations assume tab routing exists)*

## Disagreements

### 1. Unsaved-changes guard scope — enduser prescribes, architect silent

The enduser calls unsaved-changes interception on route navigation, browser refresh, and browser close a non-negotiable must-have and the minimum contract for explicit save to be trustworthy. The architect mentions `dirty flag` in the component state description but does not enumerate the exit paths that must be guarded. This is not a conflict — the architect deferred frontend specifics — but it is a coverage gap. The enduser's position fills it.

*Sources: enduser.md §1 + Warning 1; architect.md §Q4 (mentions dirty flag only)*

### 2. External-edit awareness — enduser wants it, architect absent

The enduser argues dual-surface use is the expected norm (citing D5) and recommends re-fetching content on route activation or `visibilitychange`, with a dirty-state notice for conflicts. The architect does not address this scenario at all. This is the largest gap between the two stances. The enduser's proposal is pragmatic (no mtime, no OCC) but adds meaningful interaction complexity: re-fetch logic, clean-vs-dirty branching, and a user-facing notice.

*Sources: enduser.md §5 + Warning 2; architect.md (not addressed)*

### 3. Preview toggle — enduser "should-have" vs architect deferred

The enduser recommends preview toggle as a should-have for v1, noting dependencies are already bundled and the UX benefit for re-reading. The enduser also acknowledges the evidence gap (will users revisit in cockpit or VS Code?) and accepts Phase 2 deferral. The architect defers all frontend specifics to #1638. Context.md records that the simplifier proposed cutting preview entirely. This remains an unresolved scope question.

*Sources: enduser.md §4; architect.md §Q4; context.md Active Tensions*

### 4. Default-to-edit-mode — enduser prescribes, architect silent

The enduser explicitly requires the textarea to be visible and focused on tab open, contrasting with the existing TaskFieldsEditor which starts in preview mode. The architect does not address this. If preview is included, this becomes a meaningful UX decision; if preview is cut, it's moot.

*Sources: enduser.md §3; architect.md §Q4*

## Recommendation

Ship the backend exactly as the architect describes (two endpoints, `atomic_write` import, `get_ideas_path` dependency, create-on-first-write). On the frontend, adopt the enduser's must-haves (#1 unsaved-changes guard on all exit paths, #2 empty-state-as-editor, #3 default edit mode) as acceptance criteria. These are not feature additions — they are the minimum contract that makes explicit save trustworthy.

Defer the preview toggle (enduser #4) and external-edit awareness (enduser #5) to Phase 2. Both add real complexity and neither blocks a usable v1. The preview toggle has an acknowledged evidence gap; external-edit awareness requires interaction design that is better validated after the base feature ships.

The Cmd+S shortcut (enduser #6) and icon choice (enduser #7) are polish — defer without discussion.

**Confidence: 0.80** — High alignment on structure and backend. The recommendation to defer external-edit awareness is the weakest point; the enduser makes a strong case that dual-surface use is the norm, and shipping without any re-fetch creates a predictable stale-content complaint. However, adding it to v1 scope risks creep for a preference feature.

## Open Questions

1. **External-edit awareness: v1 or Phase 2?** The enduser argues it belongs in v1 because dual-surface use is the expected pattern. The synthesis defers it, but this is the decision most likely to be revisited. The user should weigh whether stale-content friction on a feature they'll use alongside VS Code undermines the co-location value proposition.

2. **Preview toggle: v1 or Phase 2?** Context.md records an active tension from the simplifier. The enduser recommends v1 inclusion but accepts deferral. If deferred, the v1 is textarea-only with no toggle — simpler to build and test. The revisit trigger is whether the user actually re-reads ideas in the cockpit vs VS Code.

3. **`atomic_write` docstring update.** The architect flags that the function's docstring says "for kanban task files." When should this be updated — as part of the ideas feature or as a separate hygiene task?

4. **CockpitProvider eager polling on non-board routes.** The architect flags this as a #1638 concern. Is this tracked in #1638's acceptance criteria, or does it need a separate task?
