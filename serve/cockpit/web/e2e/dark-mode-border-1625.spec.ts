/**
 * RED phase Playwright E2E tests for #1625: P3-04 — Dark mode audit, border contrast + token compliance
 *
 * AC-1: In dark mode (.scheme-dark active), border-color on shell structural elements
 *       (.shell__sidecar, .shell__nav-rail borders), Column, and FilterPanel has >= 1.3:1
 *       contrast ratio against adjacent background — verified via Playwright computed-style assertions.
 *
 * AC-3: Computed border-color values differ between light (.scheme-light) and dark (.scheme-dark)
 *       schemes on >= 2 structural border elements — confirms intentional per-scheme token
 *       switching, not filter inversion.
 *
 * AC-4: Card.css --pds-border-subtle (or post-migration successor) resolves to a defined
 *       custom property value in both color schemes — no undefined var() references in
 *       border declarations.
 *
 * RED evidence (quality-runner verified, 2026-05-17 retry 2):
 *
 *   Token injection: PDS CSS custom properties (--p-color-contrast-low etc.) are not
 *   injected in Playwright tests because PDS loads its global-styles CSS asynchronously
 *   via load() in main.tsx, which requires CDN assets not available locally. When tokens
 *   are undefined, CSS `border:` shorthands collapse to border-style:none → border-width:0px.
 *   ensurePDSTokens() injects the actual PDS v4 token values so tests distinguish
 *   "missing declaration" (FAIL in RED) from "token unavailable" (infra issue).
 *
 *   AC-2 (static token compliance): Pre-satisfied by migration (#1614–#1618).
 *     All CSS border declarations use var() references — no hardcoded colors.
 *     Removed from RED file per w-tdd-red §5.
 *
 *   TestFromAC_DarkModeBorderContrast (AC-1):
 *     - sidecar: PASSED after token injection (Shell.css has border-left) → removed per §5.
 *     - nav-rail: FAILS (border-right-width = 0, no border-right declaration) → 1 test kept.
 *     - column: PASSED after token injection (Column.css has border) → removed per §5.
 *     - filter-panel: PASSED after token injection (FilterPanel.css has border) → removed per §5.
 *
 *   TestFromAC_DarkModeBorderSchemeSwitch (AC-3):
 *     - nav-rail: FAILS (border-right-width = 0) → 1 test kept.
 *
 *   TestFromAC_CardChipBorderResolution (AC-4):
 *     - card-chip dark: PASSED after token injection (Card.css has border) → removed per §5.
 *     - card-chip light: PASSED after token injection → removed per §5.
 *
 *   Final RED: 2 tests, both targeting missing nav-rail border-right declaration.
 *   Builder fix: add border-right: 1px solid var(--p-color-contrast-low) to .shell__nav-rail in Shell.css.
 *
 * API isolation: all /api/* routes stubbed — no backend required.
 * LIFO route registration: catch-all registered first, specific routes registered last (highest priority).
 */
import { test, expect, type Page } from '@playwright/test'

// ─── Board and task fixtures ──────────────────────────────────────────────────

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: PRIORITIES,
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  } as Record<string, string[]>,
}

// Include a task with tags so .card-chip elements are rendered for AC-4 tests
const TASKS = {
  tasks: [
    {
      id: 1,
      title: 'Border audit task',
      status: 'todo',
      priority: 'important',
      updated: '2026-05-16T00:00:00+00:00',
      tags: ['frontend', 'pds'],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
    {
      id: 2,
      title: 'No-tag task',
      status: 'backlog',
      priority: 'needed',
      updated: '2026-05-16T00:00:00+00:00',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    },
  ],
  mtime: 1_713_456_000,
}

// ─── API stub helper ──────────────────────────────────────────────────────────

/**
 * Stub all API routes with LIFO semantics.
 * Catch-all registered first → specific handlers registered after take priority.
 */
async function stubApis(page: Page): Promise<void> {
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))
  await page.route('/api/events', (route) =>
    route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body: '',
    }),
  )
  await page.route('/api/tasks', (route) => route.fulfill({ json: TASKS }))
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
}

// ─── Style readiness guard ────────────────────────────────────────────────────

