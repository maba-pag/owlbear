# Synthesis — Cockpit Visual Redesign

## Summary

Four domain panelists evaluated the cockpit visual redesign from architecture, data integrity, end-user experience, and security perspectives. Convergence is strong on the foundational strategy: install PDS foundation first, adopt `@tailwindcss/vite`, treat token migration as atomic, and gate further work behind a human re-audit checkpoint. The stances are compatible on decomposition order, differing mainly on where specific concerns land in the timeline. One hard blocker was surfaced (font self-hosting) that must be resolved before or during foundation work. The remaining tensions are sequencing disagreements, not design disagreements.

## Convergences

### C1 — Foundation first is unanimous

All four panelists agree PDS foundation install is the prerequisite for everything else. Architect frames it as Tier 0; enduser makes it co-equal Batch 1 with board scroll; data agrees formatting work depends on correct variable resolution; security's font-hosting concern is a foundation-adjacent requirement.

**Sources:** architect.md §Decomposition Order, enduser.md §Batch priority, data.md §Display Boundary Validation, security.md §R1.

### C2 — Human checkpoint after foundation, before committing to 73 remediations

Architect mandates a visual re-audit after Tier 1 token migration. Enduser demands it after Batch 1 (foundation + scroll). Both expect many findings to self-resolve when PDS variables cascade correctly. Data is compatible — formatting utilities depend on knowing which fields actually need treatment post-foundation.

**Sources:** architect.md §Decomposition Order (`[HUMAN CHECKPOINT]`), enduser.md §Warning 3, context.md §Early Challenge Summary point 1.

### C3 — `@tailwindcss/vite`, not PostCSS

Architect provides the technical rationale: PostCSS would replace LightningCSS and break `light-dark()` preservation. Security's R4 assessment is compatible — CSS processing chain change is negligible risk. No panelist disputes the Vite plugin path.

**Sources:** architect.md §Correction, security.md §R4.

### C4 — Token migration is atomic (delete + migrate + custom-tokens in one task)

Architect: unmigrated `--pds-*` reference resolves to nothing after `tokens.css` deletion — cannot split across tasks. Data: canonical values passed to mutation APIs must never break during migration. Both demand a complete provenance map as prerequisite.

**Sources:** architect.md §Warning 3, data.md §Canonical vs. Display Value Partition.

### C5 — Theme mechanism is settled

Architect resolves ORQ-4 from research: `useTheme` hook already sets `.scheme-dark`/`.scheme-light` classes that PDS reads. After `tokens.css` deletion, `data-theme` becomes vestigial but harmless. No panelist disputes this. No new theme mechanics needed.

**Sources:** architect.md §Theme contract is settled.

### C6 — Board scroll in Batch 1

Enduser: board horizontal scroll restores the kanban spatial metaphor and is co-equal with foundation. Architect: layout is Tier 3 but board scroll specifically (`overflow-x: auto`) is a one-line fix that could ship earlier. No tension — the disagreement is classification, not priority.

**Sources:** enduser.md §Batch 1, architect.md §Tier 3, context.md §Early Challenge Summary point 5.

### C7 — Config-driven enum vocabularies

Data: statuses and priorities come from the board API as configuration arrays, not hardcoded enums. Enduser agrees cards should render dynamic values. Architect is silent but compatible — no hardcoded enums in the structural proposal.

**Sources:** data.md §Enum Vocabularies Are Config-Driven, enduser.md §Card information density.

### C8 — Canonical vs. display value partition

Data's core position: formatted display values must never feed mutation APIs, especially the `updated` concurrency token. Enduser agrees formatting is JavaScript logic separate from CSS. Architect is compatible — no formatting in the structural proposal. Security is silent but the partition doesn't introduce new trust concerns.

**Sources:** data.md §Core Position, enduser.md §Warning 1, data.md §Warning 1.

### C9 — Smaller batches with human visual review

All four panelists endorse this as process mitigation. The previous brief failed partly because builder agents wrote CSS without visual verification. The batched decomposition with checkpoints is unanimous.

