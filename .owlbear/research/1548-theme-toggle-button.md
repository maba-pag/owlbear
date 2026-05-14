# Theme Toggle UI: Status Bar Button — Implementation Research

> **Owning task:** #1548 — P3-06: impl — theme toggle UI: status bar button
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

How should a theme toggle button be implemented in the Cockpit status bar (right side)? The button must call `useTheme().toggle` to cycle light → dark → auto and visually indicate current state.

**Dependencies (both done):** #1540 (tests exist at `ThemeToggle.test.tsx`), #1545 (`useTheme` hook + bootstrap script shipped).

**Existing state:** The status bar (`shell__status-bar` in `Shell.tsx`) is a `<header>` with traffic light, task count, HealthBadge, CleanupPanel, scan error retry, and DRStatusIndicator — all flex children. No ThemeToggle component exists. Tests expect `components/ThemeToggle` default export.

## 2. Sources Studied

| # | Source | URL/Path | Relevance |
|---|--------|----------|-----------|
| 1 | web.dev — Building a theme switch component | web.dev/articles/building/a-theme-switch-component | 0.95 — canonical `<button>` + SVG sun/moon + `aria-label` pattern |
| 2 | next-themes ThemeScript | github.com/pacocoursey/next-themes | 0.80 — `aria-label` set to current theme value for screen readers |
| 3 | Existing DRStatusIndicator | `src/components/DRStatusIndicator.tsx` | 0.95 — local convention: PButton in status bar, aria-label |
| 4 | Existing useTheme hook | `src/hooks/useTheme.ts` | 1.00 — API: `{ theme, toggle, isDark }` |
| 5 | Existing ThemeToggle tests | `src/__tests__/ThemeToggle.test.tsx` | 1.00 — expected: default export, button role, toggle call, distinct labels per state |
| 6 | #1540 research doc | `.owlbear/research/1540-theme-toggle-ui-test-approach.md` | 0.95 — mock pattern, AC mapping |

## 3. Analysis

### 3.1 Component Structure

| Option | Description | Complexity | Matches tests | KISS |
|--------|-------------|-----------|---------------|------|
| **A: Plain `<button>` + inline SVG** | Vanilla HTML button with sun/moon/auto icon, `aria-label` | Low | Yes | High |
| **B: PButton wrapper** | Use `<PButton>` like DRStatusIndicator/HealthBadge | Low | Likely — PButton renders `role="button"` | High |
| C: Radix/headless toggle | External toggle primitive | Medium | Maybe | Low |

Both A and B satisfy the test query `getByRole('button')`. Option B matches the codebase convention — every status bar button uses `PButton`. Option A is simpler but diverges from existing patterns.

**Recommendation: B (`PButton`)** — confidence 0.88. Matches local convention. PDS handles focus ring, touch target sizing, and theming. The test mock checks `getByRole('button')` which PButton satisfies.

### 3.2 Visual State Indication (AC-3)

Tests check that button accessible name or content differs per state. Three approaches:

| Approach | Mechanism | Accessible | Source |
|----------|-----------|------------|--------|
| **A: aria-label per state** | `aria-label="Theme: light"` / `"Theme: dark"` / `"Theme: auto"` | Yes | web.dev guide |
| **B: Text label** | `textContent` = "Light" / "Dark" / "Auto" | Yes | Simple |
| **C: Icon + aria-label** | SVG sun/moon icon + aria-label | Yes | web.dev guide (enhanced) |

Tests use `getByRole('button')` then check `aria-label` and `textContent`. Any approach works. Option C (icon + label) is the richest UX but requires SVG icons. Option B is simplest.

**Recommendation: B (text label) for initial impl** — confidence 0.85. The tests assert `aria-label` OR `textContent` differs per state. A text label is the simplest passing implementation. Icons can be added later as polish.

### 3.3 Theme Label Mapping

The toggle cycles: light → dark → auto. Each state needs a distinct label:

| `theme` | Label | Tooltip/title |
|---------|-------|---------------|
| `light` | "Light" | "Switch to dark theme" |
| `dark` | "Dark" | "Switch to auto theme" |
| `auto` | "Auto" | "Switch to light theme" |

The `aria-label` should include "Theme:" prefix for context: `"Theme: light"`, `"Theme: dark"`, `"Theme: auto"`.

### 3.4 Shell Integration

The ThemeToggle should be placed at the right end of the status bar, after DRStatusIndicator. Existing status bar items are flex children — adding `<ThemeToggle />` at the end puts it rightmost.

| Placement | Position | Matches AC-1 |
|-----------|----------|------|
| **After DRStatusIndicator** | Rightmost in status bar | Yes — "right side" per brief |
| Before HealthBadge | Left side | No |

**Recommendation: rightmost, after all existing indicators** — confidence 0.92.

### 3.5 File Structure

Tests import from `'../components/ThemeToggle'`. The component must be:
- **Path:** `src/components/ThemeToggle.tsx`
- **Export:** `export default function ThemeToggle()`
- **Dependencies:** `useTheme` from `../hooks/useTheme`, `PButton` from PDS (optional)

Estimated size: ~20-30 lines. No CSS file needed — PButton handles styling.

## 4. Recommendation

**Implementation plan (confidence: 0.88):**

1. Create `src/components/ThemeToggle.tsx` — default export, calls `useTheme()`, renders `PButton` with `aria-label="Theme: {theme}"` and text content showing current state.
2. Add `<ThemeToggle />` to `Shell.tsx` status bar as the last child before `</header>`.
3. No new dependencies, no new CSS files.

**Risks:**
- PButton may wrap content differently than tests expect → Mitigation: tests use `getByRole('button')` which PButton satisfies; verify during GREEN phase.
- Status bar crowding → Low risk: button is compact, existing items handle overflow.

**Challenge: skipped** — trivial component with no architecture decisions. Single-file creation + single-line Shell edit. All patterns well-established in codebase.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #1548 is the implementation task. Its tests (#1540) already exist and pass expectations are well-defined.