/**
 * Inject PDS CSS token stubs via a style tag so that var(--p-color-contrast-low)
 * references in Shell.css, Column.css, FilterPanel.css, and Card.css resolve to
 * a defined, non-transparent value.
 *
 * Root cause of the original 0px failure:
 * PDS loads its global CSS (`variables.css`) asynchronously via the `load()` call
 * in main.tsx. In Playwright tests the CDN is redirected to localhost, but no
 * PDS CSS files exist at those paths, so the injection never completes.
 * When `--p-color-contrast-low` is undefined, any CSS shorthand using it
 * (`border: 1px solid var(--p-color-contrast-low)`) triggers an invalid
 * substitution → every constituent longhand falls back to its initial value
 * (`border-style: none` → `border-width: 0px`). This masks whether a declaration
 * exists, making it impossible for the builder to distinguish missing-declaration
 * failures (nav-rail) from token-unavailability failures (all other elements).
 *
 * Fix: inject the actual PDS v4 token values as a static style tag so that:
 * - Elements WITH correct border declarations render a visible border (width > 0).
 * - Elements MISSING a declaration (nav-rail) still show border-width = 0px.
 *
 * Token values taken verbatim from
 * @porsche-design-system/components-react/global-styles/variables.css.
 * The `scheme` parameter selects the dark or light variant of each light-dark()
 * pair so that contrast-ratio assertions use the correct colours.
 *
 * Call after page.goto() and before waitFor()/evaluate() in each test.
 */
async function ensurePDSTokens(page: Page, scheme: 'dark' | 'light' = 'light'): Promise<void> {
  // Values from PDS v4 global-styles/variables.css — light-dark() pairs split by scheme.
  const tokens =
    scheme === 'dark'
      ? {
          '--p-color-contrast-low': 'hsl(240 12.5% 96.9% / 0.45)',
          '--p-color-contrast-medium': 'hsl(240 12.5% 96.9% / 0.7)',
          '--p-color-surface': 'hsl(240 2% 10%)',
          '--p-color-canvas': 'hsl(225 66.7% 1.2%)',
          '--p-color-primary': 'hsl(225 100% 99%)',
        }
      : {
          '--p-color-contrast-low': 'hsl(240 5.3% 14.9% / 0.5)',
          '--p-color-contrast-medium': 'hsl(240 5.3% 14.9% / 0.75)',
          '--p-color-surface': 'hsl(240 10% 95%)',
          '--p-color-canvas': '#fff',
          '--p-color-primary': 'hsl(225 66.7% 1.2%)',
        }

  const css = [':root {', ...Object.entries(tokens).map(([k, v]) => `  ${k}: ${v};`), '}'].join('\n')
  await page.addStyleTag({ content: css })
}

// ─── WCAG 2.1 contrast ratio measurement helper ───────────────────────────────

/**
 * Measure WCAG 2.1 relative-luminance contrast ratio between a border and the
 * shell canvas background. The border color (which may be semi-transparent via
 * var(--p-color-contrast-low)) is first composited over the element's own
 * background, then compared against the shell canvas — the surface that is
 * directly adjacent to nav-rail, sidecar, column, and filter-panel borders.
 *
 * @param page       - Playwright Page object (must have PDS tokens already injected)
 * @param elementSel - CSS selector for the bordered element
 * @param borderProp - camelCase computed style property for the border side to check
 *                     (e.g. 'borderRightColor', 'borderLeftColor', 'borderTopColor')
 */
