/**
 * RED-phase Playwright E2E tests for #1606: P1-09 Shell layout — sticky header + responsive sidebar.
 *
 * All tests must FAIL against the current implementation.
 *
 * Current state (before builder implementation):
 *   AC1 — header: className="shell__status-bar", no Tailwind sticky/z-10 classes.
 *           getComputedStyle(header).position === "static" (no explicit position in CSS).
 *   AC2 — sidecar at 768–1023px: grid column = 240px (via @media rule in Shell.css).
 *           At >=1024px sidecar = 360px (GREEN already — regression guard).
 *   AC3 — Shell.css has layout property rules (display, height, overflow, position, z-index).
 *           Shell root className="shell" — no Tailwind utility classes.
 *           Header className="shell__status-bar" — no Tailwind sticky/top-0/z-10 classes.
 *
 * Expected failures (RED evidence):
 *   TestFromAC_StickyHeader — position:static → not sticky; no z-10 class on header.
 *   TestFromAC_ResponsiveSidecar — sidecar=240px at 1023px → outside 40–56px range.
 *   TestFromAC_TailwindCSSStructure — Shell.css has forbidden layout properties;
 *     shell/header have no Tailwind layout utility classes.
 *
 * API mocking: all routes stubbed via page.route() — no real backend required.
 * Proof bundle: behavioral.
 */
import * as fs from 'node:fs'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect, type Page } from '@playwright/test'

// ─── Constants ─────────────────────────────────────────────────────────────────

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

const TASKS = STATUSES.map((status, i) => ({
  id: i + 1,
  title: `Task in ${status}`,
  status,
  priority: PRIORITIES[i % PRIORITIES.length],
  updated: '2026-05-16T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}))

// ─── Shell.css path for AC3 file-content checks ────────────────────────────────

const SHELL_CSS_PATH = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
  'src',
  'Shell.css',
)

// ─── API stub helper ──────────────────────────────────────────────────────────

/**
 * Stub all API routes. Catch-all registered first (LIFO: specific routes registered
 * after take precedence per Playwright route() semantics).
 */
async function stubApis(page: Page, tasks: object[] = TASKS): Promise<void> {
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
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks, mtime: 1_747_353_600 } }),
  )
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
}

// ─── AC1: Sticky header ───────────────────────────────────────────────────────
//
// Contract: header ([data-region="status-bar"]) must have position:sticky so it
// remains visible when content below it is scrolled, with z-index >= 10 to avoid
// overlap with scrolled content.
//
// RED: .shell__status-bar has no position rule in CSS → computed position = "static".
// RED: header className = "shell__status-bar" — no Tailwind z-10 class.

test.describe('TestFromAC_StickyHeader', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="status-bar"]').waitFor({ state: 'visible' })
  })

  // RED: getComputedStyle(el).position is "static" — no position set on .shell__status-bar
  test('header has position:sticky computed style', async ({ page }) => {
    const position = await page
      .locator('[data-region="status-bar"]')
      .evaluate((el) => getComputedStyle(el).position)
    expect(position, 'status-bar must have position:sticky for robust sticky layout').toBe('sticky')
  })

  // RED: header className = "shell__status-bar" — no Tailwind z-10 class present
  test('header has Tailwind z-10 class for stacking context', async ({ page }) => {
    const classes = await page
      .locator('[data-region="status-bar"]')
      .evaluate((el) => el.className)
    expect(
      classes,
      `status-bar className "${classes}" must include Tailwind z-10 class`,
    ).toContain('z-10')
  })

})

// ─── AC2: Responsive sidecar column width ─────────────────────────────────────
//
// Contract:
//   • At viewport width < 1024px (without manual collapse): sidecar grid column
//     renders 40–56px wide (icon-strip, not full detail panel).
//   • At viewport width >= 1024px: sidecar renders approximately 360px wide.
//
// RED: Shell.css @media(768–1023px) sets grid-template-columns: 56px minmax(0,1fr) 240px
//      → sidecar = 240px at 1023px viewport — outside the 40–56px required range.
//
// Precondition: data-sidecar-collapsed must NOT be set (responsive narrow ≠ manual collapse).

