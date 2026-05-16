# Architect — Critic Debate Log

## Cycle 1

### Critic Challenges (5 substantive, 3 blind spots)

**C1 (Critical): Incomplete token inventory.** `--app-signal-claimed` is not the only app-specific token. Shell.css defines semantic aliases (`--pds-border-default`, `--pds-text-default`), Card.css has additional semantic vars, and tests lock these dependencies. Cannot prescribe custom-tokens.css contents without full inventory.

**Response: Accepted.** My initial "one variable" claim was wrong. Revised to require a complete token provenance map as prerequisite. Four-way classification: (a) has `--p-*` equivalent → migrate, (b) app-semantic → `--app-*`, (c) broken/undefined → delete with replacement value, (d) dead → delete.

**C2 (Critical): Atomic migration scope is larger than stated.** TokenArchitecture and PdsColorSchemeBridge tests hardcode the current tokens.css approach and must be updated in the same commit. Migration isn't just "delete + migrate references."

**Response: Accepted.** Atomic migration task scope expanded to include: delete tokens.css + migrate all `--pds-*` references + create custom-tokens.css + update/replace architectural proof tests + update main.tsx imports.

**C3 (Critical): Component migration task-per-type is too coarse.** Shell tabs have custom tabChange event handling with raw `p-tabs`/`p-sheet`. FilterPanel has manual update/input/change listeners with raw `p-checkbox`. TaskFieldsEditor has hide-label coupling. jsdom attachInternals shims exist in test harness. "One test for PButton behavior" doesn't match the actual contract surface.

**Response: Partially accepted.** The grouping principle (consistency across component type) stands, but complex integrations with custom event wiring and test harness dependencies need dedicated tasks. Revised to: simple swaps (task-per-type) + complex integrations (task-per-integration, each with test harness scope).

**C4 (Moderate): Tailwind utility migration savings overstated.** Most existing `--pds-*` references live in selector-driven CSS (attribute states, pseudo-states, drag states), not plain JSX. Can't become Tailwind utilities. Double-churn argument is weaker than claimed.

**Response: Accepted.** Revised rationale: Tailwind before migration is about setting the correct authoring pattern for NEW code written in Tiers 2-3 (utilities from day one), not about saving churn on existing code which mostly stays as `var(--p-*)` in CSS.

**C5 (Moderate): Stylelint rejects unknown at-rules.** `.stylelintrc.json` will reject Tailwind's `@theme`, `@import "tailwindcss"`. "Avoids pipeline reconfiguration" is too strong.

**Response: Accepted.** Added Stylelint config update to Tailwind installation task scope. Revised claim: pipeline reconfiguration is minimal but not zero.

**C6 (Minor): Board horizontal scroll already exists.** `overflow-x: auto` is already in KanbanBoard and guarded by ShellSecondaryCSS test. One advertised Tier 3 workstream is not actually open.

**Response: Accepted.** Removed from Tier 3. Post-foundation re-audit determines actual remaining layout work.

### Blind Spots Surfaced

1. **Bootstrap readiness contract is false today.** Only 4 elements in `REQUIRED_PDS_ELEMENTS`, actual PDS surface much larger. Noted for Cycle 2 discussion.
2. **Token provenance spans shell aliases, card semantic vars, and broken references.** Addressed by four-way classification in revised Claim 4.
3. **Test harness sensitivity** (jsdom shims, property-vs-attribute assertions). Added as new risk R7.

---

## Cycle 2

### Critic Challenges (5 substantive, 3 blind spots)

**C1 (Critical): Foundation sequencing lacks root-cause contract.** Research says Tailwind "does not add any capability that PDS CSS variables in plain CSS do not already provide." The position commits to "Foundation → Tailwind → Migration" but doesn't separate the root-cause fix (foundation) from the tooling decision (Tailwind).

