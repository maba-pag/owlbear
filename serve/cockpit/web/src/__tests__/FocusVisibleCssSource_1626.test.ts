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
import { describe, it, expect, beforeAll } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const SRC_DIR = resolve(__dirname, '..')
const CARD_CSS_PATH = resolve(__dirname, '../components/Card.css')
const CUSTOM_TOKENS_PATH = resolve(__dirname, '../custom-tokens.css')

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

// ─── AC-1 (cycle 3): Pinned source-contract for custom-tokens.css ─────────────
//
// Architect review cycle 3 mandate: the source-contract must read src/custom-tokens.css
// BY RESOLVED PATH (not glob/recursive scan) and assert:
//   - all five selector parts present in that specific file
//   - the exact `outline` and `outline-offset` declarations inside the selector block
//
// This tighter contract prevents false-greens where a looser matching rule elsewhere
// in src/ could satisfy a glob-based check while the precise custom-tokens.css rule
// regresses.

describe('TestFromAC_FocusSourceContractPinned', () => {
  let source: string

  beforeAll(() => {
    source = readFileSync(CUSTOM_TOKENS_PATH, 'utf-8')
  })

  // Happy path: file is readable and non-empty (AC-1)
  it('custom-tokens.css is readable at its resolved path (AC-1)', () => {
    expect(source.length).toBeGreaterThan(0)
  })

  // Happy path: first selector part present in file (AC-1)
  it('custom-tokens.css contains button:focus-visible selector (AC-1)', () => {
    expect(
      source,
      'custom-tokens.css must declare button:focus-visible as part of the global rule.',
    ).toContain('button:focus-visible')
  })

  // Happy path: second selector part present (AC-1)
  it('custom-tokens.css contains [role="button"]:focus-visible selector (AC-1)', () => {
    expect(
      source,
      'custom-tokens.css must declare [role="button"]:focus-visible as part of the global rule.',
    ).toContain('[role="button"]:focus-visible')
  })

  // Happy path: third selector part present (AC-1)
  it('custom-tokens.css contains [role="menuitem"]:focus-visible selector (AC-1)', () => {
    expect(
      source,
      'custom-tokens.css must declare [role="menuitem"]:focus-visible as part of the global rule.',
    ).toContain('[role="menuitem"]:focus-visible')
  })

  // Happy path: fourth selector part present (AC-1)
  it('custom-tokens.css contains input:focus-visible selector (AC-1)', () => {
    expect(
      source,
      'custom-tokens.css must declare input:focus-visible as part of the global rule.',
    ).toContain('input:focus-visible')
  })

  // Happy path: fifth selector part present (AC-1)
  it('custom-tokens.css contains a:focus-visible selector (AC-1)', () => {
    expect(
      source,
      'custom-tokens.css must declare a:focus-visible as part of the global rule.',
    ).toContain('a:focus-visible')
  })

  // Happy path: outline declaration inside the rule block (AC-1)
  it('custom-tokens.css focus-visible block declares outline: 2px solid var(--color-focus) (AC-1)', () => {
    // Match the block that opens after the button:focus-visible selector group.
    // The selector list spans multiple lines; [\s\S]*? lazily reaches the { opening brace.
    const blockMatch = source.match(/button:focus-visible[\s\S]*?\{([\s\S]*?)\}/)
    expect(
      blockMatch,
      'custom-tokens.css must have a rule block starting from button:focus-visible. ' +
        'Verify the selector group and block are present.',
    ).not.toBeNull()
    const block = blockMatch![1]
    expect(
      block,
      'The focus-visible rule block must declare `outline: 2px solid var(--color-focus)`. ' +
        'Do not use hardcoded hex values or legacy tokens.',
    ).toContain('outline: 2px solid var(--color-focus)')
  })

  // Boundary: outline-offset declaration inside the rule block (AC-1)
  it('custom-tokens.css focus-visible block declares outline-offset: 2px (AC-1)', () => {
    const blockMatch = source.match(/button:focus-visible[\s\S]*?\{([\s\S]*?)\}/)
    expect(
      blockMatch,
      'custom-tokens.css must have a rule block starting from button:focus-visible.',
    ).not.toBeNull()
    const block = blockMatch![1]
    expect(
      block,
      'The focus-visible rule block must declare `outline-offset: 2px` (not 1px or any other value).',
    ).toMatch(/outline-offset\s*:\s*2px/)
  })
})

// ─── AC-1 (cycle 4): Grouped-rule extraction — single rule invariant ──────────
//
// Architect review cycle 4 mandate: the source-contract must prove the five-part
// selector group by extracting ONE rule block from custom-tokens.css and asserting
// all five selectors appear within THAT SINGLE rule's selector list.
//
// Independent per-selector toContain against the full file is explicitly insufficient
// (AC-1 frontmatter): it would false-green if selectors were split across multiple rules.
//
// Methodology:
//   1. Read src/custom-tokens.css by resolved path.
//   2. Iterate CSS rule blocks (selector text before '{' + declarations between '{' and '}').
//   3. Locate the ONE rule whose selector includes ':focus-visible' and whose declarations
//      include 'var(--color-focus)'.
//   4. Normalize whitespace in that selector list.
//   5. Assert all five selectors present in that single normalized list.
//   6. Assert both declarations ('outline: 2px solid var(--color-focus)' and
//      'outline-offset: 2px') inside that same rule block.