**Sources:** context.md §Early Challenge Summary point 4, architect.md §Decomposition Order, enduser.md §Key Trade-offs.

## Disagreements

### T1 — Font self-hosting: blocker or foundation-adjacent? *(security vs. field)*

**Security** (confidence 0.88): PDS `font-face.css` hardcodes all URLs to `https://cdn.ui.porsche.com`. The existing CDN trap only intercepts JS-driven loading. CSS `@font-face` URLs bypass it. Importing `global-styles/index.css` either breaks font loading (CSP blocks) or requires CSP relaxation. Required mitigation: extend `sync-pds-assets.mjs` to mirror font files and provide self-hosted font-face URLs.

**Architect, enduser, data**: Do not address font hosting. The architect's foundation task imports `global-styles/index.css` without noting the font URL issue.

**Assessment:** Security's finding is well-evidenced and the mitigation path is clear (option (a) — extend existing `sync-pds-assets.mjs`). This is a hard dependency for foundation work: importing `global-styles/index.css` without font self-hosting will either break visually or require CSP relaxation. It belongs in the foundation tier, not a separate track.

### T2 — Data formatting: where in the decomposition? *(enduser vs. data)*

**Enduser** (confidence 0.82): Data formatting is JavaScript code (not CSS), belongs in Batch 2 alongside card visual treatment. Explicit tasks for `formatRelativeTime()`, hide-if-empty, boolean-to-semantic text.

**Data** (confidence 0.80): Formatting utilities need strict display/mutation partition, null-safety, and config-driven enum lookup. Recommends a `utils/format.ts` module with specific function signatures. Also requires extending `computeSignal` with an "unknown" state.

**Assessment:** These positions are compatible, not opposed. Enduser defines the *what* (formatting is Batch 2, needs explicit tasks). Data defines the *constraints* (partition rule, null-safety, unknown state). Both can be satisfied by placing formatting utility tasks in Batch 2 with data's constraints as acceptance criteria. The `computeSignal` unknown-state extension is a domain logic change that should be its own task, also in Batch 2.

### T3 — Component migration: inventory first or start with obvious swaps? *(architect vs. enduser)*

**Architect** (confidence 0.78): Full behavioral-complexity inventory before any component migration. Components divide into simple swaps (button, heading) and complex integrations (shell tabs, filter panel, overlays). Overlay architecture is a distinct track. Inventory is insurance against the old failure mode.

**Enduser** (confidence 0.82): Cards need visual hierarchy (chips, icons, color differentiation) — this IS component work. Sidecar needs information architecture before styling. Both belong in Batch 2-3 and shouldn't wait for a complete inventory.

**Assessment:** The architect's inventory is a planning artifact (one task), not a blocking gate for simple swaps. The enduser's card visual hierarchy likely involves simple PDS component swaps (PTag chips, PIcon indicators) that don't need complex integration analysis. Recommended resolution: inventory task produces the complexity classification; simple swaps (including card chips/icons) can begin in parallel; complex integrations and overlay track wait for inventory results.

### T4 — PToast success feedback: in scope or deferred? *(enduser vs. field)*

**Enduser** (confidence 0.82): Success feedback is the "quiet gap" — error paths exist but success is silent. Creates mutation anxiety. PToast for moves, inline confirmation for edits.

**Architect, data, security**: Do not raise this concern.

**Assessment:** This is a legitimate UX finding but depends on PDS component migration being complete (PToast requires PDS foundation). It naturally lands in enduser's Batch 4 (polish). It is in scope for the brief but not for early batches.

### T5 — `computeSignal` unknown state *(data vs. field)*

**Data** (confidence 0.80): `computeSignal` needs an "unknown" state for malformed/missing inputs. Currently defaults without indication, which can produce false "ready" signals.

**No other panelist addresses this.**

**Assessment:** This is a data-integrity concern at the display boundary. It's small in scope (one branch addition + tests) and belongs with the formatting utility work in Batch 2. Not controversial — just unaddressed by other panelists.

## Recommendation