async function measureBorderContrast(
  page: Page,
  elementSel: string,
  borderProp: string,
): Promise<{ found: boolean; contrastRatio: number; borderColor: string; canvasBg: string; hasSchemeDark: boolean }> {
  return page.evaluate(
    ({ sel, prop }: { sel: string; prop: string }) => {
      // Convert camelCase to kebab-case for getPropertyValue
      const toKebab = (s: string) => s.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)

      const parseRgba = (s: string) => {
        const m = s.match(
          /rgba?\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)(?:,\s*(\d+(?:\.\d+)?))?\)/,
        )
        return m ? { r: +m[1]!, g: +m[2]!, b: +m[3]!, a: m[4] !== undefined ? +m[4]! : 1 } : null
      }
      const lin = (c: number) => {
        const s = c / 255
        return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
      }
      const lum = (r: number, g: number, b: number) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

      const el = document.querySelector<HTMLElement>(sel)
      const shellEl = document.querySelector<HTMLElement>('.shell')
      if (!el || !shellEl) {
        return { found: false, contrastRatio: 0, borderColor: '', canvasBg: '', hasSchemeDark: false }
      }

      const elStyle = window.getComputedStyle(el)
      const shellStyle = window.getComputedStyle(shellEl)
      const borderColorStr = elStyle.getPropertyValue(toKebab(prop))
      const elementBgStr = elStyle.backgroundColor
      const canvasBgStr = shellStyle.backgroundColor

      const borderRgba = parseRgba(borderColorStr)
      const elementBgRgba = parseRgba(elementBgStr)
      const canvasBgRgba = parseRgba(canvasBgStr)
      if (!borderRgba || !elementBgRgba || !canvasBgRgba) {
        return { found: false, contrastRatio: 0, borderColor: borderColorStr, canvasBg: canvasBgStr, hasSchemeDark: false }
      }

      // Composite semi-transparent border over element's own background to get rendered border color
      const fg =
        borderRgba.a < 1
          ? {
              r: Math.round(borderRgba.a * borderRgba.r + (1 - borderRgba.a) * elementBgRgba.r),
              g: Math.round(borderRgba.a * borderRgba.g + (1 - borderRgba.a) * elementBgRgba.g),
              b: Math.round(borderRgba.a * borderRgba.b + (1 - borderRgba.a) * elementBgRgba.b),
            }
          : borderRgba

      const L_border = lum(fg.r, fg.g, fg.b)
      const L_canvas = lum(canvasBgRgba.r, canvasBgRgba.g, canvasBgRgba.b)
      const ratio = (Math.max(L_border, L_canvas) + 0.05) / (Math.min(L_border, L_canvas) + 0.05)

      return {
        found: true,
        contrastRatio: ratio,
        borderColor: borderColorStr,
        canvasBg: canvasBgStr,
        hasSchemeDark: document.documentElement.classList.contains('scheme-dark'),
      }
    },
    { sel: elementSel, prop: borderProp },
  )
}

// ─── AC-1: Border contrast in dark mode ──────────────────────────────────────

