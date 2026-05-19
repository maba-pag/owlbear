/** Token migration regressions for PDS v4 token adoption and legacy CSS cleanup. */
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

describe('PDS token namespace cleanup', () => {
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

describe('token file migration', () => {
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

  it('AC-2: custom-tokens.css declares exactly two custom properties (--custom-signal-claimed + --p-color-contrast-low)', () => {
    expect(existsSync(CUSTOM_TOKENS_CSS_PATH), 'custom-tokens.css must exist').toBe(true)
    const css = readFileSync(CUSTOM_TOKENS_CSS_PATH, 'utf-8')
    const cssNoComments = css.replace(/\/\*[\s\S]*?\*\//g, '')
    const declarations = [...cssNoComments.matchAll(/--[a-z][a-z0-9-]*\s*:/g)]
    expect(
      declarations.length,
      `custom-tokens.css must declare exactly 2 custom properties, found ${declarations.length}: ` +
        declarations.map((m) => m[0].replace(':', '')).join(', '),
    ).toBe(2)
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

describe('dark-mode override removal', () => {
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

describe('retired legacy token tests', () => {
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
// Card.css.supplemental.test.ts was removed — Card.css is replaced by PDS Tailwind in Card.tsx.
// Signal border mapping is enforced via Card.visual-treatment.test.tsx DOM tests.
// --custom-signal-claimed is used in Card.tsx source (inline Tailwind class).

describe('migrated token test coverage', () => {
  it('AC-4: BoardVisualDesign.test.tsx no longer asserts [data-theme="dark"] block in tokens.css (file deleted)', () => {
    const path = resolve(TESTS_DIR, 'BoardVisualDesign.test.tsx')
    expect(existsSync(path), 'BoardVisualDesign.test.tsx must exist (updated, not retired)').toBe(true)
    const source = readFileSync(path, 'utf-8')
    expect(
      source,
      'BoardVisualDesign.test.tsx must not assert [data-theme="dark"] override block — tokens.css is deleted',
    ).not.toMatch(/\[data-theme\s*=\s*["']dark["']\]\s*block/)
  })

  it('AC-4: Card.tsx source uses --custom-signal-claimed for claimed signal border', () => {
    const cardPath = resolve(TESTS_DIR, '..', 'components', 'Card.tsx')
    expect(existsSync(cardPath), 'Card.tsx must exist').toBe(true)
    const source = readFileSync(cardPath, 'utf-8')
    expect(
      source,
      'Card.tsx must use --custom-signal-claimed token for claimed signal border (PDS has no purple)',
    ).toMatch(/--custom-signal-claimed/)
  })
})