### Recommended Decomposition

The four stances converge on a layered decomposition. Reconciling the sequencing tensions produces:

```
Batch 0 — Foundation (prerequisite for everything)
  ├── Import global-styles/index.css
  ├── Extend sync-pds-assets.mjs for font self-hosting  ← security blocker
  ├── Update REQUIRED_PDS_ELEMENTS to match actual surface
  ├── Install @tailwindcss/vite, update Stylelint config
  └── Board horizontal scroll (overflow-x: auto)

  [HUMAN CHECKPOINT: visual re-audit]
  Re-evaluate which of the 73 findings self-resolved.
  Scope Batches 1-3 based on what remains.

Batch 1 — Token Migration + Formatting Utilities (atomic + parallel)
  ├── Token provenance map (four-way classification)
  ├── Delete tokens.css + migrate refs + create custom-tokens.css  ← atomic
  ├── Formatting utilities (utils/format.ts) with data constraints
  │     null-safe, config-driven enums, canonical/display partition
  ├── Extend computeSignal with "unknown" state + tests
  └── Component complexity inventory (planning artifact)

Batch 2 — Component Migration (informed by inventory)
  ├── Simple swaps: button → PButton, heading → PHeading, select → PSelect
  ├── Card visual treatment: priority color, signal icons, tag chips
  ├── Sidecar information architecture + section restructuring
  └── Complex integrations: shell tabs, filter panel controls

Batch 3 — Overlays + Feedback + Polish
  ├── Overlay track: custom modals → PModal, popovers, context menus
  ├── Success feedback: PToast for mutations, inline edit confirmation
  ├── Dark mode border contrast
  ├── Filter panel layout (horizontal bar or collapsible sidebar)
  └── Activity tab date grouping, ConflictBanner diff formatting
```

### Key Constraints (from stance convergence)

1. **Font self-hosting before or concurrent with foundation import** — non-negotiable per security (T1).
2. **Token migration is one atomic task** — delete + migrate + custom-tokens + test updates (C4).
3. **Formatting utilities enforce canonical/display partition** — formatted values never feed mutation APIs (C8).
4. **Human checkpoint after Batch 0** — re-audit scopes all subsequent work (C2).
5. **Enum vocabularies are config-driven** — no hardcoded status/priority sets in components (C7).
6. **`@tailwindcss/vite` only, never PostCSS** — preserves LightningCSS `light-dark()` exclusion (C3).

### Confidence: 0.82

High confidence in Batch 0 (all four stances agree on content and order). High confidence in the human-checkpoint gate. Moderate confidence in Batch 1-3 sequencing — the exact scope of later batches depends on what the post-foundation re-audit reveals.

## Open Questions

1. **Font self-hosting implementation complexity.** Security provides the mitigation path (extend `sync-pds-assets.mjs`), but the exact scope depends on how many font files PDS references and whether the rewrite can be done statically or needs a build-time transform. Needs investigation during Batch 0 planning.

2. **`@tailwindcss/vite` + LightningCSS `light-dark()` coexistence.** Architect flags this as needing a smoke test (confidence moderate). If it fails, the fallback is documented but would require re-planning Tailwind integration. Verify in Batch 0 before committing.

3. **Post-foundation re-audit scope.** How many of the 73 findings self-resolve? This determines whether Batches 1-3 are the right size or need further compression. Cannot be answered until Batch 0 ships.

4. **Sidecar section ordering.** Enduser proposes a specific information architecture (orientation → actions → content → DR → metadata → history). This is a reasoned proposal but needs user validation — it changes the existing layout significantly.

5. **Overlay track scope.** Architect flags overlay architecture (modals, popovers, context menus, dialogs) as a distinct cohesive track. Enduser treats modals as part of component migration. The right answer depends on how many overlay patterns exist and whether they share positioning/dismiss logic. The component inventory task should resolve this.

6. **ESLint ban for PDS `innerHTML` prop.** Security recommends it as defense-in-depth (R3). Low effort, no controversy — but needs to be an explicit task or it will be forgotten.
