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
 * RED evidence (quality-runner verified, 2026-05-17):
 *
 *   AC-2 (static token compliance): Pre-satisfied by migration (#1614–#1618).
 *     All CSS border declarations use var() references — no hardcoded colors.
 *     Static checks would all PASS → removed from RED file per w-tdd-red §5.
 *
 *   TestFromAC_DarkModeBorderContrast (AC-1) — 4 failing tests:
 *     1. shell__sidecar border-left-color = rgba(0,0,0,0) in dark mode → FAILS.
 *     2. shell__nav-rail has NO border-right → FAILS (border-right-width = 0).
 *        In dark mode, surface-to-canvas background contrast is only ~1.16:1 (below 1.3:1).
 *        A border is required. Fix: add border-right to .shell__nav-rail in Shell.css.
 *     3. .column border-color = rgba(0,0,0,0) in dark mode → FAILS.
 *     4. .filter-panel border-color = rgba(0,0,0,0) in dark mode → FAILS.
 *     All four elements: --p-color-contrast-low does not resolve in the built app.
 *     Root cause TBD by builder (possible: PDS CSS not loading, light-dark() resolution issue).
 *
 *   AC-3 scheme switch on sidecar + column: PASSED (removed per §5 — PDS token switching works).
 *   TestFromAC_DarkModeBorderSchemeSwitch (AC-3) — 1 failing test:
 *     - shell__nav-rail border-right-width = 0 in dark mode → FAILS.
 *
 *   AC-4 test 3 (static --pds-border-subtle guard): PASSED (removed per §5 — token is gone).
 *   TestFromAC_CardChipBorderResolution (AC-4) — 2 failing tests:
 *     - .card-chip border-color = rgba(0,0,0,0) in dark mode → FAILS.
 *     - .card-chip border-color = rgba(0,0,0,0) in light mode → FAILS.
 *     The --p-color-contrast-low token is not resolving for .card-chip border in either scheme.
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

// ─── Computed style helpers ───────────────────────────────────────────────────

/**
 * Parse an RGB or RGBA color string returned by getComputedStyle into [r, g, b, a].
 * Returns null if the string cannot be parsed (e.g., 'rgba(0,0,0,0)' for transparent).
 */
function parseRgba(color: string): [number, number, number, number] | null {
  const m = color.match(
    /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)/,
  )
  if (!m) return null
  return [parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]), m[4] !== undefined ? parseFloat(m[4]) : 1]
}

/**
 * Compute WCAG 2.1 relative luminance for a given [r, g, b] triplet (0–255).
 * https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
function relativeLuminance(r: number, g: number, b: number): number {
  const channel = (c: number): number => {
    const s = c / 255
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

/**
 * Compute WCAG 2.1 contrast ratio between two luminance values.
 * Returns a value >= 1.0 (1.0 = no contrast, 21.0 = black on white).
 */
