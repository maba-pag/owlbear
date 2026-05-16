# PDS Motion/Transition Token Migration

> **Owning task:** #1627 — P3-08: Motion/transitions — PDS duration + easing tokens
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Three authored CSS transition declarations use hardcoded durations and easings. They should use PDS v4 motion tokens. The task AC references `--p-transition-duration` and `--p-transition-timing-function` — but these need correction against actual PDS v4 token surface.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| PDS v4 `global-styles/variables.css` (node_modules) | Primary — token definitions | 1.0 |
| PDS v4 `common-styles.ts` (GitHub source) | Primary — `getTransition()` internals | 0.9 |
| PDS v4 CSS Variables docs page (stylesheets/css-variables/api) | Primary — public token API | 1.0 |
| PDS v4 Motion tokens docs page (tokens/motion) | Primary — duration/easing guidance | 1.0 |
| PDS v4 Tailwind motion docs page | Secondary — Tailwind integration | 0.8 |
| PDS GitHub `packages/components/src/styles/` | Secondary — component patterns | 0.8 |
| Shell.css, Card.css (codebase) | Primary — current transition usage | 1.0 |
| SidecarCollapse_1549.test.tsx (codebase) | Primary — existing test lock | 0.9 |

## 3. Analysis

### 3a. PDS v4 Motion Token Inventory

| CSS Custom Property | Value | PDS guidance |
|---|---|---|
| `--p-duration-sm` | `0.25s` | Hover effects, buttons, switches, popovers |
| `--p-duration-md` | `0.4s` | Moderate motion: carousels, modals, link-tiles |
| `--p-duration-lg` | `0.6s` | Deliberate animations: notifications, flyouts |
| `--p-duration-xl` | `1.2s` | Very long motion (rare) |
| `--p-ease-in-out` | `cubic-bezier(0.25, 0.1, 0.25, 1)` | General transitions (= CSS `ease`) |
| `--p-ease-in` | `cubic-bezier(0, 0, 0.2, 1)` | Exit animations |
| `--p-ease-out` | `cubic-bezier(0.4, 0, 0.5, 1)` | Enter animations |

Note: `--p-transition-duration` exists as a PDS component-internal override variable (used in `getTransition()` as `var(--p-transition-duration, <fallback>)`). It is NOT a fixed-value token. `--p-transition-timing-function` does not exist in PDS v4 at all.

### 3b. AC1 Correction Required

| AC text | Problem | Corrected version |
|---|---|---|
| `--p-transition-duration` | Override variable, not a token | Use `--p-duration-sm` / `--p-duration-md` |
| `--p-transition-timing-function` | Does not exist in PDS v4 | Use `--p-ease-in-out` / `--p-ease-in` / `--p-ease-out` |

### 3c. Current Codebase Transitions

| Location | Current declaration | Duration | Easing |
|---|---|---|---|
| Shell.css `.shell` | `transition: grid-template-columns 250ms ease` | 250ms | ease |
| Shell.css `.icon-button` | `transition: background 120ms ease, border-color 120ms ease` | 120ms | ease |
| Card.css `.card` | `transition: box-shadow 120ms ease` | 120ms | ease |

Key observation: the codebase encodes a **two-tier motion hierarchy** — 250ms for layout changes (expand/collapse), 120ms for micro-interactions (hover/focus). CSS `ease` is semantically identical to `--p-ease-in-out`.

### 3d. Migration Trade-off Matrix

| Criterion | Option A: All `--p-duration-sm` | Option B: Layout=`sm`, micro=literal 120ms |
|---|---|---|
| PDS compliance | Full — all tokens from PDS | Partial — easing tokenized, micro-duration stays custom |
| UX continuity | 120ms bumps to 250ms (+108%) on hover | Preserves current two-tier hierarchy |
| Testability | Existing `SidecarCollapse_1549` test must update regex | Same test update needed |
| Maintainability | Single token for all durations | Two duration sources |
| PDS guidance fit | PDS recommends `--p-duration-sm` for hover effects | PDS has no sub-250ms token |
| Risk | Hover feels ~2× slower | Non-tokenized 120ms is technical debt |

### 3e. Route Transitions (AC3)

The app defines a single route (`/` → KanbanBoard). There are no route-to-route transitions to evaluate. AC3 ("route transitions smooth, no FOUC") is **untestable** in current state. PDS global-styles import + Vite bundling prevents FOUC on initial load. AC3 should be marked as N/A until routes are added, or interpreted as "initial render has no FOUC."

### 3f. `transition: all` Audit (AC2)

Zero `transition: all` declarations found in authored CSS. AC2 is already satisfied.

## 4. Recommendation

**Use Option A: full PDS tokenization** (confidence: 0.78).

Rationale: The 120→250ms bump aligns with PDS design intent for hover effects. PDS explicitly recommends `--p-duration-sm` for "hover effects on Buttons, Checkboxes, Switches." The current 120ms was a pre-PDS choice; adopting the design system means accepting its motion scale. The difference (130ms) is below the ~300ms threshold where users perceive delay.

Corrected AC1: replace `--p-transition-duration` / `--p-transition-timing-function` with `--p-duration-sm` and `--p-ease-in-out`.

AC3: mark as N/A for single-route SPA; validate when routes are added.

`prefers-reduced-motion` handling is out of scope (owned by #1628 accessibility sweep).

Challenge: reconsider — challenger flagged UX regression and AC naming. Revised from 0.85 to 0.78 after acknowledging the two-tier hierarchy trade-off. The 250ms PDS standard for hover effects is the stronger argument.

## 5. Follow-up Tasks

See task body for planner delegation.
