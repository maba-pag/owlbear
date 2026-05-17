/**
 * RED phase Vitest tests for #1626: P3-06 — Focus-visible rings (PDS focus styling)
 *
 * CSS source-contract tests for AC-2:
 *   AC-2: Focus rings use `var(--color-focus)` from PDS Tailwind theme (not custom
 *         `--p-color-focus` or hardcoded values); Card.css migrated from
 *         `--p-color-focus` to `--color-focus` with `outline-offset: 2px`.
 *
 * These tests inspect the CSS source files on disk to verify the token migration.
 * Computed-style checks for the PDS color cannot distinguish --p-color-focus from
 * --color-focus (both resolve to #1A44EA), so source-level proof is required.
 *
 * RED reasons:
 *   - Card.css `:focus-visible` rule uses `var(--p-color-focus)` — check for
 *     `var(--color-focus)` FAILS.
 *   - Card.css `:focus-visible` rule has `outline-offset: 1px` — check for `2px` FAILS.
 *   - No CSS file in src/ contains a global `:focus-visible` rule targeting native
 *     elements (`button`, `input`, `a`) with `var(--color-focus)` — FAILS.
 *   - Card.css `:focus-visible` block still references `--p-color-focus` — the
 *     "no legacy token in any :focus-visible rule" check FAILS.
 *
 * Behavioral (computed-style) coverage is in:
 *   serve/cockpit/web/e2e/focus-visible-pds-1626.spec.ts
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const SRC_DIR = resolve(__dirname, '..')
const CARD_CSS_PATH = resolve(__dirname, '../components/Card.css')

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Collect all .css file paths recursively under a directory.
 * Excludes node_modules.
 */
function collectCssFiles(dir: string): string[] {
  const results: string[] = []
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules') continue
    const fullPath = join(dir, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      results.push(...collectCssFiles(fullPath))
    } else if (entry.endsWith('.css')) {
      results.push(fullPath)
    }
  }
  return results
}

// ─── AC-2: Card.css token migration ───────────────────────────────────────────
//
// Card.css currently:
//   .card:focus-visible {
//     outline: 2px solid var(--p-color-focus);
//     outline-offset: 1px;
//   }
//
// After migration must be:
//   .card:focus-visible {
//     outline: 2px solid var(--color-focus);
//     outline-offset: 2px;
//   }