test.describe('TestFromAC_DarkModeBorderContrast', () => {
  /**
   * AC-1 Test 1 — .shell__sidecar left border has visible non-transparent border in dark mode.
   *
   * .shell__sidecar has border-left: 1px solid var(--p-color-contrast-low) (Shell.css) and
   * border-t via Tailwind (Shell.tsx). The border must be non-transparent.
   *
   * Falsifiable: FAILS if border-left-width = 0 or border-color = rgba(0,0,0,0).
   */
  // AC-1 Test 1 (sidecar border) PASSED — pre-satisfied by migration (#1614–#1618).
  // Shell.css already has border-left: 1px solid var(--p-color-contrast-low) on .shell__sidecar.
  // Removed per w-tdd-red §5 (passes against current code).

  /**
   * AC-1 Test 2 — .shell__nav-rail must have a right border separating it from the workspace in dark mode.
   *
   * RED: .shell__nav-rail currently has NO border-right. In dark mode, surface-to-canvas
   * background contrast ≈ 1.16:1 (below 1.3:1 threshold). Without a border, the nav-rail
   * is not visually separated from the workspace to the required 1.3:1 contrast level.
   *
   * Builder fix: add border-right: 1px solid var(--p-color-contrast-low) to .shell__nav-rail in Shell.css.
   *
   * Falsifiable:
   *   - FAILS (RED): border-right-width = 0 → no visual border → separation < 1.3:1.
   *   - PASSES (GREEN): border-right-width > 0 AND border-right-color != transparent.
   */
  test(
    'AC-1: shell__nav-rail must have a right border providing >= 1.3:1 visual separation in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await ensurePDSTokens(page, 'dark')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await page.evaluate(() => {
        const navRail = document.querySelector('.shell__nav-rail') as HTMLElement | null
        const workspace = document.querySelector('.shell__workspace') as HTMLElement | null
        if (!navRail || !workspace) {
          return {
            found: false,
            borderWidth: 0,
            borderColor: '',
            navRailBg: '',
            workspaceBg: '',
            hasSchemeDark: false,
          }
        }
        const navStyle = window.getComputedStyle(navRail)
        const wsStyle = window.getComputedStyle(workspace)
        return {
          found: true,
          borderWidth: parseFloat(navStyle.borderRightWidth),
          borderColor: navStyle.borderRightColor,
          navRailBg: navStyle.backgroundColor,
          workspaceBg: wsStyle.backgroundColor,
          hasSchemeDark: document.documentElement.classList.contains('scheme-dark'),
        }
      })

      expect(result.found, '.shell__nav-rail and .shell__workspace must exist in the DOM').toBe(true)
      expect(
        result.hasSchemeDark,
        'html must carry .scheme-dark when dark theme is active',
      ).toBe(true)

      // Primary assertion: border must exist (FAILS in RED state — no border-right on nav-rail)
      expect(
        result.borderWidth,
        `shell__nav-rail must have border-right-width > 0 to provide >= 1.3:1 visual separation ` +
          `from the workspace in dark mode. Currently: ${result.borderWidth}px. ` +
          `Without a border, surface-to-canvas background contrast is ~1.16:1 (below 1.3:1 threshold). ` +
          `Fix: add border-right: 1px solid var(--p-color-contrast-low) to .shell__nav-rail in Shell.css.`,
      ).toBeGreaterThan(0)

      // Secondary assertion: border must not be transparent
      expect(
        result.borderColor,
        `shell__nav-rail border-right-color must not be rgba(0,0,0,0) — a transparent border ` +
          `provides no visual separation. Got: "${result.borderColor}"`,
      ).not.toBe('rgba(0, 0, 0, 0)')
    },
  )

  // AC-1 Test 3 (column border contrast) PASSED — pre-satisfied by Column.css migration.
  // Column.css already has border: 1px solid var(--p-color-contrast-low); contrast >= 1.3:1.
  // Removed per w-tdd-red §5.

  // AC-1 Test 4 (filter-panel border) PASSED — pre-satisfied by FilterPanel.css migration.
  // FilterPanel.css already has border: 1px solid var(--p-color-contrast-low).
  // Removed per w-tdd-red §5.

  /**
   * AC-1 Contrast Test A — .shell__sidecar border-left vs canvas.
   *
   * Asserts that the rendered sidecar left border achieves >= 1.3:1 WCAG contrast
   * against the shell canvas background. The border uses var(--p-color-contrast-low)
   * which is semi-transparent; it is composited over the element's own surface
   * background before the ratio is computed.
   *
   * Falsifiable: FAILS if contrastRatio < 1.3 (token resolves to value too close to canvas).
   */
  test(
    'AC-1: sidecar border-left contrast ratio >= 1.3:1 against canvas in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await ensurePDSTokens(page, 'dark')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await measureBorderContrast(page, '.shell__sidecar', 'borderLeftColor')

      expect(result.found, '.shell__sidecar must be present in the DOM').toBe(true)
      expect(result.hasSchemeDark, 'html must carry .scheme-dark in dark mode').toBe(true)
      expect(
        result.contrastRatio,
        `AC-1: .shell__sidecar border-left contrast must be >= 1.3:1 against canvas. ` +
          `Got ${result.contrastRatio.toFixed(2)}:1. ` +
          `border=${result.borderColor}, canvas=${result.canvasBg}. ` +
          `Fix: ensure .shell__sidecar border-left uses a PDS token with sufficient contrast.`,
      ).toBeGreaterThanOrEqual(1.3)
    },
  )

  /**
   * AC-1 Contrast Test B — .shell__nav-rail border-right vs canvas.
   *
   * Asserts that the rendered nav-rail right border achieves >= 1.3:1 WCAG contrast
   * against the shell canvas background. Complements the border-existence test above
   * with an explicit ratio assertion.
   *
   * Falsifiable: FAILS if border-right-color resolves to a value with contrast < 1.3:1.
   */
  test(
    'AC-1: nav-rail border-right contrast ratio >= 1.3:1 against canvas in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await ensurePDSTokens(page, 'dark')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await measureBorderContrast(page, '.shell__nav-rail', 'borderRightColor')

      expect(result.found, '.shell__nav-rail must be present in the DOM').toBe(true)
      expect(result.hasSchemeDark, 'html must carry .scheme-dark in dark mode').toBe(true)
      expect(
        result.contrastRatio,
        `AC-1: .shell__nav-rail border-right contrast must be >= 1.3:1 against canvas. ` +
          `Got ${result.contrastRatio.toFixed(2)}:1. ` +
          `border=${result.borderColor}, canvas=${result.canvasBg}. ` +
          `Fix: ensure .shell__nav-rail border-right uses a PDS token with sufficient contrast.`,
      ).toBeGreaterThanOrEqual(1.3)
    },
  )

  /**
   * AC-1 Contrast Test C — .column border vs canvas.
   *
   * Asserts that the rendered column border achieves >= 1.3:1 WCAG contrast
   * against the shell canvas background (the workspace area behind columns).
   *
   * Falsifiable: FAILS if column border-top-color contrast < 1.3:1 against canvas.
   */
  test(
    'AC-1: column border contrast ratio >= 1.3:1 against canvas in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await ensurePDSTokens(page, 'dark')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
      await page.locator('.column').first().waitFor({ state: 'visible' })

      const result = await measureBorderContrast(page, '.column', 'borderTopColor')

      expect(result.found, 'At least one .column must be present in the DOM').toBe(true)
      expect(result.hasSchemeDark, 'html must carry .scheme-dark in dark mode').toBe(true)
      expect(
        result.contrastRatio,
        `AC-1: .column border contrast must be >= 1.3:1 against canvas. ` +
          `Got ${result.contrastRatio.toFixed(2)}:1. ` +
          `border=${result.borderColor}, canvas=${result.canvasBg}. ` +
          `Fix: ensure .column border uses a PDS token with sufficient contrast.`,
      ).toBeGreaterThanOrEqual(1.3)
    },
  )

  /**
   * AC-1 Contrast Test D — .filter-panel border vs canvas.
   *
   * Asserts that the rendered filter-panel border achieves >= 1.3:1 WCAG contrast
   * against the shell canvas background. The filter panel is conditionally rendered
   * and requires opening the filter toggle before measurement.
   *
   * Falsifiable: FAILS if .filter-panel border-top-color contrast < 1.3:1 against canvas.
   */
  test(
    'AC-1: filter-panel border contrast ratio >= 1.3:1 against canvas in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await ensurePDSTokens(page, 'dark')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      // FilterPanel is conditionally rendered — open the filter toggle first
      await page.click('[data-testid="filter-toggle"]')
      await page.locator('#filter-panel').waitFor({ state: 'visible', timeout: 4_000 })

      const result = await measureBorderContrast(page, '.filter-panel', 'borderTopColor')

      expect(
        result.found,
        '.filter-panel must be present in the DOM after opening filter toggle',
      ).toBe(true)
      expect(result.hasSchemeDark, 'html must carry .scheme-dark in dark mode').toBe(true)
      expect(
        result.contrastRatio,
        `AC-1: .filter-panel border contrast must be >= 1.3:1 against canvas. ` +
          `Got ${result.contrastRatio.toFixed(2)}:1. ` +
          `border=${result.borderColor}, canvas=${result.canvasBg}. ` +
          `Fix: ensure .filter-panel border uses a PDS token with sufficient contrast.`,
      ).toBeGreaterThanOrEqual(1.3)
    },
  )
})

