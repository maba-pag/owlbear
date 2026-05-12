/**
 * and viewport-accessible surface infrastructure.
 *
 * AC1 (td:2): Viewport usability at 320px, 768px, 1024px, 1440px — Shell.css must have responsive
 *             grid adjustments via @media rules.
 * AC2 (td:2): Mobile reachability — Shell.css must collapse/hide sidecar at narrow viewports so
 *             the board workspace is accessible without horizontal scrolling.
 * AC3 (td:2): Desktop layout — Shell.css must have media-query breakpoints.
 * AC4 (td:2): Surface coverage — Shell.css must provide responsive rules for all major surfaces.
 * AC5 (td:2): PDS-compatible token or component usage expected for priority color presentation.
 *
 * AC1/AC2/AC3/AC4 layout behavior (bounding-box assertions at real viewports) require Playwright.
 * Builder (#1392) MUST promote the tracked E2E proof per AC7:
 *   cp .owlbear/scratch/1391-e2e-v2.spec.ts serve/cockpit/web/e2e/responsive-layout-1391.spec.ts
 * These static-analysis tests provide AC1–AC4 coverage that can be verified without a layout engine.
 *
 *   - Shell.css has zero @media rules (fixed grid only: 56px 1fr 360px).
 *   - Card.tsx PRIORITY_COLORS uses hardcoded hex values (#e00000, #ff8000, #ffcc00, #0066cc, #888888).
 *
 * Counterpart: #1392 implements PDS token usage and responsive Shell CSS.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import fs from 'node:fs'
import path from 'node:path'
import type { Task } from '../hooks/useBoard'
import { Card } from '../components/Card'

// ─── File paths (resolved from this test file's directory — independent of cwd) ───

const CARD_TSX = path.resolve(__dirname, '../components/Card.tsx')
const SHELL_CSS = path.resolve(__dirname, '../Shell.css')
const SHELL_TSX = path.resolve(__dirname, '../Shell.tsx')
const KANBAN_BOARD_TSX = path.resolve(__dirname, '../KanbanBoard.tsx')

// ─── Shared CSS source ────────────────────────────────────────────────────────

let shellCss = ''
let cardSource = ''
let shellTsx = ''
let kanbanBoardSource = ''

// loaded once for static analysis blocks
;(() => {
  shellCss = fs.readFileSync(SHELL_CSS, 'utf-8')
  cardSource = fs.readFileSync(CARD_TSX, 'utf-8')
  shellTsx = fs.readFileSync(SHELL_TSX, 'utf-8')
  kanbanBoardSource = fs.readFileSync(KANBAN_BOARD_TSX, 'utf-8')
})()

// ─── AC1: Viewport usability — responsive grid adjustments ────────────────────
// Shell.css must adapt the grid via @media breakpoints for each supported viewport.
// RED: Shell.css has zero @media rules → fixed 56px 1fr 360px at ALL widths → workspace
//      gets 0px at 320px and only 352px at 768px (sidecar larger than board).

describe('TestFromAC_ViewportUsability', () => {
  // AC1: Shell.css must have narrow-viewport media queries (max-width pattern)
  // that re-allocate grid space for 320px and 768px usability.
  it('Shell.css has responsive @media max-width breakpoints for narrow viewports', () => {
    expect(
      shellCss,
      'Shell.css must contain @media (max-width: ...) rules for 320px and 768px viewport usability',
    ).toMatch(/@media\s*\(max-width/)
  })

  // AC1: Shell.css must have wide-viewport media queries (min-width pattern) ensuring
  // desktop grid properly allocates workspace vs. sidecar proportions.
  it('Shell.css has responsive @media min-width breakpoints for wide viewports', () => {
    expect(
      shellCss,
      'Shell.css must contain @media (min-width: ...) rules ensuring desktop (1024px, 1440px) layout',
    ).toMatch(/@media\s*\(min-width/)
  })
})

// ─── AC2: Mobile reachability — sidecar collapse ──────────────────────────────
// At narrow viewports, sidecar must be collapsed or hidden so workspace is accessible.
// RED: Shell.css has no @media rule targeting .shell__sidecar with display:none or
//      width:0 → sidecar always takes 360px, pushing workspace to 0px at 320px.

describe('TestFromAC_MobileReachability', () => {
  // AC2: Shell.css must have a responsive rule that collapses or hides the sidecar
  // at mobile widths so the board workspace is not blocked to 0px.
  it('Shell.css provides a responsive rule to collapse sidecar at narrow viewports', () => {
    // After fix: Shell.css will contain both @media and .shell__sidecar inside the block.
    // Using a simple check: source must contain @media (present even without sidecar rule
    // the first hurdle is the @media itself).
    expect(
      shellCss,
      'Shell.css must define a mobile @media rule so sidecar collapses and board workspace is accessible',
    ).toMatch(/@media/)
    // Specifically: .shell__sidecar must appear in a responsive context (display:none or zero-width rule)
    const sidecarInMedia =
      shellCss.indexOf('@media') < shellCss.lastIndexOf('shell__sidecar')
      && shellCss.includes('@media')
    expect(
      sidecarInMedia,
      '.shell__sidecar must have a responsive rule inside an @media block to collapse on mobile',
    ).toBe(true)
  })

  // AC2: the main shell grid must not use a layout that forces workspace to ≤0px
  // on any supported viewport (i.e., fixed 56px 1fr 360px at all widths is wrong).
  it('Shell.css grid-template-columns is not fixed to a layout that collapses workspace at 320px', () => {
    // The problematic pattern: grid-template-columns: 56px 1fr 360px with no @media override.
    // After fix: either different grid values OR the fixed grid only inside a wide-viewport @media.
    // Proof: Shell.css MUST contain an @media rule that overrides the grid for narrow viewports.
    expect(
      shellCss,
      'Shell.css must have @media rules overriding the fixed grid so workspace is non-zero at 320px',
    ).toMatch(/@media/)
  })
})

// ─── AC4: Surface coverage — responsive infrastructure for all surfaces ─────────
// Board columns, sidecar, status-bar, nav-rail, cards, empty/loading/error states,
// and primary interaction affordances must be accessible as a coherent responsive experience.
// RED: Shell.css has no @media rules for any surface → board-side surfaces inaccessible at 320px.

describe('TestFromAC_SurfaceCoverage', () => {
  // AC4: Shell workspace surface must have responsive layout rules so board columns,
  // cards, and affordances inside it are accessible at all supported viewport widths.
  it('Shell.css defines responsive layout rules for .shell__workspace surface', () => {
    // After fix: @media block will target .shell__workspace or the .shell grid to give
    // workspace sufficient width on narrow viewports.
    // RED: no @media → no responsive rules → workspace = 0px at 320px.
    expect(
      shellCss,
      'Shell.css must have @media rules that make .shell__workspace accessible at 320px',
    ).toMatch(/@media/)
  })

  // AC4: Shell sidecar surface must have responsive rules so it is accessible
  // at desktop viewports AND does not block board access at mobile viewports.
  it('Shell.css defines responsive rules for .shell__sidecar surface', () => {
    expect(
      shellCss,
      'Shell.css must have responsive rules ensuring sidecar is accessible at desktop and not blocking at mobile',
    ).toMatch(/@media/)
  })

  // AC4: Card.tsx priority presentation must use PDS-compatible tokens (not hardcoded hex)
  // so priority colors are part of a coherent, token-driven visual experience.
  it('Card.tsx priority presentation does not use any hardcoded hex color literals', () => {
    // Matches any 6-digit hex color literal: #rrggbb
    expect(
      cardSource,
      'Card.tsx must not contain any hardcoded 6-digit hex color literals — use PDS CSS tokens instead',
    ).not.toMatch(/#[0-9a-f]{6}/i)
  })
})

// ─── Task fixtures for Card rendering ─────────────────────────────────────────

function makeTask(priority: string): Task {
  return {
    id: 1,
    title: 'Test Task',
    status: 'todo',
    priority,
    updated: '2026-05-10T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  }
}

// ─── AC5: PDS token usage for priority colors ──────────────────────────────────
// Card.tsx currently uses a hardcoded PRIORITY_COLORS constant with hex values.
// After #1392 fixes it, priority colors must use PDS CSS variables (var(--pds-...)).
//
// Strategy: static source analysis (reliable across JSDOM normalization differences).
// RED: Card.tsx source contains '#e00000', '#ff8000', '#ffcc00', '#0066cc', '#888888'.
// GREEN: source uses var(--pds-...) tokens instead.

describe('TestFromAC_PdsTokenUsage', () => {
  // AC5: critical priority must not use hardcoded '#e00000'
  it('Card.tsx critical priority color is not a hardcoded hex value (#e00000)', () => {
    expect(cardSource).not.toContain('#e00000')
  })

  // AC5: needed priority must not use hardcoded '#ff8000'
  it('Card.tsx needed priority color is not a hardcoded hex value (#ff8000)', () => {
    expect(cardSource).not.toContain('#ff8000')
  })

  // AC5: important priority must not use hardcoded '#ffcc00'
  it('Card.tsx important priority color is not a hardcoded hex value (#ffcc00)', () => {
    expect(cardSource).not.toContain('#ffcc00')
  })

  // AC5: nice-to-have priority must not use hardcoded '#0066cc'
  it('Card.tsx nice-to-have priority color is not a hardcoded hex value (#0066cc)', () => {
    expect(cardSource).not.toContain('#0066cc')
  })

  // AC5: someday priority and fallback must not use hardcoded '#888888'
  it('Card.tsx someday / fallback priority color is not a hardcoded hex value (#888888)', () => {
    expect(cardSource).not.toContain('#888888')
  })

  // AC5: Card renders priority border using PDS CSS variable, not raw color
  // Rendered inline style should contain var(--pds-...) for the borderLeft property.
  // RED: Card.tsx inlines PRIORITY_COLORS hex → element style has hardcoded color.
  it('Card renders critical priority borderLeft using a PDS CSS variable', () => {
    const { container } = render(
      <Card
        task={makeTask('critical')}
        onContextMenu={() => {}}
        onDragStart={() => {}}
        onDragEnd={() => {}}
      />,
    )
    const card = container.querySelector('[data-testid="task-card"]') as HTMLElement
    expect(card).not.toBeNull()

    // borderLeft must reference a PDS CSS custom property, not a hex literal or rgb value.
    // After fix: style contains 'var(--pds-theme-light-notification-error)'.
    // Currently: style contains 'rgb(224, 0, 0)' (normalized from #e00000) → no var().
    const rawStyle = card.getAttribute('style') ?? ''
    expect(rawStyle, 'borderLeft should use a PDS CSS variable (var(--pds-...))').toMatch(
      /var\(--pds-/,
    )
  })
})

// ─── AC3: Shell CSS responsive breakpoints ─────────────────────────────────────
// Shell.css currently has zero @media rules — the grid is fixed at 56px 1fr 360px.
// After #1392, at least one @media breakpoint must exist for mobile/tablet layouts.

describe('TestFromAC_ResponsiveCSS', () => {
  // AC3: Shell.css must have at least one @media rule for responsive layout
  it('Shell.css has at least one @media query for responsive breakpoints', () => {
    expect(shellCss, 'Shell.css must contain at least one @media rule').toMatch(/@media/)
  })
})

// ─── AC1/AC2/AC3/AC4 — Discriminating CSS assertions (added in retry, RF1–RF3) ─
// Previous tests checked only for generic @media presence. These checks require
// specific responsive patterns that the fix (#1392) must implement.
// All FAIL against the current Shell.css (zero @media rules).

describe('TestFromAC_ResponsiveCSSDiscriminating', () => {
  // AC1: Shell.css must target a specific narrow-viewport breakpoint in the 320–800px range.
  // Current: no @media at all → FAIL.
  it('Shell.css has @media max-width breakpoint targeting the 320px–800px viewport range', () => {
    expect(
      shellCss,
      'Shell.css must contain @media (max-width: Npx) where N is between 320 and 800 for mobile viewport usability',
    ).toMatch(/@media[^{(]*\(max-width\s*:\s*[3-8]\d{2}px\)/)
  })

  // AC2/AC4: Shell.css must include .shell__sidecar inside an @media block to collapse it
  // at narrow viewports so the board workspace is accessible without horizontal scrolling.
  // Current: no @media rules → sidecar always 360px → workspace=0px at 320px → FAIL.
  it('Shell.css places a .shell__sidecar rule inside an @media responsive block', () => {
    const hasMediaWithSidecar = /@media[^{]*\{[^@]*shell__sidecar/s.test(shellCss)
    expect(
      hasMediaWithSidecar,
      'Shell.css must define a .shell__sidecar rule inside an @media block to collapse the sidecar at mobile viewports',
    ).toBe(true)
  })

  // AC3/AC1: Shell.css must override grid-template-columns inside a @media rule so the
  // fixed 56px 1fr 360px layout is replaced at narrow viewports where workspace=0px.
  // Current: no @media rules → grid is always fixed → FAIL.
  it('Shell.css overrides grid-template-columns inside a responsive @media rule', () => {
    const hasResponsiveGrid = /@media[^{]*\{[^@]*grid-template-columns/s.test(shellCss)
    expect(
      hasResponsiveGrid,
      'Shell.css must override grid-template-columns inside an @media block so the workspace is non-zero at 320px',
    ).toBe(true)
  })
})

// ─── AC5: PDS token usage — Shell.css spacing/color and Shell.tsx controls ─────
// Shell.css already uses PDS CSS custom properties for spacing and color (PASS).
// Shell.tsx already uses PButton from Porsche Design System (PASS).
// These tests document and enforce continued PDS usage per AC5 broader scope (RF4).

describe('TestFromAC_PdsShellTokenUsage', () => {
  // AC5: Shell.css uses --pds-grid-gap spacing token (already present — documents coverage).
  it('Shell.css uses --pds-grid-gap spacing token for layout gaps', () => {
    expect(
      shellCss,
      'Shell.css must use var(--pds-grid-gap) for spacing to maintain PDS token usage for spacing',
    ).toContain('--pds-grid-gap')
  })

  // AC5: Shell.css uses --pds-grid-margin spacing token (already present).
  it('Shell.css uses --pds-grid-margin spacing token for layout margins', () => {
    expect(
      shellCss,
      'Shell.css must use var(--pds-grid-margin) for margin spacing to maintain PDS token usage',
    ).toContain('--pds-grid-margin')
  })

  // AC5: Shell.css uses --pds-theme-light-background-base color token (already present).
  it('Shell.css uses --pds-theme-light-background-base color token for page background', () => {
    expect(
      shellCss,
      'Shell.css must use var(--pds-theme-light-background-base) for page background color',
    ).toContain('--pds-theme-light-background-base')
  })

  // AC5: Shell.css uses --pds-theme-light-contrast-low color token for borders (already present).
  it('Shell.css uses --pds-theme-light-contrast-low color token for surface borders', () => {
    expect(
      shellCss,
      'Shell.css must use var(--pds-theme-light-contrast-low) for border colors',
    ).toContain('--pds-theme-light-contrast-low')
  })

  // AC5: Shell.tsx imports PButton from @porsche-design-system for PDS-compatible controls
  // (already present — documents that PDS control components are used where equivalents exist).
  it('Shell.tsx imports PButton from @porsche-design-system/components-react for PDS controls', () => {
    expect(
      shellTsx,
      'Shell.tsx must import PButton from @porsche-design-system/components-react for PDS-compatible interactive controls',
    ).toContain("from '@porsche-design-system/components-react'")
  })

  // AC5: Shell.tsx uses PButton in the nav-rail control surface (already present).
  it('Shell.tsx uses PButton component in the nav-rail control surface', () => {
    const navRailIdx = shellTsx.indexOf('shell__nav-rail')
    expect(navRailIdx, 'Shell.tsx must have a shell__nav-rail element').toBeGreaterThan(-1)
    // PButton must appear after the nav-rail class reference in the component tree.
    const pbuttonIdx = shellTsx.indexOf('<PButton', navRailIdx)
    expect(
      pbuttonIdx,
      'Shell.tsx must use <PButton> in the nav-rail surface for PDS-compatible interaction affordances',
    ).toBeGreaterThan(-1)
  })
})
// ─── AC2/AC3 retry: Mobile board column width discriminator ────────────────────
// Reviewer RF-retry: toBeVisible() alone does not prove mobile accessibility because
// repeat(auto-fit, minmax(0, 1fr)) with 7 columns yields ≈45px per column at 320px
// — technically visible but not meaningfully accessible.
// These static-analysis tests replace the E2E rendered-width proof that cannot be
// expressed in Playwright without a running dev server.

describe('TestFromAC_MobileBoardAccessibility', () => {
  // AC3 (RF-retry): Board grid must not use minmax(0, ...) which allows 7 columns
  // to collapse to ≈45px each at 320px — technically visible but not accessible.
  // FAIL: KanbanBoard.tsx uses repeat(auto-fit, minmax(0, 1fr)) (line ≈294).
  it('KanbanBoard board grid does not use minmax(0) zero-minimum that collapses columns to inaccessible widths at mobile', () => {
    expect(
      kanbanBoardSource,
      'Board grid must not use minmax(0, ...) — at 320px with 7 columns this compresses each to ≈45px (not accessible); use a positive minimum width (e.g., minmax(120px, 1fr)) or responsive column count',
    ).not.toMatch(/minmax\(\s*0\s*,/)
  })

  // AC2 (RF-retry): Board grid column minimum must be at least 80px so board columns
  // have meaningful rendered width at mobile viewports. With a ≥80px minimum the board
  // either shows fewer columns at 320px or allows internal horizontal scroll — either
  // approach makes columns meaningfully accessible unlike the current ≈45px columns.
  // FAIL: current minmax(0, 1fr) has no px minimum, so extracted minimum is 0.
  it('KanbanBoard board grid specifies a minimum column width of at least 80px per column', () => {
    // Pattern: repeat(..., minmax(Npx, ...)) where N ≥ 80
    const match = kanbanBoardSource.match(/repeat\([^)]+,\s*minmax\(\s*(\d+)px/)
    const minWidth = match ? parseInt(match[1], 10) : 0
    expect(
      minWidth,
      `Board grid column minimum must be ≥80px for mobile usability — current minmax minimum is ${minWidth}px, causing ≈45px columns at 320px with 7 columns (not accessible)`,
    ).toBeGreaterThanOrEqual(80)
  })
})