describe('TestFromAC_FocusTokenSource', () => {
  // Happy path: Card.css :focus-visible rule references --color-focus (AC-2)
  // RED: Card.css uses var(--p-color-focus) → string match for var(--color-focus) FAILS.
  it('Card.css :focus-visible block references var(--color-focus) (not --p-color-focus) (AC-2)', () => {
    const source = readFileSync(CARD_CSS_PATH, 'utf-8')

    // Extract the :focus-visible block for .card
    const focusBlockMatch = source.match(/\.card:focus-visible\s*\{([^}]+)\}/)
    expect(
      focusBlockMatch,
      'Card.css must contain a .card:focus-visible { ... } block. ' +
        'Check that the rule was not accidentally removed.',
    ).not.toBeNull()

    const focusBlock = focusBlockMatch![1]

    expect(
      focusBlock,
      'Card.css :focus-visible block must reference var(--color-focus) — the PDS canonical ' +
        'token. RED: block currently uses var(--p-color-focus) which is a custom legacy token.',
    ).toContain('var(--color-focus)')
  })

  // Happy path: Card.css :focus-visible rule has outline-offset: 2px (AC-2)
  // RED: Card.css has `outline-offset: 1px` → check for '2px' FAILS.
  it('Card.css :focus-visible block has outline-offset: 2px (AC-2)', () => {
    const source = readFileSync(CARD_CSS_PATH, 'utf-8')

    const focusBlockMatch = source.match(/\.card:focus-visible\s*\{([^}]+)\}/)
    expect(focusBlockMatch, 'Card.css must contain a .card:focus-visible block.').not.toBeNull()

    const focusBlock = focusBlockMatch![1]

    expect(
      focusBlock,
      'Card.css :focus-visible block must have outline-offset: 2px. ' +
        'RED: block currently has outline-offset: 1px (pre-migration value).',
    ).toMatch(/outline-offset\s*:\s*2px/)
  })

  // Error path: Card.css :focus-visible block must NOT reference --p-color-focus (AC-2)
  // RED: Card.css still uses var(--p-color-focus) → this assertion FAILS.
  // GREEN: After migration, --p-color-focus is replaced with --color-focus → PASSES.
  it('Card.css :focus-visible block does not reference legacy --p-color-focus token (AC-2)', () => {
    const source = readFileSync(CARD_CSS_PATH, 'utf-8')

    const focusBlockMatch = source.match(/\.card:focus-visible\s*\{([^}]+)\}/)
    expect(focusBlockMatch, 'Card.css must contain a .card:focus-visible block.').not.toBeNull()

    const focusBlock = focusBlockMatch![1]

    expect(
      focusBlock,
      'Card.css :focus-visible block must not reference --p-color-focus. ' +
        'RED: block still has var(--p-color-focus) — migration not yet applied.',
    ).not.toContain('--p-color-focus')
  })

  // Happy path: some CSS file in src/ contains a :focus-visible rule covering native
  // elements (button, input, a) using var(--color-focus) (AC-2 global rule)
  // RED: no global :focus-visible rule for native elements exists → FAILS.
  it('a CSS file in src/ contains a :focus-visible rule for native elements using var(--color-focus) (AC-2)', () => {
    const cssFiles = collectCssFiles(SRC_DIR)
    expect(
      cssFiles.length,
      'Expected to find at least one .css file in src/. Check the SRC_DIR path.',
    ).toBeGreaterThan(0)

    // A global :focus-visible rule for native elements must:
    // 1. Include a relevant native selector (button, input, or standalone `a`)
    // 2. Use var(--color-focus) in the declaration block
    // We test this by looking for files containing BOTH :focus-visible and var(--color-focus)
    // where the :focus-visible context also references a native-element selector.
    const fileWithGlobalRule = cssFiles.find((filePath) => {
      const content = readFileSync(filePath, 'utf-8')

      // Must reference var(--color-focus) somewhere
      if (!content.includes('var(--color-focus)')) return false

      // Must have a :focus-visible block that is NOT scoped solely to .card
      // (i.e., it targets native elements: button, input, or `a` outside card context)
      //
      // Strategy: find any :focus-visible occurrence that is preceded by
      // a selector containing 'button', 'input', or a bare 'a' (not inside a .card scope).
      // A regex that looks for patterns like:
      //   button:focus-visible  |  button, ... :focus-visible  |  :where(button,...):focus-visible
      //   input:focus-visible   |  a:focus-visible             |  button { :focus-visible { ... } }
      const hasNativeElementFocusRule = /(?:^|\n)\s*(?:[^{]*\b(?:button|input)\b[^{]*|a:focus-visible)/m.test(
        content,
      )

      // Also match Tailwind/nesting syntax: `button { ... &:focus-visible`
      const hasNestedFocusRule = /button[\s\S]{0,200}:focus-visible/m.test(content)

      // Match a single-selector or group selector containing button or input near :focus-visible
      const hasSelectorNearFocus = /(?:button|input|a)[^{]{0,200}:focus-visible|:focus-visible[^{]{0,200}(?:button|input)/m.test(
        content,
      )

      return hasNativeElementFocusRule || hasNestedFocusRule || hasSelectorNearFocus
    })

    expect(
      fileWithGlobalRule,
      'No CSS file in src/ was found containing a :focus-visible rule that targets native ' +
        'elements (button, input, a) using var(--color-focus). RED: the global :focus-visible ' +
        'rule for native elements has not been added yet. Builder must add a rule such as:\n' +
        '  button:focus-visible, [role="button"]:focus-visible,\n' +
        '  [role="menuitem"]:focus-visible, input:focus-visible, a:focus-visible {\n' +
        '    outline: 2px solid var(--color-focus);\n' +
        '    outline-offset: 2px;\n' +
        '  }',
    ).toBeDefined()
  })

  // Boundary: no :focus-visible rule in any src/ CSS file references --p-color-focus
  // RED: Card.css :focus-visible block uses var(--p-color-focus) → FAILS.
  // GREEN: After migration, no :focus-visible block uses the legacy token → PASSES.
  it('no :focus-visible block in any src/ CSS file references legacy --p-color-focus token (AC-2)', () => {
    const cssFiles = collectCssFiles(SRC_DIR)

    const violations: string[] = []

    for (const filePath of cssFiles) {
      const content = readFileSync(filePath, 'utf-8')

      // Find :focus-visible blocks and check if any reference --p-color-focus
      // Split on :focus-visible occurrences and check the block that follows each
      const segments = content.split(':focus-visible')
      for (let i = 1; i < segments.length; i++) {
        // Extract characters up to the closing } of the block that follows :focus-visible
        const blockMatch = segments[i].match(/\s*\{([^}]+)\}/)
        if (blockMatch && blockMatch[1].includes('--p-color-focus')) {
          const relPath = filePath.replace(SRC_DIR + '/', '')
          violations.push(relPath)
          break
        }
      }
    }

    expect(
      violations,
      'The following CSS files contain a :focus-visible block referencing the legacy ' +
        '--p-color-focus token. Migrate each to var(--color-focus):\n' +
        violations.map((f) => `  - ${f}`).join('\n') +
        '\nRED: Card.css :focus-visible block still uses var(--p-color-focus).',
    ).toHaveLength(0)
  })

  // Error path: no :focus-visible block in any src/ CSS file references --pds-state-focus (AC-3)
  // Architecture review cycle 2 (challenge #3 accepted): AC-3 now names both legacy tokens
  // (--pds-state-focus AND --p-color-focus). Both must be absent from all :focus-visible blocks.
  // GREEN: no CSS file uses --pds-state-focus in a :focus-visible context.
  it('no :focus-visible block in any src/ CSS file references legacy --pds-state-focus token (AC-3)', () => {
    const cssFiles = collectCssFiles(SRC_DIR)

    const violations: string[] = []

    for (const filePath of cssFiles) {
      const content = readFileSync(filePath, 'utf-8')

      const segments = content.split(':focus-visible')
      for (let i = 1; i < segments.length; i++) {
        const blockMatch = segments[i].match(/\s*\{([^}]+)\}/)
        if (blockMatch && blockMatch[1].includes('--pds-state-focus')) {
          const relPath = filePath.replace(SRC_DIR + '/', '')
          violations.push(relPath)
          break
        }
      }
    }

    expect(
      violations,
      'The following CSS files contain a :focus-visible block referencing the legacy ' +
        '--pds-state-focus token. Migrate each to var(--color-focus):\n' +
        violations.map((f) => `  - ${f}`).join('\n') +
        '\nAC-3: no :focus-visible rule may reference --pds-state-focus.',
    ).toHaveLength(0)
  })
})
