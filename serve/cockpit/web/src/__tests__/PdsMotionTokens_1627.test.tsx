import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const SHELL_CSS_PATH = resolve(__dirname, '..', 'Shell.css')
const CARD_CSS_PATH = resolve(__dirname, '..', 'components', 'Card.css')

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Extract the content inside a CSS selector block.
 * Uses a negative lookahead to avoid partial-class matches.
 */
function extractSelectorBlock(css: string, selector: string): string {
  const escaped = escapeRegExp(selector)
  const pattern = new RegExp(
    `(?:^|[\\n\\r])${escaped}(?![a-zA-Z0-9_\\-\\[])\\s*\\{([\\s\\S]*?)\\}`,
  )
  const match = css.match(pattern)
  expect(match, `Missing CSS selector block for: ${selector}`).not.toBeNull()
  return match?.[1] ?? ''
}

describe('TestFromAC_PdsMotionTokens_1627', () => {
  // AC-1: Shell.css .icon-button — background and border-color transitions use PDS tokens

  it('AC-1 icon-button-duration: Shell.css .icon-button transition uses var(--p-duration-sm)', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.icon-button')
    expect(
      /transition\s*:.*var\(--p-duration-sm\)/.test(block),
      'Expected .icon-button transition to use var(--p-duration-sm) — currently hardcoded 120ms',
    ).toBe(true)
  })

  it('AC-1 icon-button-easing: Shell.css .icon-button transition uses var(--p-ease-in-out)', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.icon-button')
    expect(
      /transition\s*:.*var\(--p-ease-in-out\)/.test(block),
      'Expected .icon-button transition to use var(--p-ease-in-out) — currently hardcoded ease',
    ).toBe(true)
  })

  it('AC-1 icon-button-no-hardcoded: Shell.css .icon-button transition has no hardcoded millisecond duration', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.icon-button')
    expect(
      /transition\s*:.*\d+ms/.test(block),
      'Expected .icon-button transition to have no hardcoded ms value — currently uses 120ms',
    ).toBe(false)
  })

  // AC-1: Card.css .card — box-shadow transition uses PDS tokens

  it('AC-1 card-duration: Card.css .card transition uses var(--p-duration-sm)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.card')
    expect(
      /transition\s*:.*var\(--p-duration-sm\)/.test(block),
      'Expected .card transition to use var(--p-duration-sm) — currently hardcoded 120ms',
    ).toBe(true)
  })

  it('AC-1 card-easing: Card.css .card transition uses var(--p-ease-in-out)', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.card')
    expect(
      /transition\s*:.*var\(--p-ease-in-out\)/.test(block),
      'Expected .card transition to use var(--p-ease-in-out) — currently hardcoded ease',
    ).toBe(true)
  })

  it('AC-1 card-no-hardcoded: Card.css .card transition has no hardcoded millisecond duration', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.card')
    expect(
      /transition\s*:.*\d+ms/.test(block),
      'Expected .card transition to have no hardcoded ms value — currently uses 120ms',
    ).toBe(false)
  })

  // AC-1 property-level specificity: assert correct property names are in the transition declarations
  // (not just token presence — a wrong property list with the same tokens must still fail)

  it('AC-1 icon-button-background-property: Shell.css .icon-button transition names background with PDS duration and easing', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.icon-button')
    const transitionMatch = block.match(/transition\s*:([^;]+)/)
    expect(transitionMatch, 'No transition declaration found in .icon-button').not.toBeNull()
    const subDeclarations = transitionMatch![1].split(',').map((s) => s.trim())
    const backgroundSub = subDeclarations.find((s) => /^background\s/.test(s))
    expect(backgroundSub, '.icon-button transition does not name background as a transitioned property').toBeDefined()
    expect(backgroundSub).toMatch(/var\(--p-duration-sm\)/)
    expect(backgroundSub).toMatch(/var\(--p-ease-in-out\)/)
  })

  it('AC-1 icon-button-border-color-property: Shell.css .icon-button transition names border-color with PDS duration and easing', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.icon-button')
    const transitionMatch = block.match(/transition\s*:([^;]+)/)
    expect(transitionMatch, 'No transition declaration found in .icon-button').not.toBeNull()
    const subDeclarations = transitionMatch![1].split(',').map((s) => s.trim())
    const borderColorSub = subDeclarations.find((s) => /^border-color\s/.test(s))
    expect(borderColorSub, '.icon-button transition does not name border-color as a transitioned property').toBeDefined()
    expect(borderColorSub).toMatch(/var\(--p-duration-sm\)/)
    expect(borderColorSub).toMatch(/var\(--p-ease-in-out\)/)
  })

  it('AC-1 card-box-shadow-property: Card.css .card transition names box-shadow with PDS duration and easing', () => {
    const css = readFileSync(CARD_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.card')
    const transitionMatch = block.match(/transition\s*:([^;]+)/)
    expect(transitionMatch, 'No transition declaration found in .card').not.toBeNull()
    const subDeclarations = transitionMatch![1].split(',').map((s) => s.trim())
    const boxShadowSub = subDeclarations.find((s) => /^box-shadow\s/.test(s))
    expect(boxShadowSub, '.card transition does not name box-shadow as a transitioned property').toBeDefined()
    expect(boxShadowSub).toMatch(/var\(--p-duration-sm\)/)
    expect(boxShadowSub).toMatch(/var\(--p-ease-in-out\)/)
  })

  // AC-1 / AC-3: Shell.css .shell — base block grid-template-columns transition uses PDS tokens
  // (property-level: must name grid-template-columns, not just have token strings somewhere)

  it('AC-1 shell-grid-template-columns-property: Shell.css .shell transition names grid-template-columns with PDS duration and easing', () => {
    const css = readFileSync(SHELL_CSS_PATH, 'utf-8')
    const block = extractSelectorBlock(css, '.shell')
    const transitionMatch = block.match(/transition\s*:([^;]+)/)
    expect(transitionMatch, 'No transition declaration found in base .shell block').not.toBeNull()
    const subDeclarations = transitionMatch![1].split(',').map((s) => s.trim())
    const gridSub = subDeclarations.find((s) => /^grid-template-columns\s/.test(s))
    expect(gridSub, '.shell transition does not name grid-template-columns as a transitioned property').toBeDefined()
    expect(gridSub).toMatch(/var\(--p-duration-sm\)/)
    expect(gridSub).toMatch(/var\(--p-ease-in-out\)/)
  })
})