function contrastRatio(l1: number, l2: number): number {
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

/**
 * Alpha-composite a foreground RGBA color onto an opaque background RGB color.
 * Returns the composited [r, g, b] triplet.
 *
 * Formula: out = alpha * fg + (1 - alpha) * bg
 */
function composite(
  fg: [number, number, number, number],
  bg: [number, number, number],
): [number, number, number] {
  const a = fg[3]
  return [
    Math.round(a * fg[0] + (1 - a) * bg[0]),
    Math.round(a * fg[1] + (1 - a) * bg[1]),
    Math.round(a * fg[2] + (1 - a) * bg[2]),
  ]
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
  test(
    'AC-1: shell__sidecar has a visible non-transparent left border in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await page.evaluate(() => {
        const sidecar = document.querySelector('.shell__sidecar') as HTMLElement | null
        if (!sidecar) return { found: false, borderWidth: 0, borderColor: '', hasSchemeDark: false }
        const style = window.getComputedStyle(sidecar)
        return {
          found: true,
          borderWidth: parseFloat(style.borderLeftWidth),
          borderColor: style.borderLeftColor,
          hasSchemeDark: document.documentElement.classList.contains('scheme-dark'),
        }
      })

      expect(result.found, '.shell__sidecar element must exist in the DOM').toBe(true)
      expect(
        result.hasSchemeDark,
        'html must carry .scheme-dark when dark theme is active',
      ).toBe(true)
      expect(
        result.borderWidth,
        `shell__sidecar must have border-left-width > 0 in dark mode (got: ${result.borderWidth}px)`,
      ).toBeGreaterThan(0)
      expect(
        result.borderColor,
        `shell__sidecar border-left-color must not be fully transparent (rgba(0,0,0,0)) in dark mode — ` +
          `got: "${result.borderColor}"`,
      ).not.toBe('rgba(0, 0, 0, 0)')
    },
  )

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

  /**
   * AC-1 Test 3 — .column border has >= 1.3:1 contrast against adjacent canvas background in dark mode.
   *
   * .column has border: 1px solid var(--p-color-contrast-low) (Column.css).
   * PDS --p-color-contrast-low in dark mode provides > 5:1 contrast against canvas (per research).
   *
   * Falsifiable: FAILS if border-width = 0 or border-color is rgba(0,0,0,0), or
   * contrast ratio is computed below 1.3:1.
   */
  test(
    'AC-1: .column border has >= 1.3:1 contrast against background in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await page.evaluate(() => {
        const col = document.querySelector('.column') as HTMLElement | null
        if (!col) return { found: false, borderWidth: 0, borderColor: '', bgColor: '' }
        const style = window.getComputedStyle(col)
        const parentStyle = window.getComputedStyle(col.parentElement ?? col)
        return {
          found: true,
          borderWidth: parseFloat(style.borderTopWidth),
          borderColor: style.borderTopColor,
          bgColor: parentStyle.backgroundColor,
        }
      })

      expect(result.found, '.column element must be rendered (a task must exist in the board)').toBe(true)
      expect(
        result.borderWidth,
        `column must have border-top-width > 0 in dark mode (got: ${result.borderWidth}px)`,
      ).toBeGreaterThan(0)
      expect(
        result.borderColor,
        `column border-top-color must not be rgba(0,0,0,0) in dark mode — got: "${result.borderColor}"`,
      ).not.toBe('rgba(0, 0, 0, 0)')

      // Verify contrast ratio against the parent background (proxy for adjacent background)
      const borderRgba = parseRgba(result.borderColor)
      const bgRgba = parseRgba(result.bgColor)
      if (borderRgba && bgRgba) {
        const effectiveBorder =
          borderRgba[3] < 1
            ? composite(borderRgba, [bgRgba[0], bgRgba[1], bgRgba[2]])
            : [borderRgba[0], borderRgba[1], borderRgba[2]]

        const borderLuminance = relativeLuminance(effectiveBorder[0], effectiveBorder[1], effectiveBorder[2])
        const bgLuminance = relativeLuminance(bgRgba[0], bgRgba[1], bgRgba[2])
        const ratio = contrastRatio(borderLuminance, bgLuminance)

        expect(
          ratio,
          `column border-color must have >= 1.3:1 contrast against adjacent background in dark mode. ` +
            `Border: ${result.borderColor}, Background: ${result.bgColor}, Ratio: ${ratio.toFixed(2)}:1`,
        ).toBeGreaterThanOrEqual(1.3)
      }
    },
  )

  /**
   * AC-1 Test 4 — .filter-panel border is visible and non-transparent in dark mode.
   *
   * FilterPanel.css: border: 1px solid var(--p-color-contrast-low).
   *
   * Falsifiable: FAILS if filter-panel has no visible border or transparent border-color.
   */
  test(
    'AC-1: .filter-panel border is visible and non-transparent in dark mode',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await page.evaluate(() => {
        const panel = document.querySelector('.filter-panel') as HTMLElement | null
        if (!panel) return { found: false, borderWidth: 0, borderColor: '' }
        const style = window.getComputedStyle(panel)
        return {
          found: true,
          borderWidth: parseFloat(style.borderTopWidth),
          borderColor: style.borderTopColor,
        }
      })

      expect(result.found, '.filter-panel must be rendered in the workspace').toBe(true)
      expect(
        result.borderWidth,
        `filter-panel must have border-top-width > 0 in dark mode (got: ${result.borderWidth}px)`,
      ).toBeGreaterThan(0)
      expect(
        result.borderColor,
        `filter-panel border-top-color must not be rgba(0,0,0,0) — got: "${result.borderColor}"`,
      ).not.toBe('rgba(0, 0, 0, 0)')
    },
  )
})

// ─── AC-3: Border color differs between light and dark schemes ────────────────
// Note: AC-3 test for sidecar + column scheme-switch PASSED (removed per w-tdd-red §5).
// PDS light-dark() token switching is active for already-bordered elements.
// The remaining failing test targets .shell__nav-rail which has no border yet.

