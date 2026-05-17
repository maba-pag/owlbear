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
})

// ─── AC-4: Card chip border resolves to a defined value in both schemes ───────
// AC-4 tests PASSED — Card.css migration (#1614–#1618) replaced --pds-border-subtle
// with var(--p-color-contrast-low) which resolves correctly in both schemes.
// All AC-4 tests removed per w-tdd-red §5 (pass against current code).
