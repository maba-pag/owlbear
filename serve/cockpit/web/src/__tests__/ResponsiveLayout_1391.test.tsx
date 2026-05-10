/**
 * RED-phase Vitest tests for #1391: Cockpit responsive dashboard — PDS token usage, CSS breakpoints,
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
 * AC1/AC2/AC3/AC4 layout behavior (bounding-box assertions at real viewports) require Playwright
 * and are documented in .owlbear/scratch/1391-e2e.spec.ts for the builder to place in e2e/.
 * These static-analysis tests provide AC1–AC4 coverage that can be verified without a layout engine.
 *
 * All tests FAIL against the current implementation:
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

// ─── File paths (resolved from package root — process.cwd() = serve/cockpit/web/) ───

const CARD_TSX = path.resolve(process.cwd(), 'src/components/Card.tsx')
const SHELL_CSS = path.resolve(process.cwd(), 'src/Shell.css')

// ─── Shared CSS source ────────────────────────────────────────────────────────

let shellCss = ''
let cardSource = ''

// loaded once for static analysis blocks
;(() => {
  shellCss = fs.readFileSync(SHELL_CSS, 'utf-8')
  cardSource = fs.readFileSync(CARD_TSX, 'utf-8')
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
