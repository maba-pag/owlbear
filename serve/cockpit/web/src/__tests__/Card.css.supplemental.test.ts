/**
 * Supplemental Card.css regressions for text wrapping, base tokens, and drag state.
 * Card.css.test.ts covers signal selectors and selected/hover/focus states.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const CARD_CSS_PATH = resolve(__dirname, '..', 'components', 'Card.css')

/**
 * Extract the declaration block content for an exact CSS selector.
 * Returns null when the selector is not found.
 */
function getCSSBlock(css: string, selector: string): string | null {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`${escaped}\\s*\\{([^}]*)\\}`)
  const match = css.match(pattern)
  return match ? match[1] : null
}

// ─── AC-3: overflow-wrap and height constraint ────────────────────────────────

describe('card text overflow CSS', () => {
  it('.card block declares overflow-wrap: break-word (AC-3)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block).not.toBeNull()
    expect(block).toMatch(/overflow-wrap\s*:\s*break-word/)
  })

  it('.card block does not declare max-height — fixed height constraint removed per AC-3', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block).not.toBeNull()
    expect(block).not.toMatch(/max-height/)
  })
})

// ─── AC-1: base border uses agnostic PDS token, no legacy shadowing ──────────

describe('card base token CSS', () => {
  it('.card border-left references var(--p-color-contrast-medium) directly for theme-aware base (AC-1)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border-left\s*:[^;]*var\(--p-color-contrast-medium\)/)
  })

  it('.card border-left declaration specifies 4px width — falsifiable against 1px or 8px (AC-1)', () => {
    // Reviewer gap: previous test proved token reference but not the 4px width.
    // A border-left: 1px solid var(--p-color-contrast-medium) would have passed before.
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border-left\s*:\s*4px/)
  })

  it('.card block does not shadow --p-color-contrast-medium with a theme-light override (AC-1 dark mode)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block).not.toBeNull()
    expect(block).not.toMatch(/--p-color-contrast-medium\s*:\s*var\(--pds-theme-light-contrast-medium\)/)
  })

  it('.card block does not shadow --p-color-warning with a theme-light override (AC-1 dark mode)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block).not.toBeNull()
    expect(block).not.toMatch(/--p-color-warning\s*:\s*var\(--pds-theme-light-notification-warning\)/)
  })

  it('.card block does not shadow --p-color-error with a theme-light override (AC-1 dark mode)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '.card')
    expect(block).not.toBeNull()
    expect(block).not.toMatch(/--p-color-error\s*:\s*var\(--pds-theme-light-notification-error\)/)
  })
})

// ─── AC-4: Drag state CSS selector ────────────────────────────────────────────

describe('card drag-state CSS', () => {
  it('[data-dragging="true"] selector exists in Card.css (AC-4)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    expect(css).toMatch(/\[data-dragging="true"\]/)
  })

  it('[data-dragging="true"] selector applies opacity: 0.5 (AC-4)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-dragging="true"]')
    expect(block).not.toBeNull()
    expect(block).toMatch(/opacity\s*:\s*0\.5/)
  })
})
