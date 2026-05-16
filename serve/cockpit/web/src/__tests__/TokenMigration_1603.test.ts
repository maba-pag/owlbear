/**
 * RED phase tests for #1603: Atomic token migration — delete tokens.css + migrate references
 *
 * AC-1: grep -r '--pds-' serve/cockpit/web/src/ returns zero matches (CSS and TSX)
 * AC-2: tokens.css deleted; custom-tokens.css declares exactly --custom-signal-claimed
 *       (the sole custom-keep token) and no other custom properties
 * AC-3: Manual dark-mode override blocks ([data-theme="dark"] and
 *       @media prefers-color-scheme) removed from authored CSS
 * AC-4: Tests formerly asserting --pds-* names updated to assert --p-* equivalents
 *       or deleted when their assertion target (tokens.css structure) no longer exists
 *
 * All tests FAIL in RED phase because:
 *   AC-1 — source CSS/TSX files currently contain --pds-* references
 *   AC-2 — tokens.css currently exists; custom-tokens.css does not exist
 *   AC-3 — tokens.css currently contains [data-theme="dark"] and
 *           @media (prefers-color-scheme: dark) blocks
 *   AC-4 — TokenArchitecture test files still exist; key assertions still name --pds-* tokens
 */
import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { dirname, extname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SRC_DIR = resolve(__dirname, '..')
const TESTS_DIR = resolve(__dirname)

// ─── File collection helpers ───────────────────────────────────────────────────

function collectSourceFiles(dir: string, extensions: string[], excludeDirs: Set<string>): string[] {
  const result: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = join(dir, entry.name)
    if (entry.isDirectory()) {
      if (!excludeDirs.has(entry.name)) {
        result.push(...collectSourceFiles(fullPath, extensions, excludeDirs))
      }
    } else if (entry.isFile() && extensions.includes(extname(entry.name))) {
      result.push(fullPath)
    }
  }
  return result
}

function findPdsViolations(files: string[]): string[] {
  const violations: string[] = []
  for (const filePath of files) {
    const content = readFileSync(filePath, 'utf-8')
    const lines = content.split('\n')
    for (let i = 0; i < lines.length; i++) {
      if (/--pds-/.test(lines[i])) {
        const rel = filePath.replace(SRC_DIR + '/', 'src/')
        violations.push(`${rel}:${i + 1}: ${lines[i].trim()}`)
      }
    }
  }
  return violations
}

// Directories excluded from production-source scans
const EXCLUDE_FROM_SRC_SCAN = new Set(['__tests__', 'node_modules', 'dist', 'build'])

// ─── AC-1: Zero --pds-* references in source CSS and TSX/TS component files ──

describe('TestFromAC_NoPdsTokensInSource', () => {
  it('AC-1: all authored CSS files in src/ contain zero --pds-* references after migration', () => {
    const cssFiles = collectSourceFiles(SRC_DIR, ['.css'], EXCLUDE_FROM_SRC_SCAN)
    expect(cssFiles.length, 'src/ must contain CSS files to scan').toBeGreaterThan(0)
    const violations = findPdsViolations(cssFiles)
    expect(
      violations,
      `--pds-* references must be zero in CSS after migration:\n${violations.join('\n')}`,
    ).toHaveLength(0)
  })

  it('AC-1: all authored TSX/TS component files in src/ contain zero --pds-* references after migration', () => {
    const tsxFiles = collectSourceFiles(SRC_DIR, ['.tsx', '.ts'], EXCLUDE_FROM_SRC_SCAN)
    expect(tsxFiles.length, 'src/ must contain TSX/TS files to scan').toBeGreaterThan(0)
    const violations = findPdsViolations(tsxFiles)
    expect(
      violations,
      `--pds-* references must be zero in TSX/TS after migration:\n${violations.join('\n')}`,
    ).toHaveLength(0)
  })
})

// ─── AC-2: tokens.css deleted; custom-tokens.css with exactly --custom-signal-claimed ──