describe('TestFromAC_FocusSourceContractGrouped', () => {
  let normalizedSelectorList: string
  let declarationsBlock: string
  let foundRule: boolean

  beforeAll(() => {
    const source = readFileSync(CUSTOM_TOKENS_PATH, 'utf-8')

    // Extract all CSS rule blocks: iterate (selectorList, declarations) pairs.
    // Find the ONE rule whose selector contains ':focus-visible' and whose declarations
    // contain 'var(--color-focus)' — this is the global native-element focus rule.
    const CSS_RULE_RE = /([^{}]*?)\{([^}]*)\}/g
    let ruleMatch: RegExpExecArray | null
    foundRule = false
    normalizedSelectorList = ''
    declarationsBlock = ''

    while ((ruleMatch = CSS_RULE_RE.exec(source)) !== null) {
      const rawSelector = ruleMatch[1]
      const rawDeclarations = ruleMatch[2]

      if (
        rawSelector.includes(':focus-visible') &&
        rawDeclarations.includes('var(--color-focus)')
      ) {
        // Normalize whitespace: collapse newlines and repeated spaces into a single space.
        normalizedSelectorList = rawSelector.replace(/\s+/g, ' ').trim()
        declarationsBlock = rawDeclarations
        foundRule = true
        break
      }
    }
  })

  // Happy path: the rule exists (AC-1 — global focus-visible rule must be present)
  it('custom-tokens.css contains a :focus-visible rule with var(--color-focus) declarations (AC-1 grouped-rule)', () => {
    expect(
      foundRule,
      'src/custom-tokens.css must contain a CSS rule block whose selector list includes ' +
        '":focus-visible" and whose declarations contain "var(--color-focus)". ' +
        'Rule not found — it may be missing or using a different token.',
    ).toBe(true)
  })

  // Key invariant: ALL FIVE selectors appear within ONE rule's selector list (AC-1)
  // This is the grouped-rule proof that cycle-3 independent toContain checks could not provide.
  // A regression where selectors are split across multiple rules would FAIL this test.
  it('all five :focus-visible selectors appear within the ONE grouped rule selector list — not split across rules (AC-1)', () => {
    const REQUIRED_SELECTORS = [
      'button:focus-visible',
      '[role="button"]:focus-visible',
      '[role="menuitem"]:focus-visible',
      'input:focus-visible',
      'a:focus-visible',
    ] as const

    for (const selector of REQUIRED_SELECTORS) {
      expect(
        normalizedSelectorList,
        `Selector "${selector}" must appear within the SINGLE grouped rule's selector list in ` +
          'src/custom-tokens.css. Independent per-selector presence in the full file is ' +
          'insufficient — all five must be in ONE rule. ' +
          `Current extracted selector list: "${normalizedSelectorList}"`,
      ).toContain(selector)
    }
  })

  // Happy path: the grouped rule's block declares the outline shorthand (AC-1)
  it("the grouped rule's declaration block contains outline: 2px solid var(--color-focus) (AC-1)", () => {
    expect(
      declarationsBlock,
      "The global :focus-visible rule block must declare 'outline: 2px solid var(--color-focus)'. " +
        'Hardcoded hex values and legacy tokens are not acceptable.',
    ).toContain('outline: 2px solid var(--color-focus)')
  })

  // Boundary: the grouped rule's block declares the correct offset (AC-1)
  it("the grouped rule's declaration block contains outline-offset: 2px (AC-1)", () => {
    expect(
      declarationsBlock,
      "The global :focus-visible rule block must declare 'outline-offset: 2px' (not 1px or absent).",
    ).toMatch(/outline-offset\s*:\s*2px/)
  })
})

// ─── AC-3 (cycle 3): Hardcoded color prohibition in :focus-visible blocks ─────
//
// Architect review cycle 3 mandate: add an executable assertion using the AC-3 regex
// (`#[0-9a-fA-F]{3,8}|rgb\(|rgba\(|hsl\(|hsla\(`) that scans all src/**/*.css files,
// extracts :focus-visible blocks, and asserts no outline/outline-color value contains
// a hardcoded color literal.
//
// The existing legacy-token assertions (--p-color-focus, --pds-state-focus) remain
// unchanged; this test adds the missing structural color-literal prohibition.

describe('TestFromAC_FocusHardcodedColorProhibition', () => {
  // Error path: no :focus-visible block in any src/ CSS file uses a hardcoded color
  // literal in an outline or outline-color property value (AC-3).
  it('no :focus-visible block in src/**/*.css uses hardcoded color literals in outline/outline-color (AC-3)', () => {
    const cssFiles = collectCssFiles(SRC_DIR)
    // Regex from AC-3: matches hex notation and functional color notations.
    const HARDCODED_COLOR_RE = /#[0-9a-fA-F]{3,8}|rgb\(|rgba\(|hsl\(|hsla\(/

    const violations: Array<{ file: string; property: string }> = []

    for (const filePath of cssFiles) {
      const content = readFileSync(filePath, 'utf-8')
      const segments = content.split(':focus-visible')

      for (let i = 1; i < segments.length; i++) {
        const blockMatch = segments[i].match(/\s*\{([^}]+)\}/)
        if (!blockMatch) continue

        const block = blockMatch[1]
        // Extract outline and outline-color property declarations from this block.
        const outlineProps = block.match(/\boutline(?:-color)?\s*:[^;\n}]+/g) ?? []

        for (const prop of outlineProps) {
          if (HARDCODED_COLOR_RE.test(prop)) {
            const relPath = filePath.replace(SRC_DIR + '/', '')
            violations.push({ file: relPath, property: prop.trim() })
          }
        }
      }
    }

    expect(
      violations,
      'Found hardcoded color literals in :focus-visible outline/outline-color property values.\n' +
        'All :focus-visible outline colors must use CSS custom properties (e.g., var(--color-focus)).\n' +
        'Violations:\n' +
        violations.map((v) => `  ${v.file}: ${v.property}`).join('\n'),
    ).toHaveLength(0)
  })
})
