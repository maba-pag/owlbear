/**
 * RED-phase tests for Tailwind v4 Vite plugin + Stylelint at-rule recognition — task #1592
 *
 * AC-1: dist/assets/*.css contains compiled CSS selectors for PDS Tailwind utility classes
 *       bg-canvas, text-contrast-high, gap-fluid-md, rounded-sm.
 *       Fails RED: @tailwindcss/vite not installed → no utility compilation → no selectors in dist.
 *
 * AC-2: dist CSS contains PDS Tailwind-compiled color custom properties using light-dark().
 *       Verified by finding --color-* variable assignments with light-dark( in compiled dist.
 *       Fails RED: without @tailwindcss/vite the PDS @theme block is never processed →
 *       no --color-* vars emitted → no light-dark() in utility-class context in dist.
 *
 * AC-3: Stylelint with project .stylelintrc.json does not flag @theme, @utility, or @apply
 *       as unknown at-rules when run on a CSS fixture containing them.
 *       Fails RED: current config has at-rule-no-unknown: true without ignoreAtRules →
 *       Stylelint exits non-zero on Tailwind v4 at-rules.
 *
 * Builder: #1595 (install @tailwindcss/vite + tailwindcss, import PDS theme, update Stylelint config).
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { existsSync, readFileSync, readdirSync, writeFileSync, unlinkSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import { tmpdir } from 'node:os'

// ─── Path resolution (ESM-compatible) ─────────────────────────────────────────

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// serve/cockpit/web/
const WEB_DIR = resolve(__dirname, '..', '..')
// serve/cockpit/dist/assets/  (vite.config.ts: outDir: '../dist')
const DIST_ASSETS_DIR = resolve(WEB_DIR, '..', 'dist', 'assets')
// node_modules/.bin/vite → ../vite/bin/vite.js (Node.js script, invoke via node)
const VITE_BIN = resolve(WEB_DIR, 'node_modules', '.bin', 'vite')
// Fixture source file: deterministic Tailwind utility-class input for build (AC-1 reviewer finding)
const FIXTURE_FILE = resolve(WEB_DIR, 'src', '_tailwind-test-fixture-1592.tsx')
const FIXTURE_CONTENT = [
  '// Tailwind v4 test fixture — created and removed by TailwindStylelint_1592.test.ts',
  'export const TailwindTestFixture = () => (',
  '  <div className="bg-canvas text-contrast-high gap-fluid-md rounded-sm" />',
  ')',
  '',
].join('\n')

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Collect all .css files under a directory. Returns empty array if dir doesn't exist. */
function readCssFiles(dir: string): string[] {
  if (!existsSync(dir)) {
    return []
  }
  return readdirSync(dir)
    .filter((f) => f.endsWith('.css'))
    .map((f) => readFileSync(resolve(dir, f), 'utf-8'))
}

/** Concatenate all dist CSS into one string for pattern matching. */
function getDistCss(): string {
  return readCssFiles(DIST_ASSETS_DIR).join('\n')
}

// ─── AC-1: PDS Tailwind utility class compilation ─────────────────────────────

