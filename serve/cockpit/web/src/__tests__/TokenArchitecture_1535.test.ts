import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const TOKENS_CSS_PATH = resolve(__dirname, '..', 'tokens.css')

const EXPECTED_COLOR_TOKENS = [
  '--pds-primary',
  '--pds-background-base',
  '--pds-background-surface',
  '--pds-background-shading',
  '--pds-contrast-low',
  '--pds-contrast-medium',
  '--pds-contrast-high',
  '--pds-notification-success',
  '--pds-notification-success-soft',
  '--pds-notification-warning',
  '--pds-notification-warning-soft',
  '--pds-notification-error',
  '--pds-notification-error-soft',
  '--pds-notification-info',
  '--pds-notification-info-soft',
  '--pds-state-hover',
  '--pds-state-active',
  '--pds-state-focus',
  '--pds-state-disabled',
] as const

const EXPECTED_NON_COLOR_TOKENS = [
  '--pds-shadow-sm',
  '--pds-shadow-md',
  '--pds-shadow-lg',
  '--pds-radius-sm',
  '--pds-radius-md',
  '--pds-radius-lg',
  '--pds-radius-xl',
  '--pds-spacing-xs',
  '--pds-spacing-sm',
  '--pds-spacing-md',
  '--pds-spacing-lg',
  '--pds-spacing-xl',
  '--pds-spacing-2xl',
] as const

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function parseDeclarations(block: string): Map<string, string> {
  const result = new Map<string, string>()
  const declarationPattern = /(--[a-z0-9-]+)\s*:\s*([^;]+);/gi

  for (const match of block.matchAll(declarationPattern)) {
    const [, tokenName, tokenValue] = match
    result.set(tokenName.trim(), tokenValue.trim())
  }

  return result
}

function extractSelectorBlock(css: string, selector: string): string {
  const selectorPattern = new RegExp(`${escapeRegExp(selector)}\\s*\\{([\\s\\S]*?)\\}`, 'm')
  const match = css.match(selectorPattern)
  expect(match, `Missing selector block: ${selector}`).not.toBeNull()
  return match?.[1] ?? ''
}

function extractAtRuleBody(css: string, atRulePrefix: string): string {
  const startIndex = css.indexOf(atRulePrefix)
  expect(startIndex, `Missing at-rule: ${atRulePrefix}`).toBeGreaterThanOrEqual(0)

  const openBraceIndex = css.indexOf('{', startIndex)
  expect(openBraceIndex, `Missing opening brace for: ${atRulePrefix}`).toBeGreaterThanOrEqual(0)

  let depth = 0
  for (let index = openBraceIndex; index < css.length; index++) {
    const char = css[index]
    if (char === '{') {
      depth += 1
    } else if (char === '}') {
      depth -= 1
      if (depth === 0) {
        return css.slice(openBraceIndex + 1, index)
      }
    }
  }

  throw new Error(`Unclosed at-rule block: ${atRulePrefix}`)
}

describe('TestFromAC_TokenArchitecture_1535', () => {
  it('AC-1: :root declares exactly the 19 agnostic --pds-* color tokens and no --pds-theme-light-* names', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const rootBlock = extractSelectorBlock(css, ':root')
    const rootDeclarations = parseDeclarations(rootBlock)

    const actualColorTokens = [...rootDeclarations.keys()].filter((token) =>
      EXPECTED_COLOR_TOKENS.includes(token as (typeof EXPECTED_COLOR_TOKENS)[number]),
    )

    expect(actualColorTokens.sort()).toEqual([...EXPECTED_COLOR_TOKENS].sort())

    const legacyNames = [...rootDeclarations.keys()].filter((token) => token.startsWith('--pds-theme-light-'))
    expect(legacyNames).toEqual([])
  })

  it('AC-2: [data-theme="dark"] overrides all 19 color tokens with non-empty values different from :root values', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const rootDeclarations = parseDeclarations(extractSelectorBlock(css, ':root'))
    const darkDeclarations = parseDeclarations(extractSelectorBlock(css, '[data-theme="dark"]'))

    for (const token of EXPECTED_COLOR_TOKENS) {
      const rootValue = rootDeclarations.get(token)
      const darkValue = darkDeclarations.get(token)

      expect(rootValue, `Missing token in :root: ${token}`).toBeTruthy()
      expect(darkValue, `Missing token in [data-theme="dark"]: ${token}`).toBeTruthy()
      expect(darkValue?.trim().length, `Dark token is empty: ${token}`).toBeGreaterThan(0)
      expect(darkValue, `Dark token must differ from :root token: ${token}`).not.toBe(rootValue)
    }
  })

  it('AC-2: @media (prefers-color-scheme: dark) fallback declares the same 19 color token overrides', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const mediaBlock = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    const mediaDeclarations = parseDeclarations(mediaBlock)

    expect([...mediaDeclarations.keys()].filter((token) => EXPECTED_COLOR_TOKENS.includes(token as (typeof EXPECTED_COLOR_TOKENS)[number])).sort()).toEqual(
      [...EXPECTED_COLOR_TOKENS].sort(),
    )

    for (const token of EXPECTED_COLOR_TOKENS) {
      const value = mediaDeclarations.get(token)
      expect(value, `Missing fallback token in dark media block: ${token}`).toBeTruthy()
      expect(value?.trim().length, `Fallback token is empty in dark media block: ${token}`).toBeGreaterThan(0)
    }
  })

  it('AC-3: :root declares 13 non-color tokens (shadow/radius/spacing) with non-empty values', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const rootDeclarations = parseDeclarations(extractSelectorBlock(css, ':root'))

    expect(
      [...rootDeclarations.keys()].filter((token) =>
        EXPECTED_NON_COLOR_TOKENS.includes(token as (typeof EXPECTED_NON_COLOR_TOKENS)[number]),
      ).sort(),
    ).toEqual([...EXPECTED_NON_COLOR_TOKENS].sort())

    for (const token of EXPECTED_NON_COLOR_TOKENS) {
      const value = rootDeclarations.get(token)
      expect(value, `Missing non-color token in :root: ${token}`).toBeTruthy()
      expect(value?.trim().length, `Non-color token is empty in :root: ${token}`).toBeGreaterThan(0)
    }
  })
})
