# Card Component CSS Test Approach

> **Owning task:** #1538 — P3-01: test — card component CSS: signal border, hover, focus, selected states
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1538 writes RED Vitest tests for card CSS visual states: `data-signal` attribute rendering, left-border color mapping per signal, and `[data-selected]` box-shadow/outline. The implementation (#1546) will create `Card.css` and wire `computeSignal()` into the Card component.

**Research questions:**
1. Can JSDOM test CSS computed styles from stylesheets?
2. What test approach handles both DOM attribute and CSS rule verification?
3. What color values should tests expect per signal?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/cockpit/web/src/components/Card.tsx` | Codebase | 1.0 — current Card: inline styles, `PRIORITY_COLORS`, no `data-signal` |
| S2 | `serve/cockpit/web/src/tokens.css` | Codebase | 1.0 — current 19-var light-only token set |
| S3 | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | Codebase | 0.9 — file-based `readFileSync` + regex test pattern |
| S4 | Vitest issue #1689 (getComputedStyle limitation) | Web | 0.9 — confirms JSDOM doesn't apply imported CSS |
| S5 | SO: vitest cannot test for presence of specific styling | Web | 0.8 — community consensus: use E2E for computed styles |
| S6 | `.owlbear/research/1535-token-architecture-test-approach.md` | Codebase | 0.9 — established file-based CSS parse pattern |
| S7 | `.owlbear/research/card-signal-data-model-1536.md` | Codebase | 1.0 — `computeSignal()` signature and placement |
| S8 | Board Visual Design brief (#1534) | Brief | 1.0 — signal model, card spec, color mapping |

## 3. Analysis

### 3.1 JSDOM CSS Limitation

JSDOM does not resolve CSS from stylesheets. `getComputedStyle()` returns empty/default values for properties set via `<link>` or imported CSS. CSS custom properties (`var(--pds-*)`) are not resolved (S4, S5). This means **any test verifying border-left-color, box-shadow, or hover/focus styling cannot use DOM render + getComputedStyle**.

### 3.2 Test Approach Comparison

| Approach | AC-1 (data-signal attr) | AC-2 (border color) | AC-3 (selected style) | Fit |
|----------|------------------------|---------------------|----------------------|-----|
| **A: Split (DOM + file-parse)** | render Card → assert attr | readFile Card.css → regex | readFile Card.css → regex | ✅ Best |
| B: All DOM/render | render → assert attr | getComputedStyle → ❌ | getComputedStyle → ❌ | ❌ AC-2/3 fail |
| C: All file-based | parse Card.tsx → fragile | readFile → regex | readFile → regex | ❌ AC-1 lossy |
| D: E2E (Playwright) | full browser | full browser | full browser | ❌ Wrong layer |

**Approach A** splits testing into two complementary strategies:
- **AC-1**: DOM render test (Card component renders `data-signal` attribute correctly)
- **AC-2, AC-3**: File-based CSS parsing (Card.css contains correct selectors + property values)

This follows the PDSHexScan (S3) and token architecture (S6) precedent.

### 3.3 AC-1: data-signal Attribute Rendering

The test renders Card with various task states and asserts `data-signal` attribute. Card.tsx currently lacks `data-signal` — the test is RED until #1546 adds it.

| Test case | Task state | Expected data-signal |
|-----------|------------|---------------------|
| DR pending | id in pendingDRIds | `dr-pending` |
| Blocked | blocked=true | `blocked` |
| Claimed | claimed=true | `claimed` |
| Deps unmet | dep_status="blocked" | `deps-unmet` |
| Ready (default) | no flags | `ready` |

**Self-contained design:** Tests define expected signal values inline using a test-local mapping table — no import of `computeSignal` needed. The test asserts the rendered DOM attribute matches the brief's signal model directly. This avoids coupling to #1544's implementation.

### 3.4 AC-2: Signal → Border-Left Color CSS Mapping

File-based test reads `Card.css` (created by #1546) and verifies each `[data-signal="X"]` selector declares a `border-left-color` with the brief's specified color.

| Signal | Brief color | Expected CSS value | Token source |
|--------|-------------|-------------------|-------------|
| `dr-pending` | Orange | `var(--pds-notification-warning)` | Existing token |
| `blocked` | Red | `var(--pds-notification-error)` | Existing token |
| `claimed` | Purple | `var(--pds-signal-claimed)` | Custom (see §3.6) |
| `deps-unmet` | Grey | `var(--pds-contrast-medium)` | Existing token |
| `ready` | White/Black | Theme-aware: no `border-left-color` override (inherits from base) or explicit `var(--pds-primary)` | Theme-dependent |

Test structure: read `Card.css` with `readFileSync`, match `[data-signal="X"]` selector blocks, assert `border-left-color` property with specific token reference per brief. The `ready` signal should verify absence of explicit border-left-color (inheriting default) or presence of `var(--pds-primary)` — the test-writer should pick one and document the choice.

### 3.5 AC-3: Selected State Styling

File-based test verifies `[data-selected="true"]` or `[data-selected]` selector in Card.css declares `box-shadow` or `outline` (distinct from border-left). Brief says: "Selected: box-shadow or outline (green from PDS success)."

Test asserts: selector exists with either `box-shadow` or `outline` property referencing `var(--pds-notification-success)`.

### 3.6 Purple Color Gap

PDS v4 tokens include no purple color. Current `tokens.css` has: notification-warning (orange), notification-error (red), notification-info (blue), notification-success (green). No purple/violet.

| Resolution | Approach | Risk |
|------------|----------|------|
| Custom signal token | `--pds-signal-claimed: hsl(270 60% 55%)` in tokens.css | Clean; adds 1 non-PDS token |
| Per-signal token set | `--pds-signal-{name}` for all 5 signals | Clean abstraction layer |
| Reuse notification-info | Blue ≈ Purple | Brief explicitly says purple — color mismatch |

**Revised recommendation:** The test should expect a specific token: `var(--pds-signal-claimed)` for purple. This makes the test fail RED until the token is added by the token architecture (#1543) or card impl (#1546). The brief's color intent (purple) is non-negotiable — the test protects that. Using a per-signal token set (`--pds-signal-{name}`) is cleanest but is an impl concern for the builder.

### 3.7 Hover/Focus Pseudo-Selectors (First-Class Coverage)

The task title and scope explicitly include hover and focus states. Brief specifies:
- **Hover:** subtle background shift using PDS `state-hover` token
- **Focus:** PDS focus ring via `focus-visible` pseudo-selector

These pseudo-selectors cannot be triggered in jsdom. File-based CSS parsing is the only viable Vitest approach:
- Verify `:hover` pseudo-selector exists with `background` property referencing `var(--pds-state-hover)`
- Verify `:focus-visible` pseudo-selector exists with `outline` property referencing `var(--pds-state-focus)`

These are **not optional** — they are first-class test assertions, not bonus coverage.

### 3.8 Existing Selection Test Overlap

`Shell.card-selection.integration.test.tsx` already tests `data-selected` attribute transitions at integration level (click card → `data-selected="true"`). AC-3 tests a different concern: the **CSS styling** triggered by `[data-selected]` (box-shadow/outline). No duplication — #1538 tests the visual contract, the existing test tests the interaction contract.

### 3.9 File Placement

| Artifact | Path | Rationale |
|----------|------|-----------|
| DOM render test (AC-1) | `src/__tests__/Card.signal.test.tsx` | Component rendering, follows existing `Shell.*.test.tsx` pattern |
| CSS parse test (AC-2, AC-3, hover/focus) | `src/__tests__/Card.css.test.ts` | File-based, follows `PDSHexScan_1395.test.ts` pattern |

### 3.10 Test Count Estimate

- AC-1: 5 signal states rendered with correct `data-signal` = 5 cases
- AC-2: 5 signals × selector + specific `border-left-color` token = 5 cases
- AC-3: `[data-selected]` → box-shadow or outline with success token, distinctness from border-left = 2 cases
- Hover: `:hover` selector with `background` property + state-hover token = 1 case
- Focus: `:focus-visible` selector with `outline` property + state-focus token = 1 case
- **Total: ~14 test cases across 2 files**

### 3.11 Why Not Playwright?

All three ACs explicitly say "Vitest verifies" — Playwright is out of scope by AC text. The repo does ship a Playwright lane and uses `getComputedStyle` in e2e tests (`kanban-board.spec.ts`), so browser-backed CSS verification is feasible as future supplemental coverage, but not the contract this task defines.

## 4. Recommendation

**Split test approach** (confidence: 0.75, revised from 0.85 after challenger):
- AC-1: DOM render in `Card.signal.test.tsx` — render Card with task fixtures, assert `data-signal` attribute per operational state. Self-contained (no `computeSignal` import)
- AC-2 + AC-3 + hover/focus: File-based CSS parsing in `Card.css.test.ts` — `readFileSync` on `Card.css`, regex for `[data-signal]`, `[data-selected]`, `:hover`, `:focus-visible` selectors with specific token references per brief

Key constraints from challenger review:
- Tests verify brief's **exact color semantics** (orange, red, purple, grey, theme-aware), not just generic var references
- Purple requires custom token (`--pds-signal-claimed`) — test fails RED until token exists
- Hover/focus are first-class coverage, not optional
- No dependency on `computeSignal` import — tests are self-contained
- AC-3 complements (not duplicates) existing `Shell.card-selection.integration.test.tsx`

Challenge: reconsider (confidence in original: 0.57). Accepted: purple dilution, computeSignal coupling, hover/focus demotion, Playwright observation. Rebutted: Playwright for this task (ACs say "Vitest"), two-file split remains justified (TSX vs TS file-type separation).

## 5. Follow-up Tasks

None beyond #1538 itself — task scope is already correct. The purple color gap is noted as a constraint for the test-writer (expect `--pds-signal-claimed` token) and a signal for the token architecture builder (#1543).
