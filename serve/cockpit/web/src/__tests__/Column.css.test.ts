/**
 * Column CSS file-based verification tests — AC-1, AC-2, AC-3, AC-4
 *
 * Tests verify that Column.css (modified by builder #1547) contains:
 *   AC-1: .column base styles: background surface, border-radius, border, min-width 200px
 *   AC-2: .column flex layout; header flex-shrink: 0; .column-body flex + scroll
 *   AC-3: .column-empty centering preserved (regression guard from #1539)
 *   AC-4: .column[data-drag-over="true"] drop-target background
 *
 * Column.css exists but lacks the AC-1/AC-2 flex/AC-4 properties — those tests fail RED.
 * AC-3 regression guards currently pass (centering pre-exists from #1539); they guard
 * against the builder accidentally removing centering during Column.css expansion.
 *
 * Prerequisites:
 *   src/components/Column.css — modified by builder #1547
 *   PDS tokens from src/styles/tokens.css — defined by builder #1543
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const COLUMN_CSS_PATH = resolve(__dirname, '..', 'components', 'Column.css')

// ─── CSS block extraction helper ──────────────────────────────────────────────

/**
 * Extract the declaration block content for an exact CSS selector.
 * Returns null when the selector is not found.
 * Works for non-nested single-block CSS rules (sufficient for Column.css structure).
 */
function getCSSBlock(css: string, selector: string): string | null {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`${escaped}\\s*\\{([^}]*)\\}`)
  const match = css.match(pattern)
  return match ? match[1] : null
}

// ─── AC-1: .column base styling ───────────────────────────────────────────────

describe('TestFromAC_ColumnBaseStyling', () => {
  it('.column declares background: var(--p-color-surface)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column')
    expect(block).not.toBeNull()
    expect(block).toMatch(/background\s*:\s*var\(--p-color-surface\)/)
  })

  it('.column declares border-radius: var(--p-radius-md)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border-radius\s*:\s*var\(--p-radius-md\)/)
  })

  it('.column declares border: 1px solid var(--p-color-contrast-low)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border\s*:\s*1px\s+solid\s+var\(--p-color-contrast-low\)/)
  })

  it('.column declares min-width: 200px (overrides skeleton min-width: 0)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column')
    expect(block).not.toBeNull()
    expect(block).toMatch(/min-width\s*:\s*200px/)
  })
})

// ─── AC-2: Flex layout ────────────────────────────────────────────────────────

describe('TestFromAC_ColumnFlexLayout', () => {
  it('.column declares display: flex to enable fixed-header scroll pattern', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column')
    expect(block).not.toBeNull()
    expect(block).toMatch(/display\s*:\s*flex/)
  })

  it('.column declares flex-direction: column for vertical stacking', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column')
    expect(block).not.toBeNull()
    expect(block).toMatch(/flex-direction\s*:\s*column/)
  })

  it('header within column context declares flex-shrink: 0 (fixed header)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    // Accept .column header, header, .column > header — any form that targets the column header.
    expect(css).toMatch(/header[^{]*\{[^}]*flex-shrink\s*:\s*0/)
  })

  it('.column-body declares flex: 1 to fill remaining column height', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-body')
    expect(block).not.toBeNull()
    // flex: 1 may be written as shorthand (flex: 1) or expanded; match the shorthand prefix.
    expect(block).toMatch(/flex\s*:\s*1/)
  })

  it('.column-body declares min-height: 0 to activate nested scroll within flex parent', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-body')
    expect(block).not.toBeNull()
    expect(block).toMatch(/min-height\s*:\s*0/)
  })

  it('.column-body has both flex: 1 and overflow-y: auto coexisting (scroll + fill contract)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-body')
    expect(block).not.toBeNull()
    // Both must be present in the same block after the builder adds flex layout.
    expect(block).toMatch(/overflow-y\s*:\s*auto/)
    expect(block).toMatch(/flex\s*:\s*1/)
  })
})

// ─── AC-3: Empty state centering preserved ────────────────────────────────────

describe('TestFromAC_ColumnEmptyState', () => {
  // These are regression guards — centering was established by #1539 and must survive
  // the builder's Column.css expansion in #1547.

  it('.column-empty preserves display: flex for centering layout (regression guard from #1539)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-empty')
    expect(block).not.toBeNull()
    expect(block).toMatch(/display\s*:\s*flex/)
  })

  it('.column-empty preserves align-items: center for vertical centering (regression guard from #1539)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-empty')
    expect(block).not.toBeNull()
    expect(block).toMatch(/align-items\s*:\s*center/)
  })

  it('.column-empty preserves justify-content: center for horizontal centering (regression guard from #1539)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-empty')
    expect(block).not.toBeNull()
    expect(block).toMatch(/justify-content\s*:\s*center/)
  })
})

// ─── AC-4: Drag-over drop-target highlight ────────────────────────────────────

describe('TestFromAC_ColumnDragOver', () => {
  it('.column[data-drag-over="true"] declares background: var(--p-color-frosted)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column[data-drag-over="true"]')
    expect(block).not.toBeNull()
    expect(block).toMatch(/background\s*:\s*var\(--p-color-frosted\)/)
  })
})

// ─── AC-4 (spacing): Header / body / empty-state spacing tokens ───────────────
// Retry #1575: reviewer gap — AC-4 proof did not assert spacing token usage.
// A regression from var(--pds-spacing-*) to raw pixel values must cause these to fail.

describe('TestFromAC_ColumnSpacingTokens', () => {
  it('.column header padding uses PDS spacing token var(--p-spacing-static-sm) on both axes', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column header')
    expect(block).not.toBeNull()
    expect(block).toMatch(/padding\s*:\s*var\(--p-spacing-static-sm\)\s+var\(--p-spacing-static-sm\)/)
  })

  it('.column-body padding uses PDS spacing token var(--p-spacing-static-xs)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-body')
    expect(block).not.toBeNull()
    expect(block).toMatch(/padding\s*:\s*var\(--p-spacing-static-xs\)/)
  })

  it('.column-body gap uses PDS spacing token var(--p-spacing-static-xs)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-body')
    expect(block).not.toBeNull()
    expect(block).toMatch(/gap\s*:\s*var\(--p-spacing-static-xs\)/)
  })

  it('.column-empty padding uses PDS spacing token var(--p-spacing-static-md)', () => {
    const css = readFileSync(COLUMN_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.column-empty')
    expect(block).not.toBeNull()
    expect(block).toMatch(/padding\s*:\s*var\(--p-spacing-static-md\)/)
  })
})