describe('TestFromAC_TailwindBuildOutput', () => {
  /**
   * Create a deterministic fixture source file with the four PDS utility classes, then
   * run a fresh `vite build`. Without @tailwindcss/vite the scanner finds the classes
   * in the fixture but emits no compiled selectors — giving AC-1/AC-2 a causal RED path.
   * (Cycle-3 fix: reviewer cycle-2 finding 1 — previous retry had no fixture input.)
   */
  beforeAll(() => {
    writeFileSync(FIXTURE_FILE, FIXTURE_CONTENT, 'utf-8')
    const result = spawnSync('node', [VITE_BIN, 'build'], {
      cwd: WEB_DIR,
      encoding: 'utf-8',
    })
    if (result.status !== 0) {
      throw new Error(
        `vite build failed (exit ${result.status ?? 'null'}):\n${result.stderr}`,
      )
    }
  }, 120_000) // 2-minute budget for the build

  afterAll(() => {
    if (existsSync(FIXTURE_FILE)) {
      unlinkSync(FIXTURE_FILE)
    }
  })

  /**
   * AC-1: dist/assets/*.css must contain compiled CSS selectors for PDS utility classes.
   * Each class is emitted by @tailwindcss/vite when it processes the PDS theme CSS.
   * Selectors appear as `.bg-canvas`, `.text-contrast-high`, etc. (possibly minified
   * to `.bg-canvas{` without space).
   *
   * RED failure cause: @tailwindcss/vite not installed → vite build does not process
   * the PDS @theme block → no utility selectors emitted → dist is empty or lacks these.
   */

  it('AC-1: dist/assets/*.css contains a compiled .bg-canvas CSS selector', () => {
    const css = getDistCss()
    expect(
      css,
      'dist/assets/*.css must contain compiled .bg-canvas selector — fails RED because ' +
        '@tailwindcss/vite is not installed so no Tailwind utility classes are emitted',
    ).toMatch(/\.bg-canvas[\s{,:]/)
  })

  it('AC-1: dist/assets/*.css contains a compiled .text-contrast-high CSS selector', () => {
    const css = getDistCss()
    expect(
      css,
      'dist/assets/*.css must contain compiled .text-contrast-high selector — ' +
        'fails RED because @tailwindcss/vite is not installed',
    ).toMatch(/\.text-contrast-high[\s{,:]/)
  })

  it('AC-1: dist/assets/*.css contains a compiled .gap-fluid-md CSS selector', () => {
    const css = getDistCss()
    expect(
      css,
      'dist/assets/*.css must contain compiled .gap-fluid-md selector — ' +
        'fails RED because @tailwindcss/vite is not installed',
    ).toMatch(/\.gap-fluid-md[\s{,:]/)
  })

  it('AC-1: dist/assets/*.css contains a compiled .rounded-sm CSS selector', () => {
    const css = getDistCss()
    expect(
      css,
      'dist/assets/*.css must contain compiled .rounded-sm selector — ' +
        'fails RED because @tailwindcss/vite is not installed',
    ).toMatch(/\.rounded-sm[\s{,:]/)
  })

  // ─── AC-2: light-dark() preservation in Tailwind-compiled PDS color output ───

  /**
   * AC-2: Asserts two things about the fresh build output:
   *   (a) @theme at-rule is ABSENT from dist CSS — discriminates Tailwind-processed output
   *       from raw lightningcss passthrough (Tailwind consumes @theme → not in dist).
   *   (b) --color-* custom property declarations with light-dark() values ARE present —
   *       emitted by @tailwindcss/vite when it processes the PDS @theme block.
   *
   * RED failure cause: without @tailwindcss/vite, PDS @theme is never processed →
   * no --color-* declarations emitted (b fails). Assertion (a) guards against false-green
   * where raw @theme passthrough could emit variables without Tailwind compilation.
   * (Cycle-3 fix: architect cycle-3 refinement — added (a) discriminator.)
   */
  it('AC-2: dist/assets/*.css shows @theme consumed by Tailwind (absent) and --color-* properties with light-dark() emitted', () => {
    const css = getDistCss()
    // (a) discriminator: Tailwind processes @theme → block absent from dist output
    expect(
      css,
      'dist/assets/*.css must NOT contain raw @theme { — its presence indicates lightningcss ' +
        'passthrough rather than Tailwind compilation of the PDS theme',
    ).not.toMatch(/@theme\s*\{/)
    // (b) Tailwind emits PDS color vars as :root custom properties with light-dark() values
    // Pattern: --color-<name>: light-dark( — produced only by Tailwind processing PDS @theme
    // RED: without @tailwindcss/vite no --color-* declarations emitted → this assertion fails
    expect(
      css,
      'dist/assets/*.css must contain a PDS Tailwind-compiled --color-* variable with ' +
        'light-dark() value — fails RED because without @tailwindcss/vite the PDS @theme ' +
        'block is not processed and no --color-* declarations with light-dark() are emitted',
    ).toMatch(/--color-[a-z][a-z0-9-]*\s*:\s*light-dark\(/)
  })
})

// ─── AC-3: Stylelint allows Tailwind v4 at-rules ─────────────────────────────

describe('TestFromAC_StylelintAtRules', () => {
  /**
   * AC-3: .stylelintrc.json must allow @theme, @utility, and @apply without flagging them
   * as unknown at-rules. Tests run Stylelint via CLI on a CSS fixture file containing
   * each at-rule in isolation, asserting exit code 0.
   *
   * RED failure cause: current .stylelintrc.json has "at-rule-no-unknown": true with no
   * ignoreAtRules option → Stylelint exits non-zero on @theme, @utility, @apply.
   */

  const STYLELINT_BIN = resolve(WEB_DIR, 'node_modules', '.bin', 'stylelint')
  const STYLELINT_CONFIG = resolve(WEB_DIR, '.stylelintrc.json')

  function runStylelintOnFixture(fixtureCSS: string): ReturnType<typeof spawnSync> {
    const tmpFile = resolve(tmpdir(), `stylelint-fixture-1592-${Date.now()}.css`)
    writeFileSync(tmpFile, fixtureCSS, 'utf-8')
    try {
      return spawnSync(
        'node',
        [STYLELINT_BIN, '--config', STYLELINT_CONFIG, tmpFile],
        { cwd: WEB_DIR, encoding: 'utf-8' },
      )
    } finally {
      unlinkSync(tmpFile)
    }
  }

  it('AC-3: Stylelint does not flag @theme as an unknown at-rule', () => {
    const result = runStylelintOnFixture('@theme {\n  --color-test: red;\n}\n')
    expect(
      result.status,
      `Stylelint must exit 0 on @theme — stdout: ${result.stdout}\nstderr: ${result.stderr}`,
    ).toBe(0)
  })

  it('AC-3: Stylelint does not flag @utility as an unknown at-rule', () => {
    const result = runStylelintOnFixture('@utility test-util {\n  display: block;\n}\n')
    expect(
      result.status,
      `Stylelint must exit 0 on @utility — stdout: ${result.stdout}\nstderr: ${result.stderr}`,
    ).toBe(0)
  })

  it('AC-3: Stylelint passes on combined @theme + @utility + @apply fixture, and still rejects @foobar', () => {
    const fixture = [
      '@theme {',
      '  --color-canvas: light-dark(#fff, hsl(225 66.7% 1.2%));',
      '}',
      '',
      '@utility bg-canvas {',
      '  background-color: var(--color-canvas);',
      '}',
      '',
      '.component {',
      '  @apply bg-canvas;',
      '}',
      '',
    ].join('\n')
    const resultCombined = runStylelintOnFixture(fixture)
    // Fails RED: at-rule-no-unknown: true without ignoreAtRules → @theme/@utility/@apply rejected
    expect(
      resultCombined.status,
      `Stylelint must exit 0 on combined @theme + @utility + @apply fixture — ` +
        `stdout: ${resultCombined.stdout}\nstderr: ${resultCombined.stderr}`,
    ).toBe(0)
    // Guard: @foobar must still be flagged — proves ignoreAtRules is targeted, not a global disable.
    // (Cycle-3 fix: architect cycle-3 refinement — prevents false-green from disabling entire rule.)
    const resultGuard = runStylelintOnFixture('@foobar {\n  --test: 1;\n}\n')
    expect(
      resultGuard.status,
      `Stylelint must still flag @foobar as an unknown at-rule (exit non-zero) — ` +
        `proves ignoreAtRules is a targeted allowlist, not a global rule disable. ` +
        `stdout: ${resultGuard.stdout}\nstderr: ${resultGuard.stderr}`,
    ).not.toBe(0)
  })
})
