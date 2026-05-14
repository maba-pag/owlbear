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

// Per PDS v4: these two tokens have identical values in both light and dark themes.
// The builder must NOT assert they differ; they are intentionally the same.
const PDS_IDENTICAL_IN_ALL_THEMES: ReadonlyArray<string> = [
  '--pds-state-focus',
  '--pds-background-shading',
]

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

describe('TestFromAC_TokenArchitecture_1543', () => {
  it('AC-2 happy: @media (prefers-color-scheme: dark) block uses :root:not([data-theme]) as inner selector', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const mediaBody = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    expect(
      /:root:not\(\[data-theme\]\)/.test(mediaBody),
      'Expected :root:not([data-theme]) selector inside @media (prefers-color-scheme: dark) block — bare :root would incorrectly override explicit data-theme attributes',
    ).toBe(true)
  })

  it('AC-2 happy: :root:not([data-theme]) block inside media query declares all 19 color tokens', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const mediaBody = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    const innerBlock = extractSelectorBlock(mediaBody, ':root:not([data-theme])')
    const declarations = parseDeclarations(innerBlock)
    const actualColorTokens = [...declarations.keys()].filter((token) => token.startsWith('--pds-'))
    expect(actualColorTokens.sort()).toEqual([...EXPECTED_COLOR_TOKENS].sort())
  })

  it('AC-2 boundary: :root:not([data-theme]) block declares exactly 19 tokens — no extras, no legacy names', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const mediaBody = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    const innerBlock = extractSelectorBlock(mediaBody, ':root:not([data-theme])')
    const declarations = parseDeclarations(innerBlock)
    const legacyNames = [...declarations.keys()].filter((token) => token.startsWith('--pds-theme-'))
    expect(legacyNames, 'No legacy --pds-theme-* names in media fallback block').toEqual([])
    expect([...declarations.keys()]).toHaveLength(19)
  })

  it('AC-2 happy: media fallback values match [data-theme="dark"] overrides for the 17 non-identical tokens', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const darkDeclarations = parseDeclarations(extractSelectorBlock(css, '[data-theme="dark"]'))
    const mediaBody = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    const mediaDeclarations = parseDeclarations(extractSelectorBlock(mediaBody, ':root:not([data-theme])'))
    const differingTokens = EXPECTED_COLOR_TOKENS.filter(
      (token) => !PDS_IDENTICAL_IN_ALL_THEMES.includes(token),
    )
    for (const token of differingTokens) {
      const darkValue = darkDeclarations.get(token)
      const mediaValue = mediaDeclarations.get(token)
      expect(darkValue, `Missing token in [data-theme="dark"]: ${token}`).toBeTruthy()
      expect(mediaValue, `Missing token in media fallback: ${token}`).toBeTruthy()
      expect(mediaValue, `Media fallback value must equal [data-theme="dark"] value for ${token}`).toBe(darkValue)
    }
  })

  it('AC-2 edge: PDS-identical tokens (--pds-state-focus, --pds-background-shading) present in media fallback with non-empty values', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const mediaBody = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    const mediaDeclarations = parseDeclarations(extractSelectorBlock(mediaBody, ':root:not([data-theme])'))
    for (const token of PDS_IDENTICAL_IN_ALL_THEMES) {
      const value = mediaDeclarations.get(token)
      expect(value, `PDS-identical token must be present in media fallback: ${token}`).toBeTruthy()
      expect(
        value?.trim().length,
        `PDS-identical token must have non-empty value in media fallback: ${token}`,
      ).toBeGreaterThan(0)
    }
  })

  it('AC-2 edge: PDS-identical tokens in media fallback equal [data-theme="dark"] values', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const darkDeclarations = parseDeclarations(extractSelectorBlock(css, '[data-theme="dark"]'))
    const mediaBody = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    const mediaDeclarations = parseDeclarations(extractSelectorBlock(mediaBody, ':root:not([data-theme])'))
    for (const token of PDS_IDENTICAL_IN_ALL_THEMES) {
      const darkValue = darkDeclarations.get(token)
      const mediaValue = mediaDeclarations.get(token)
      expect(darkValue, `Missing token in [data-theme="dark"]: ${token}`).toBeTruthy()
      expect(mediaValue, `Missing token in media fallback: ${token}`).toBeTruthy()
      expect(mediaValue, `Media fallback value for ${token} must equal [data-theme="dark"] value`).toBe(darkValue)
    }
  })

  it('AC-2 error: media fallback block contains no legacy --pds-theme-* token names', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const mediaBody = extractAtRuleBody(css, '@media (prefers-color-scheme: dark)')
    const allDeclarations = parseDeclarations(mediaBody)
    const legacyNames = [...allDeclarations.keys()].filter((token) => token.startsWith('--pds-theme-'))
    expect(legacyNames, 'Media fallback block must not contain legacy --pds-theme-* names').toEqual([])
  })

  it('AC-3 boundary: non-color tokens (shadow/radius/spacing) are absent from [data-theme="dark"] — they are theme-independent', () => {
    const css = readFileSync(TOKENS_CSS_PATH, 'utf-8')
    const darkDeclarations = parseDeclarations(extractSelectorBlock(css, '[data-theme="dark"]'))
    const nonColorInDark = EXPECTED_NON_COLOR_TOKENS.filter((token) => darkDeclarations.has(token))
    expect(
      nonColorInDark,
      'Non-color tokens (shadow/radius/spacing) must not appear in [data-theme="dark"]: they are theme-independent values',
    ).toEqual([])
  })
})
