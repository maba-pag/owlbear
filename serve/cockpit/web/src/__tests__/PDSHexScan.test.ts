// Cockpit accessibility and PDS verification gate
//
// AC4 (td:2): PDS verification scans component source files (src/components/ **\/*.tsx,
//   src/*.tsx) and rejects hardcoded hex color values in JSX style props or
//   className-resolved inline styles. Token declaration files (tokens.css)
//   and CSS custom property usage (var(--pds-*)) are excluded from the scan.
//
// REGRESSION GUARD — CURRENTLY PASSES:
//   Hardcoded hex colors in Card.tsx (#e00000, #ff8000 etc.) were removed by task #1392.
//   No hex color literals remain in current component source files.
//   These tests are GREEN against the current codebase and serve as regression guards
//   to prevent future re-introduction of hardcoded hex colors.
//
// AC6 note: AC6 explicitly scopes RED tests to "where the audited problems
//   (clickable-div cards without keyboard semantics, missing keyboard movement alternative)
//   tests for the builder because no violations currently exist. They remain in the suite
//   as ongoing regression coverage for #1396 and future work.
//
// If these tests unexpectedly fail, a hex color has been re-introduced into a component
//   source file — trace the violation and replace it with a PDS CSS token (var(--pds-*)).
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// ─── Path resolution (ESM-compatible) ────────────────────────────────────────

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
// This file lives at src/__tests__/; SRC_DIR is src/
const SRC_DIR = resolve(__dirname, '..')

// ─── File discovery ───────────────────────────────────────────────────────────

// Recursively collect .tsx files under `dir`.
// Excludes: __tests__/, node_modules/, dist/, .venv/.
function findTsxFiles(dir: string): string[] {
  const EXCLUDED_DIRS = new Set(['__tests__', 'node_modules', 'dist', '.venv', 'build'])
  const result: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory() && !EXCLUDED_DIRS.has(entry.name)) {
      result.push(...findTsxFiles(resolve(dir, entry.name)))
    } else if (entry.isFile() && entry.name.endsWith('.tsx')) {
      result.push(resolve(dir, entry.name))
    }
  }
  return result
}

// ─── Hex color detection ──────────────────────────────────────────────────────

// Match hex color literals that appear in string contexts (JSX style props).
// Matches: '#fff', '#FF0000', '#AABBCC', '#12345678' (3-8 hex digits).
// Does NOT match: hex in comments, 'var(--pds-...)', tokens.css entries.
// Excludes comment lines (// ... and * ...) and var(--pds-...) usage.
const HEX_LITERAL_PATTERN = /['"`](#[0-9a-fA-F]{3,8})['"`]/g

function findHexViolations(source: string, filePath: string): string[] {
  const violations: string[] = []
  const lines = source.split('\n')

  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const line = lines[lineIdx]
    const trimmed = line.trim()

    // Skip comment lines
    if (trimmed.startsWith('//') || trimmed.startsWith('*') || trimmed.startsWith('/*')) {
      continue
    }
    // Strip PDS token usages (var(--pds-...)) before checking for hex.
    // Do NOT skip the entire line — a line with both a PDS token and a hex literal
    // must still be flagged for the hex literal.
    const lineToScan = line.replace(/var\(--pds-[^)]*\)/g, '')

    const matches = [...lineToScan.matchAll(HEX_LITERAL_PATTERN)]
    for (const match of matches) {
      violations.push(`${filePath}:${lineIdx + 1}: ${match[0]}`)
    }
  }

  return violations
}

// ─── AC4: PDS hex scan ────────────────────────────────────────────────────────

describe('TestFromAC_PDSHexScan', () => {
  // Regression guard: component files must not contain hardcoded hex colors.

  it('src/components/**/*.tsx contains no hardcoded hex color literals in style contexts (AC4)', () => {
    const componentsDir = resolve(SRC_DIR, 'components')
    const files = findTsxFiles(componentsDir)

    expect(files.length, 'components directory must contain at least one .tsx file').toBeGreaterThan(0)

    const violations: string[] = []
    for (const file of files) {
      const source = readFileSync(file, 'utf-8')
      violations.push(...findHexViolations(source, file.replace(SRC_DIR + '/', 'src/')))
    }

    // Regression guard: 0 violations expected (all hex colors removed by #1392).
    // If this fails, a hex literal was re-introduced — replace with var(--pds-*) token.
    expect(
      violations,
      `Hardcoded hex colors found in component files:\n${violations.join('\n')}`,
    ).toEqual([])
  })

  it('src/*.tsx root-level files contain no hardcoded hex color literals in style contexts (AC4)', () => {
    const files = findTsxFiles(SRC_DIR).filter((f) => {
      // Only direct children of SRC_DIR (not subdirectories)
      const relative = f.replace(SRC_DIR + '/', '')
      return !relative.includes('/')
    })

    const violations: string[] = []
    for (const file of files) {
      const source = readFileSync(file, 'utf-8')
      violations.push(...findHexViolations(source, file.replace(SRC_DIR + '/', 'src/')))
    }

    expect(
      violations,
      `Hardcoded hex colors found in root src/*.tsx files:\n${violations.join('\n')}`,
    ).toEqual([])
  })

  it('PDS token usage (var(--pds-*)) is not incorrectly flagged by the hex scanner (AC4)', () => {
    // Sanity check: var(--pds-*) patterns are excluded and do not produce false positives.
    // This test fails only if the exclusion logic is broken.
    const synthetic = `
      const COLORS = {
        critical: 'var(--pds-theme-light-notification-error)',
        needed: 'var(--pds-theme-light-notification-warning)',
      }
    `
    const violations = findHexViolations(synthetic, 'synthetic-test')
    expect(violations).toEqual([])
  })

  it('the hex scanner correctly detects a hardcoded hex color when present (AC4 — scanner validity)', () => {
    // Self-test: proves the scanner would catch actual violations.
    // This test MUST PASS to validate the scanner is not a no-op.
    const syntheticWithHex = `
      const COLORS = { critical: '#e00000', needed: '#ff8000' }
    `
    const violations = findHexViolations(syntheticWithHex, 'synthetic-with-hex')
    expect(violations.length).toBeGreaterThan(0)
  })

  it('hex scanner detects hex literals on lines that also contain var(--pds-*) tokens (AC4)', () => {
    // A line with BOTH a PDS token AND a hardcoded hex literal must NOT be skipped entirely.
    // The current scanner skips the whole line when var(--pds-) is present, allowing a
    // trailing hex value to slip through undetected — a false-green.
    // Fix: strip only the var(--pds-...) segments before scanning, not the whole line.
    const mixedLine = `  style={{ color: 'var(--pds-theme-light-notification-error)', background: '#ff0000' }}`
    const violations = findHexViolations(mixedLine, 'synthetic-mixed-token-hex')
    // FAILS with current scanner: it skips the entire line due to var(--pds-) → returns []
    expect(
      violations.length,
      'scanner must detect the hex literal even when a PDS token appears on the same line',
    ).toBeGreaterThan(0)
  })
})