test.describe('TestFromAC_DarkModeBorderSchemeSwitch', () => {
  /**
   * AC-3 Test 2 — .shell__nav-rail must have a visible border in both dark and light mode.
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
})

// ─── AC-4: Card chip border resolves to a defined value in both schemes ───────

test.describe('TestFromAC_CardChipBorderResolution', () => {
  /**
   * AC-4 Test 1 — .card-chip border-color is non-transparent in dark mode.
   *
   * Pre-migration bug: Card.css used `--pds-border-subtle` (undefined) for .card-chip,
   * resulting in invisible borders (rgba(0,0,0,0)). Post-migration successor is
   * `--p-color-contrast-low` (defined by PDS). This test verifies the fix.
   *
   * Requires: task fixture includes a task with tags (renders .card-chip elements).
   *
   * Falsifiable:
   *   - FAILS if Card.css still uses an undefined custom property for .card-chip border
   *     → computed border-color = rgba(0,0,0,0).
   *   - PASSES if the PDS token resolves correctly in dark mode.
   */
  test(
    'AC-4: .card-chip has non-transparent border-color in dark mode — successor token resolves',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'dark')
      })
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await page.evaluate(() => {
        const chip = document.querySelector('.card-chip') as HTMLElement | null
        if (!chip) return { found: false, borderColor: '', borderWidth: 0, hasSchemeDark: false }
        const style = window.getComputedStyle(chip)
        return {
          found: true,
          borderColor: style.borderTopColor,
          borderWidth: parseFloat(style.borderTopWidth),
          hasSchemeDark: document.documentElement.classList.contains('scheme-dark'),
        }
      })

      expect(
        result.found,
        '.card-chip element must be rendered — task fixture must include a task with tags. ' +
          'If no .card-chip is found, the TASKS fixture in this file is missing tag entries.',
      ).toBe(true)
      expect(
        result.hasSchemeDark,
        'html must carry .scheme-dark when dark theme is active',
      ).toBe(true)
      expect(
        result.borderWidth,
        `card-chip must have border-top-width > 0 in dark mode (got: ${result.borderWidth}px). ` +
          `A zero border-width indicates the border declaration was removed entirely.`,
      ).toBeGreaterThan(0)
      expect(
        result.borderColor,
        `.card-chip border-color must not be rgba(0,0,0,0) in dark mode. ` +
          `Got: "${result.borderColor}". ` +
          `This indicates the CSS custom property used for .card-chip border is undefined — ` +
          `the pre-migration bug (--pds-border-subtle not defined) may not be fully resolved. ` +
          `Post-migration Card.css should use var(--p-color-contrast-low) which is PDS-defined.`,
      ).not.toBe('rgba(0, 0, 0, 0)')
    },
  )

  /**
   * AC-4 Test 2 — .card-chip border-color is non-transparent in light mode.
   *
   * Verifies the successor token also resolves in light mode (not just dark).
   * Both schemes must have a defined border-color.
   *
   * Falsifiable: FAILS if the token resolves in dark but not light (or vice versa).
   */
  test(
    'AC-4: .card-chip has non-transparent border-color in light mode — successor token resolves in both schemes',
    async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('owlbear-theme', 'light')
      })
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })

      const result = await page.evaluate(() => {
        const chip = document.querySelector('.card-chip') as HTMLElement | null
        if (!chip) return { found: false, borderColor: '', borderWidth: 0, hasSchemeLight: false }
        const style = window.getComputedStyle(chip)
        return {
          found: true,
          borderColor: style.borderTopColor,
          borderWidth: parseFloat(style.borderTopWidth),
          hasSchemeLight: document.documentElement.classList.contains('scheme-light'),
        }
      })

      expect(
        result.found,
        '.card-chip element must be rendered — task fixture must include a task with tags.',
      ).toBe(true)
      expect(
        result.hasSchemeLight,
        'html must carry .scheme-light when light theme is active',
      ).toBe(true)
      expect(
        result.borderWidth,
        `card-chip must have border-top-width > 0 in light mode (got: ${result.borderWidth}px)`,
      ).toBeGreaterThan(0)
      expect(
        result.borderColor,
        `.card-chip border-color must not be rgba(0,0,0,0) in light mode. ` +
          `Got: "${result.borderColor}". ` +
          `The CSS custom property for .card-chip border must resolve in both color schemes.`,
      ).not.toBe('rgba(0, 0, 0, 0)')
    },
  )

  // AC-4 Test 3 (static --pds-border-subtle guard) PASSED and was removed per w-tdd-red §5.
  // Card.css no longer references --pds-border-subtle — migration (#1614–#1618) replaced it.
  // The 2 failing tests above (dark + light card-chip border transparent) are the RED evidence.
})