describe('TestFromAC_TokenFileMigration', () => {
  const TOKENS_CSS_PATH = resolve(SRC_DIR, 'tokens.css')
  const CUSTOM_TOKENS_CSS_PATH = resolve(SRC_DIR, 'custom-tokens.css')

  it('AC-2: tokens.css is deleted from src/ (file must not exist)', () => {
    expect(
      existsSync(TOKENS_CSS_PATH),
      `tokens.css must be deleted but was found at ${TOKENS_CSS_PATH}`,
    ).toBe(false)
  })

  it('AC-2: custom-tokens.css exists in src/ (created by builder)', () => {
    expect(
      existsSync(CUSTOM_TOKENS_CSS_PATH),
      `custom-tokens.css must be created at ${CUSTOM_TOKENS_CSS_PATH}`,
    ).toBe(true)
  })

  it('AC-2: custom-tokens.css declares the --custom-signal-claimed property', () => {
    expect(existsSync(CUSTOM_TOKENS_CSS_PATH), 'custom-tokens.css must exist').toBe(true)
    const css = readFileSync(CUSTOM_TOKENS_CSS_PATH, 'utf-8')
    expect(
      css,
      'custom-tokens.css must declare --custom-signal-claimed (the sole custom-keep token)',
    ).toMatch(/--custom-signal-claimed\s*:/)
  })

  it('AC-2: custom-tokens.css declares exactly one custom property (no stray --* declarations)', () => {
    expect(existsSync(CUSTOM_TOKENS_CSS_PATH), 'custom-tokens.css must exist').toBe(true)
    const css = readFileSync(CUSTOM_TOKENS_CSS_PATH, 'utf-8')
    const cssNoComments = css.replace(/\/\*[\s\S]*?\*\//g, '')
    const declarations = [...cssNoComments.matchAll(/--[a-z][a-z0-9-]*\s*:/g)]
    expect(
      declarations.length,
      `custom-tokens.css must declare exactly 1 custom property, found ${declarations.length}: ` +
        declarations.map((m) => m[0].replace(':', '')).join(', '),
    ).toBe(1)
  })

  it('AC-2: custom-tokens.css contains no --pds-* declarations (old namespace fully replaced)', () => {
    expect(existsSync(CUSTOM_TOKENS_CSS_PATH), 'custom-tokens.css must exist').toBe(true)
    const css = readFileSync(CUSTOM_TOKENS_CSS_PATH, 'utf-8')
    expect(
      css,
      'custom-tokens.css must not declare any --pds-* properties — use --custom-* namespace only',
    ).not.toMatch(/--pds-[a-z]/)
  })
})

// ─── AC-3: Dark-mode override blocks removed from all authored CSS files ──────

describe('TestFromAC_DarkModeOverridesRemoved', () => {
  it('AC-3: no authored CSS file in src/ contains a [data-theme="dark"] selector block', () => {
    const cssFiles = collectSourceFiles(SRC_DIR, ['.css'], EXCLUDE_FROM_SRC_SCAN)
    const violations: string[] = []
    for (const filePath of cssFiles) {
      const content = readFileSync(filePath, 'utf-8')
      if (/\[data-theme\s*=\s*["']dark["']\]/.test(content)) {
        violations.push(filePath.replace(SRC_DIR + '/', 'src/'))
      }
    }
    expect(
      violations,
      `[data-theme="dark"] override blocks must be removed from authored CSS:\n${violations.join('\n')}`,
    ).toHaveLength(0)
  })

  it('AC-3: no authored CSS file in src/ contains a @media (prefers-color-scheme) block', () => {
    const cssFiles = collectSourceFiles(SRC_DIR, ['.css'], EXCLUDE_FROM_SRC_SCAN)
    const violations: string[] = []
    for (const filePath of cssFiles) {
      const content = readFileSync(filePath, 'utf-8')
      if (/@media\s*\(\s*prefers-color-scheme/.test(content)) {
        violations.push(filePath.replace(SRC_DIR + '/', 'src/'))
      }
    }
    expect(
      violations,
      '@media prefers-color-scheme blocks must be removed — PDS handles dark via .scheme-dark:\n' +
        violations.join('\n'),
    ).toHaveLength(0)
  })
})

// ─── AC-4: Retired test files deleted ─────────────────────────────────────────

describe('TestFromAC_LegacyTestFilesRetired', () => {
  it('AC-4: TokenArchitecture_1535.test.ts is deleted (assertion target tokens.css no longer exists)', () => {
    const path = resolve(TESTS_DIR, 'TokenArchitecture_1535.test.ts')
    expect(
      existsSync(path),
      `TokenArchitecture_1535.test.ts must be deleted — it asserts tokens.css structure that no longer exists`,
    ).toBe(false)
  })

  it('AC-4: TokenArchitecture_1543.test.ts is deleted (assertion target tokens.css no longer exists)', () => {
    const path = resolve(TESTS_DIR, 'TokenArchitecture_1543.test.ts')
    expect(
      existsSync(path),
      `TokenArchitecture_1543.test.ts must be deleted — it asserts tokens.css structure that no longer exists`,
    ).toBe(false)
  })
})

// ─── AC-4: Updated test files assert --p-* equivalents ────────────────────────

describe('TestFromAC_LegacyTestFilesUpdated', () => {
  it('AC-4: CardCSS_1546.test.ts asserts the migrated --p-color-contrast-medium token (not retired --pds-contrast-medium)', () => {
    const path = resolve(TESTS_DIR, 'CardCSS_1546.test.ts')
    expect(existsSync(path), 'CardCSS_1546.test.ts must exist (updated, not retired)').toBe(true)
    const source = readFileSync(path, 'utf-8')
    expect(
      source,
      'CardCSS_1546.test.ts must reference --p-color-contrast-medium (PDS v4 replacement)',
    ).toMatch(/--p-color-contrast-medium/)
  })

  it('AC-4: CardCSS_1546.test.ts no longer asserts var(--pds-contrast-medium) as a declaration value', () => {
    const path = resolve(TESTS_DIR, 'CardCSS_1546.test.ts')
    expect(existsSync(path)).toBe(true)
    const source = readFileSync(path, 'utf-8')
    expect(
      source,
      'CardCSS_1546.test.ts must not retain --pds-contrast-medium assertions after migration',
    ).not.toMatch(/var\(--pds-contrast-medium\)/)
  })

  it('AC-4: BoardVisualDesign.test.tsx no longer asserts [data-theme="dark"] block in tokens.css (file deleted)', () => {
    const path = resolve(TESTS_DIR, 'BoardVisualDesign.test.tsx')
    expect(existsSync(path), 'BoardVisualDesign.test.tsx must exist (updated, not retired)').toBe(true)
    const source = readFileSync(path, 'utf-8')
    // After migration: tokens.css is deleted; the DarkThemeTokenCoverage tests that read it must be removed.
    // The assertion '[data-theme="dark"] block overrides all :root color tokens' is no longer applicable.
    expect(
      source,
      'BoardVisualDesign.test.tsx must not assert [data-theme="dark"] override block — tokens.css is deleted',
    ).not.toMatch(/\[data-theme\s*=\s*["']dark["']\]\s*block/)
  })

  it('AC-4: BoardVisualDesign.test.tsx card signal border uses --custom-signal-claimed (not retired --pds-signal-claimed)', () => {
    const path = resolve(TESTS_DIR, 'BoardVisualDesign.test.tsx')
    expect(existsSync(path)).toBe(true)
    const source = readFileSync(path, 'utf-8')
    expect(
      source,
      'BoardVisualDesign.test.tsx must assert --custom-signal-claimed for claimed signal border (PDS has no purple)',
    ).toMatch(/--custom-signal-claimed/)
  })

  it('AC-4: ShellSecondaryCSS_1550.test.tsx does not assert the retired --pds-background-surface token name', () => {
    const path = resolve(TESTS_DIR, 'ShellSecondaryCSS_1550.test.tsx')
    expect(existsSync(path), 'ShellSecondaryCSS_1550.test.tsx must exist (updated, not retired)').toBe(true)
    const source = readFileSync(path, 'utf-8')
    expect(
      source,
      'ShellSecondaryCSS_1550.test.tsx must not retain --pds-background-surface assertions (replaced by --p-color-surface)',
    ).not.toMatch(/--pds-background-surface/)
  })

  it('AC-4: ShellSecondaryCSS_1550.test.tsx asserts the PDS v4 --p-color-surface token (migration applied)', () => {
    const path = resolve(TESTS_DIR, 'ShellSecondaryCSS_1550.test.tsx')
    expect(existsSync(path)).toBe(true)
    const source = readFileSync(path, 'utf-8')
    expect(
      source,
      'ShellSecondaryCSS_1550.test.tsx must reference --p-color-surface (PDS v4 replacement for --pds-background-surface)',
    ).toMatch(/--p-color-surface/)
  })
})
