/**
 * Card CSS file-based verification tests — AC-2, AC-3, AC-4
 *
 * Tests verify that Card.css (created by builder #1546) contains:
 *   AC-2: [data-signal="X"] selectors with correct left-border-color tokens
 *   AC-3: [data-selected] selector with box-shadow or outline using PDS success token
 *   AC-4: :hover and :focus-visible selectors with PDS state tokens
 *
 * Card.css does not exist yet — all tests fail RED with ENOENT until #1546 creates it.
 * File-based parsing follows the PDSHexScan_1395 and token-architecture test patterns.
 *
 * Signal → token mapping (brief D10/D14):
 *   dr-pending → orange  → var(--pds-notification-warning)
 *   blocked    → red     → var(--pds-notification-error)
 *   claimed    → purple  → var(--pds-signal-claimed)  [custom token, no PDS purple]
 *   deps-unmet → grey    → var(--pds-contrast-medium)
 *   ready      → theme-aware → no explicit border-left-color override
 *
 * Prerequisites:
 *   src/components/Card.css — created by builder #1546
 *   --pds-signal-claimed custom token — defined by builder #1543 or #1546
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Card.css is the implementation deliverable for builder task #1546.
// readFileSync throws ENOENT until the file exists — all tests fail RED.
const CARD_CSS_PATH = resolve(__dirname, '..', 'components', 'Card.css')

// ─── CSS block extraction helper ──────────────────────────────────────────────

/**
 * Extract the declaration block content for an exact CSS selector.
 * Works for non-nested single-block CSS rules (sufficient for Card.css structure).
 * Returns null when the selector is not found.
 */
function getCSSBlock(css: string, selector: string): string | null {
  // Escape all regex metacharacters in the selector string.
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`${escaped}\\s*\\{([^}]*)\\}`)
  const match = css.match(pattern)
  return match ? match[1] : null
}

// ─── AC-2: Signal selectors with border-left-color tokens ────────────────────

describe('TestFromAC_CardCSSBorderSignal', () => {
  it('[data-signal="dr-pending"] declares border-left-color: var(--pds-notification-warning) (orange)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="dr-pending"]')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-notification-warning\)/)
  })

  it('[data-signal="blocked"] declares border-left-color: var(--pds-notification-error) (red)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="blocked"]')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-notification-error\)/)
  })

  it('[data-signal="claimed"] declares border-left-color: var(--pds-signal-claimed) (custom purple token)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="claimed"]')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-signal-claimed\)/)
  })

  it('[data-signal="deps-unmet"] declares border-left-color: var(--pds-contrast-medium) (grey)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="deps-unmet"]')
    expect(block).not.toBeNull()
    expect(block).toMatch(/border-left-color\s*:\s*var\(--pds-contrast-medium\)/)
  })

  it('[data-signal="ready"] has no explicit border-left-color — theme-aware default via inheritance', () => {
    // Card.css must exist (readFileSync throws ENOENT if missing → RED)
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = getCSSBlock(css, '[data-signal="ready"]')
    // If a [data-signal="ready"] block exists, it must NOT override border-left-color.
    // If the block is absent entirely, inheritance applies — also valid.
    if (block !== null) {
      expect(block).not.toMatch(/border-left-color/)
    }
  })
})

// ─── AC-3: Selected state styling ────────────────────────────────────────────

describe('TestFromAC_CardCSSSelectedState', () => {
  it('[data-selected] or [data-selected="true"] selector exists in Card.css', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    expect(css).toMatch(/\[data-selected/)
  })

  it('[data-selected] selector declares box-shadow or outline referencing var(--pds-notification-success)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    // Accept either attribute form the builder may choose.
    const block =
      getCSSBlock(css, '[data-selected]') ??
      getCSSBlock(css, '[data-selected="true"]')
    expect(block).not.toBeNull()
    // Must declare box-shadow or outline (brief: "box-shadow or outline, green from PDS success").
    const hasShadow = /box-shadow/.test(block!)
    const hasOutline = /outline/.test(block!)
    expect(hasShadow || hasOutline).toBe(true)
    // Must reference PDS success token (green) — distinct from the left-border signal color.
    expect(block).toMatch(/var\(--pds-notification-success\)/)
  })
})

// ─── AC-4: Hover and focus-visible pseudo-selector styling ───────────────────

describe('TestFromAC_CardCSSHoverFocus', () => {
  it(':hover selector in Card.css declares background property with var(--pds-state-hover)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    // Match any :hover block that sets background referencing the state-hover token.
    // [^}]* matches any characters including newlines until the closing brace.
    expect(css).toMatch(/:hover\s*\{[^}]*background[^}]*var\(--pds-state-hover\)[^}]*\}/)
  })

  it(':focus-visible selector in Card.css declares outline property with var(--pds-state-focus)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    // Match any :focus-visible block that sets outline referencing the state-focus token.
    expect(css).toMatch(/:focus-visible\s*\{[^}]*outline[^}]*var\(--pds-state-focus\)[^}]*\}/)
  })
})