test.describe('TestFromAC_ResponsiveSidecar', () => {
  // ─── at 1023px: narrow icon-strip sidecar ────────────────────────────────────

  test.describe('at 1023px viewport (below 1024px breakpoint)', () => {
    test.use({ viewport: { width: 1023, height: 800 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'visible' })
    })

    // RED: sidecar = 240px at 1023px (via @media 768–1023px rule) — fails 40–56px constraint
    test('sidecar column is 40–56px wide at 1023px without manual collapse', async ({ page }) => {
      const collapsed = await page
        .locator('.shell')
        .evaluate((el) => el.hasAttribute('data-sidecar-collapsed'))
      expect(
        collapsed,
        'data-sidecar-collapsed must NOT be set — responsive narrow is independent of manual collapse',
      ).toBe(false)

      const box = await page.locator('[data-region="sidecar"]').boundingBox()
      expect(box, 'sidecar bounding box must exist at 1023px').not.toBeNull()
      expect(
        box!.width,
        `sidecar width (${box!.width}px) must be at least 40px at 1023px`,
      ).toBeGreaterThanOrEqual(40)
      expect(
        box!.width,
        `sidecar width (${box!.width}px) must be at most 56px at 1023px`,
      ).toBeLessThanOrEqual(56)
    })

    // Boundary: 1023px is 1px below the 1024px cutoff — sidecar must be narrow, not full panel
    test('sidecar is significantly narrower than desktop width at 1023px (breakpoint boundary)', async ({
      page,
    }) => {
      const collapsed = await page
        .locator('.shell')
        .evaluate((el) => el.hasAttribute('data-sidecar-collapsed'))
      expect(collapsed, 'data-sidecar-collapsed must NOT be set for boundary test').toBe(false)

      const box = await page.locator('[data-region="sidecar"]').boundingBox()
      expect(box, 'sidecar must have a bounding box at 1023px').not.toBeNull()
      // Sidecar must NOT be full desktop width (300+px) at 1023px
      expect(
        box!.width,
        `sidecar width (${box!.width}px) must be < 100px at 1023px (icon-strip, not full panel)`,
      ).toBeLessThan(100)
    })
  })

  // ─── at 1024px: full detail panel ────────────────────────────────────────────
  //
  // GREEN already — sidecar = 360px at >=1024px in current CSS.
  // Included as regression guard: Tailwind migration must preserve desktop sidecar width.

  test.describe('at 1024px viewport (at or above 1024px breakpoint)', () => {
    test.use({ viewport: { width: 1024, height: 800 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'visible' })
    })

    // GREEN currently (regression guard): sidecar = 360px at 1024px
    test('sidecar column is approximately 360px wide at 1024px (regression guard)', async ({
      page,
    }) => {
      const collapsed = await page
        .locator('.shell')
        .evaluate((el) => el.hasAttribute('data-sidecar-collapsed'))
      expect(collapsed, 'data-sidecar-collapsed must NOT be set').toBe(false)

      const box = await page.locator('[data-region="sidecar"]').boundingBox()
      expect(box, 'sidecar bounding box must exist at 1024px').not.toBeNull()
      expect(
        box!.width,
        `sidecar width (${box!.width}px) must be approximately 360px at 1024px`,
      ).toBeGreaterThanOrEqual(340)
      expect(
        box!.width,
        `sidecar width (${box!.width}px) must be approximately 360px at 1024px`,
      ).toBeLessThanOrEqual(380)
    })
  })
})

// ─── AC3: Tailwind migration — Shell.css structure + layout class enforcement ──
//
// Contract:
//   • Shell layout uses Tailwind utility classes for all layout properties.
//   • Shell.css retains only grid-template-areas definitions and CSS custom-property
//     aliases — no layout property rules remain in CSS.
//   • No inline style={{}} attributes for layout properties on shell elements.
//
// RED (DOM checks): shell/header className have no Tailwind layout classes.
// RED (file checks): Shell.css contains display, height, overflow, position, z-index rules.