// ─── AC-3: Border color differs between light and dark schemes ────────────────
// AC-3 tests for sidecar + column scheme-switch PASSED (removed per w-tdd-red §5).
// PDS light-dark() token switching is active for already-bordered elements.
// The remaining failing test targets .shell__nav-rail which has no border yet.

test.describe('TestFromAC_DarkModeBorderSchemeSwitch', () => {
  /**
   * AC-3 — .shell__nav-rail must have a visible border in both dark and light mode.
   *
   * RED: .shell__nav-rail currently has no border-right. Once the builder adds a border
   * (fix for AC-1), this test verifies the border uses a token that switches between schemes.
   *
   * Falsifiable:
   *   - FAILS (RED): border-right-width = 0 in dark mode → no border to compare.
   *   - PASSES (GREEN): border exists in both modes and border-colors differ.
   */
  test(
    'AC-3: shell__nav-rail has a visible border in both dark and light mode (scheme-switch forward guard)',
    async ({ page }) => {
      // ── Dark page ──────────────────────────────────────────────────────────
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await ensurePDSTokens(page, 'dark')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const darkBorderWidth = await page.evaluate(() => {
        const el = document.querySelector('.shell__nav-rail') as HTMLElement | null
        if (!el) return -1
        return parseFloat(window.getComputedStyle(el).borderRightWidth)
      })

      // Primary: border must exist in dark mode (FAILS in RED state)
      expect(
        darkBorderWidth,
        `.shell__nav-rail must have border-right-width > 0 in dark mode. ` +
          `Got: ${darkBorderWidth}px. The border is required for scheme-switch verification (AC-3) ` +
          `and visual separation (AC-1). Fix: add border-right to .shell__nav-rail in Shell.css.`,
      ).toBeGreaterThan(0)

      // ── Light page ─────────────────────────────────────────────────────────
      const lightPage = await page.context().newPage()
      try {
        await lightPage.addInitScript(() => {
          localStorage.setItem('owlbear-theme', 'light')
        })
        await stubApis(lightPage)
        await lightPage.goto('/')
        await ensurePDSTokens(lightPage, 'light')
        await lightPage.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

        const lightBorderWidth = await lightPage.evaluate(() => {
          const el = document.querySelector('.shell__nav-rail') as HTMLElement | null
          if (!el) return -1
          return parseFloat(window.getComputedStyle(el).borderRightWidth)
        })

        expect(
          lightBorderWidth,
          `.shell__nav-rail must have border-right-width > 0 in light mode as well. Got: ${lightBorderWidth}px.`,
        ).toBeGreaterThan(0)
      } finally {
        await lightPage.close()
      }
    },
  )

  /**
   * AC-3 Color Test — sidecar and nav-rail computed border colors differ between schemes.
   *
   * Asserts that var(--p-color-contrast-low) resolves to different color values in dark vs
   * light mode on at least 2 structural border elements (sidecar border-left + nav-rail
   * border-right). This confirms that PDS light-dark() token switching is active and that
   * the border color is not a fixed value identical across schemes.
   *
   * Falsifiable: FAILS if the computed border color is the same string in dark and light
   * modes for either element — indicating the token does not switch between schemes.
   */
  test(
    'AC-3: sidecar and nav-rail computed border colors differ between dark and light schemes (>= 2 elements)',
    async ({ page }) => {
      // ── Dark-mode border colors ────────────────────────────────────────────
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await ensurePDSTokens(page, 'dark')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const darkColors = await page.evaluate(() => {
        const sidecar = document.querySelector<HTMLElement>('.shell__sidecar')
        const navRail = document.querySelector<HTMLElement>('.shell__nav-rail')
        return {
          sidecarFound: !!sidecar,
          navRailFound: !!navRail,
          sidecar: sidecar ? window.getComputedStyle(sidecar).getPropertyValue('border-left-color') : '',
          navRail: navRail ? window.getComputedStyle(navRail).getPropertyValue('border-right-color') : '',
        }
      })

      expect(darkColors.sidecarFound, '.shell__sidecar must exist in DOM (dark page)').toBe(true)
      expect(darkColors.navRailFound, '.shell__nav-rail must exist in DOM (dark page)').toBe(true)

      // ── Light-mode border colors ───────────────────────────────────────────
      const lightPage = await page.context().newPage()
      try {
        await lightPage.addInitScript(() => {
          localStorage.setItem('owlbear-theme', 'light')
        })
        await stubApis(lightPage)
        await lightPage.goto('/')
        await ensurePDSTokens(lightPage, 'light')
        await lightPage.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

        const lightColors = await lightPage.evaluate(() => {
          const sidecar = document.querySelector<HTMLElement>('.shell__sidecar')
          const navRail = document.querySelector<HTMLElement>('.shell__nav-rail')
          return {
            sidecar: sidecar ? window.getComputedStyle(sidecar).getPropertyValue('border-left-color') : '',
            navRail: navRail ? window.getComputedStyle(navRail).getPropertyValue('border-right-color') : '',
          }
        })

        // Element 1: sidecar — border-left-color must differ between schemes
        expect(
          darkColors.sidecar,
          `AC-3: .shell__sidecar border-left-color must differ between dark and light schemes. ` +
            `Dark: "${darkColors.sidecar}", Light: "${lightColors.sidecar}". ` +
            `Both use var(--p-color-contrast-low) — its light-dark() pair must produce different rendered values.`,
        ).not.toBe(lightColors.sidecar)

        // Element 2: nav-rail — border-right-color must differ between schemes (>= 2 required by AC-3)
        expect(
          darkColors.navRail,
          `AC-3: .shell__nav-rail border-right-color must differ between dark and light schemes. ` +
            `Dark: "${darkColors.navRail}", Light: "${lightColors.navRail}". ` +
            `Both use var(--p-color-contrast-low) — its light-dark() pair must produce different rendered values.`,
        ).not.toBe(lightColors.navRail)
      } finally {
        await lightPage.close()
      }
    },
  )
})

// ─── AC-4: Card chip border resolves to a defined value in both schemes ───────
// AC-4 tests PASSED — Card.css migration (#1614–#1618) replaced --pds-border-subtle
// with var(--p-color-contrast-low) which resolves correctly in both schemes.
// All AC-4 tests removed per w-tdd-red §5 (pass against current code).