**Response: Rebutted.** My decomposition already separates them: Foundation is Tier 0, Tailwind is Tier 0.5 — they're distinct tasks with a dependency edge. Foundation IS the root-cause fix (provides `--p-*` variables, fonts, normalize). Tailwind IS separate tooling adopted per D4. The arrow is sequencing, not coupling. Foundation can land and be validated independently. Tailwind follows because PDS Tailwind theme references `--p-*` variables that Foundation provides. The Critic reads tight coupling where there is ordered independence.

**C2 (Critical): Token provenance model still too narrow — doesn't handle broken/undefined references.**

**Response: Partially accepted.** Added fourth classification category (broken/undefined → delete with replacement). But the Critic overstates the novelty — VF-4 in research notes already identified `--pds-border-subtle` and `--pds-text-subtle` as defined nowhere. These are known broken references. The mapping is a prerequisite engineering task, not an open research question.

**C3 (Critical): Theme model not settled.** `light-dark()`, `data-theme`, `.scheme-dark`/`.scheme-light`, `useTheme` hook, `theme-bootstrap.js` all coexist. Multiple test suites encode the current contract.

**Response: Addressed.** The theme stack is actually settled, not open. Here's the resolution chain:
- `useTheme` hook sets BOTH `.scheme-dark`/`.scheme-light` classes AND `data-theme` attribute
- PDS `light-dark()` is resolved by browser `color-scheme` CSS property (set by PDS `color-scheme.css`)
- PDS components read `.scheme-dark`/`.scheme-light` — this already works with the hook
- `data-theme` attribute is consumed only by `tokens.css` manual overrides
- After tokens.css deletion, `data-theme` becomes vestigial but harmless
- Theme switching continues to work because the hook already sets the classes PDS needs
- The bootstrap theme script (`theme-bootstrap.js`) prevents FOUC — preserved as-is
- The architectural tests need updating to reflect the new token source, not new theme mechanics

This is not an open question. It's a migration that preserves the existing theme switching mechanism while removing the redundant `data-theme` consumer.

**C4 (Critical): Bootstrap readiness cannot be deferred.** The readiness list is already wrong (4 elements vs. much larger actual surface). Preserves a known broken invariant.

**Response: Accepted.** Promoted from "deferred" to "included in foundation task." The Foundation task should update `REQUIRED_PDS_ELEMENTS` to match the actual PDS custom-element surface. This is a correctness fix, not a feature addition.

**C5 (Moderate): Component decomposition is underspecified — simple/complex boundary is unstable.** ThemeToggle, HealthBadge, DRStatusIndicator, ErrorBoundary all have raw elements with behavioral concerns that don't fit "simple swap."

**Response: Accepted direction, rebutted severity.** The decomposition detail belongs in Brief Phase 2 task planning, not in the architectural stance. The stance establishes the principle (inventory-driven decomposition with behavioral risk as the axis) and the prerequisite (component inventory with complexity classification). Exact task boundaries are a planning concern.

### Blind Spots Surfaced

1. **Overlay/disclosure architecture absent.** Hand-rolled fixed-position overlays (context menu, popovers, dialogs, modals) are a distinct architectural concern from component swaps. **Accepted.** Added as Tier 2 concern: overlay migration is its own decomposition track (PModal, PPopover candidates).
2. **Passive sidecar content surface absent.** DetailTab metadata, DecisionViewport content still use raw paragraph/strong structures. **Accepted.** Belongs in post-foundation re-audit scope.
3. **PSelect composition.** Native `<option>` children inside PSelect is a known API concern. **Accepted.** Flagged as migration detail — PSelect may need different child API.

### Position Stability Assessment

After two cycles, the core structural judgments hold:
- `@tailwindcss/vite` over PostCSS — unchallenged
- Foundation → Tooling → Migration → Components/Layout → Polish — challenged on coupling, rebutted
- Atomic migration with expanded scope — refined, accepted
- Theme model — challenged as "open," resolved as "settled"
- Bootstrap readiness — promoted from deferred to included

Remaining gaps are decomposition granularity (planning, not architecture) and component inventory (prerequisite, not structural).