test.describe('TestFromAC_TailwindCSSStructure', () => {
  // ─── DOM: Tailwind classes on shell elements ──────────────────────────────────

  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="status-bar"]').waitFor({ state: 'visible' })
  })

  // RED: shell root className="shell" — no Tailwind 'grid' class
  test('shell root element has Tailwind grid class (display:grid via Tailwind)', async ({
    page,
  }) => {
    const classes = await page.locator('.shell').evaluate((el) => el.className)
    expect(
      classes,
      `shell root className "${classes}" must include Tailwind 'grid' class`,
    ).toContain('grid')
  })

  // RED: shell root has no Tailwind 'h-screen' class (height:100vh in CSS only)
  test('shell root element has Tailwind h-screen class (height:100vh via Tailwind)', async ({
    page,
  }) => {
    const classes = await page.locator('.shell').evaluate((el) => el.className)
    expect(
      classes,
      `shell root className "${classes}" must include Tailwind 'h-screen' class`,
    ).toContain('h-screen')
  })

  // RED: header has no Tailwind 'sticky' class (position:sticky moved from CSS to Tailwind)
  test('header element has Tailwind sticky class', async ({ page }) => {
    const classes = await page
      .locator('[data-region="status-bar"]')
      .evaluate((el) => el.className)
    expect(
      classes,
      `status-bar className "${classes}" must include Tailwind 'sticky' class`,
    ).toContain('sticky')
  })

  // RED: header has no Tailwind 'top-0' class
  test('header element has Tailwind top-0 class', async ({ page }) => {
    const classes = await page
      .locator('[data-region="status-bar"]')
      .evaluate((el) => el.className)
    expect(
      classes,
      `status-bar className "${classes}" must include Tailwind 'top-0' class`,
    ).toContain('top-0')
  })

  // ─── File: Shell.css must not contain layout property rules ──────────────────
  //
  // These run in Node.js context — no page parameter needed.
  // RED: Shell.css currently contains all of the following layout properties.

  // RED: .shell { display: grid } → 'display:' present in current Shell.css
  test('Shell.css does not contain display property rules', async () => {
    const css = fs.readFileSync(SHELL_CSS_PATH, 'utf-8')
    expect(
      css,
      'Shell.css must not contain "display:" rules (move display to Tailwind)',
    ).not.toMatch(/^\s*display\s*:/m)
  })

  // RED: .shell { height: 100vh } → 'height:' present in current Shell.css
  test('Shell.css does not contain height property rules', async () => {
    const css = fs.readFileSync(SHELL_CSS_PATH, 'utf-8')
    expect(
      css,
      'Shell.css must not contain "height:" rules (move height to Tailwind)',
    ).not.toMatch(/^\s*height\s*:/m)
  })

  // RED: .shell__workspace { overflow: auto } and others → 'overflow' present in Shell.css
  test('Shell.css does not contain overflow property rules', async () => {
    const css = fs.readFileSync(SHELL_CSS_PATH, 'utf-8')
    expect(
      css,
      'Shell.css must not contain "overflow" rules (move overflow to Tailwind)',
    ).not.toMatch(/^\s*overflow(-[xy])?\s*:/m)
  })

  // RED: .shell__mobile-sheet--open { position: fixed } → 'position:' present in Shell.css
  test('Shell.css does not contain position property rules', async () => {
    const css = fs.readFileSync(SHELL_CSS_PATH, 'utf-8')
    expect(
      css,
      'Shell.css must not contain "position:" rules (move position to Tailwind)',
    ).not.toMatch(/^\s*position\s*:/m)
  })

  // RED: .shell__mobile-sheet--open { z-index: 20 } → 'z-index:' present in Shell.css
  test('Shell.css does not contain z-index property rules', async () => {
    const css = fs.readFileSync(SHELL_CSS_PATH, 'utf-8')
    expect(
      css,
      'Shell.css must not contain "z-index:" rules (move z-index to Tailwind)',
    ).not.toMatch(/^\s*z-index\s*:/m)
  })

  // ─── File: Shell.css remaining banned property families (padding) ─────────────
  //
  // AC3 bans 8 CSS property families. Previous tests covered: display, height,
  // overflow, position, z-index. Width and gap are already compliant (no rules
  // present in Shell.css). Padding still has a violation: #shell-sidecar-content.

  // RED: #shell-sidecar-content { padding: var(--p-spacing-static-md) } still in Shell.css
  test('Shell.css does not contain padding property rules', async () => {
    const css = fs.readFileSync(SHELL_CSS_PATH, 'utf-8')
    expect(
      css,
      'Shell.css must not contain "padding:" rules (move padding to Tailwind)',
    ).not.toMatch(/^\s*padding(-\w+)?\s*:/m)
  })
})
