/**
 * Task #1642 — P1-02: Nav-rail tab navigation — dynamic buttons from route config
 *
 * AC1: Nav-rail element has role="navigation" and renders one button per route
 *      config entry; each button triggers useNavigate() to its route path on click.
 * AC2: Active route's nav-rail button has aria-current="page"; inactive buttons do
 *      not have aria-current; switching routes updates aria-current accordingly.
 * AC3: Validation gate: adding a third entry to the route config array produces a
 *      third nav-rail button that navigates to the new route path.
 *
 * routeConfig is mocked with THREE entries (/, /decisions, /test-route) throughout
 * this file. A hardcoded 2-button nav-rail fails all button-count assertions, proving
 * the implementation must be data-driven (AC3 validation gate).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// Mutable 3-entry routeConfig array — Shell.tsx holds a reference to this array;
// mutating it in-place per test is visible at render time without module re-evaluation.
const routeConfigMut = vi.hoisted(() => {
  function Stub() {
    return null
  }
  return [
    { path: '/', label: 'Kanban', icon: 'kanban', component: Stub },
    { path: '/decisions', label: 'Decisions', icon: 'decisions', component: Stub },
    { path: '/test-route', label: 'Test Route', icon: 'test-route', component: Stub },
  ]
})

vi.mock('../routes', () => ({
  routeConfig: routeConfigMut,
}))

// ─── Fetch stub ───────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((_url: string, init?: RequestInit) =>
      new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      }),
    ),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Updated to current MemoryRouter location after every render/re-render. */
let capturedPathname = '/'

function LocationCapture(): null {
  capturedPathname = useLocation().pathname
  return null
}

function renderShell(initialRoute = '/') {
  capturedPathname = initialRoute
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[initialRoute]}>
        <CockpitProvider>
          <Shell />
          <LocationCapture />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

function rail(container: HTMLElement): Element {
  const el = container.querySelector('[data-region="nav-rail"]')
  if (!el) throw new Error('[data-region="nav-rail"] not found')
  return el
}

function navBtn(navRail: Element, surface: string): HTMLElement {
  const el = navRail.querySelector<HTMLElement>(`[data-surface="${surface}"]`)
  if (!el) throw new Error(`button [data-surface="${surface}"] not found in nav-rail`)
  return el
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_NavRailButtons', () => {
  // ── AC1: role="navigation" + one button per routeConfig entry ─────────────

  describe('AC1 — role and data-driven button rendering', () => {
    it('ac1 happy: nav-rail <nav> has explicit role="navigation" attribute', () => {
      const { container } = renderShell()
      // <nav> has implicit navigation role; AC requires the explicit attribute
      expect(rail(container).getAttribute('role')).toBe('navigation')
    })

    it('ac1 happy: nav-rail renders 3 buttons matching the mocked 3-entry routeConfig', () => {
      const { container } = renderShell()
      expect(rail(container).querySelectorAll('button[data-surface]').length).toBe(3)
    })

    it('ac1 happy: decisions nav button is present with data-surface="decisions"', () => {
      const { container } = renderShell()
      expect(rail(container).querySelector('[data-surface="decisions"]')).not.toBeNull()
    })

    it('ac1 happy: all nav-rail data-surface buttons are native <button> elements', () => {
      const { container } = renderShell()
      const navRail = rail(container)
      // Count check first — fails if fewer than 3 buttons present
      const buttons = Array.from(navRail.querySelectorAll('button[data-surface]'))
      expect(buttons.length).toBe(3)
      for (const btn of buttons) {
        expect(btn.tagName).toBe('BUTTON')
      }
    })

    it('ac1 happy: clicking kanban button calls navigate("/")', () => {
      // Start at /decisions so a successful navigate('/') is observable
      const { container } = renderShell('/decisions')
      fireEvent.click(navBtn(rail(container), 'kanban'))
      expect(capturedPathname).toBe('/')
    })

    it('ac1 happy: clicking decisions button calls navigate("/decisions")', () => {
      const { container } = renderShell('/')
      // navBtn throws if decisions button absent → FAIL before assertion
      fireEvent.click(navBtn(rail(container), 'decisions'))
      expect(capturedPathname).toBe('/decisions')
    })

    it('ac1 edge: decisions button has an accessible label containing "decisions"', () => {
      const { container } = renderShell()
      // navBtn throws if decisions button absent → FAIL before assertion
      const btn = navBtn(rail(container), 'decisions')
      const label = btn.getAttribute('aria-label') ?? btn.textContent ?? ''
      expect(label.toLowerCase()).toContain('decisions')
    })

    it('ac1 boundary: button count equals routeConfig.length — proves data-driven rendering', () => {
      // routeConfig mocked to 3 entries; hardcoded 2-button nav yields 1 ≠ 3
      const { container } = renderShell()
      expect(rail(container).querySelectorAll('button[data-surface]').length).toBe(3)
    })
  })

  // ── AC2: aria-current tracks the active route ─────────────────────────────

  describe('AC2 — aria-current active/inactive tracking', () => {
    it('ac2 happy: on route "/", kanban button has aria-current="page"', () => {
      const { container } = renderShell('/')
      const navRail = rail(container)
      // Also verify decisions button exists (throws if absent → FAIL)
      navBtn(navRail, 'decisions')
      expect(navBtn(navRail, 'kanban').getAttribute('aria-current')).toBe('page')
    })

    it('ac2 happy: on route "/", decisions button has no aria-current', () => {
      const { container } = renderShell('/')
      // decisions button absent → throws → FAIL
      expect(navBtn(rail(container), 'decisions').hasAttribute('aria-current')).toBe(false)
    })

    it('ac2 happy: on route "/decisions", decisions button has aria-current="page"', () => {
      const { container } = renderShell('/decisions')
      // decisions button absent → throws → FAIL
      expect(navBtn(rail(container), 'decisions').getAttribute('aria-current')).toBe('page')
    })

    it('ac2 happy: on route "/decisions", kanban button has no aria-current', () => {
      const { container } = renderShell('/decisions')
      // Hardcoded kanban always has aria-current="page" → hasAttribute returns true → FAIL
      expect(navBtn(rail(container), 'kanban').hasAttribute('aria-current')).toBe(false)
    })

    it('ac2 happy: switching "/" → "/decisions" sets aria-current="page" on decisions', () => {
      const { container } = renderShell('/')
      const navRail = rail(container)
      fireEvent.click(navBtn(navRail, 'decisions'))  // throws if absent → FAIL
      expect(navBtn(navRail, 'decisions').getAttribute('aria-current')).toBe('page')
    })

    it('ac2 happy: switching "/" → "/decisions" clears aria-current from kanban', () => {
      const { container } = renderShell('/')
      const navRail = rail(container)
      fireEvent.click(navBtn(navRail, 'decisions'))  // throws if absent → FAIL
      expect(navBtn(navRail, 'kanban').hasAttribute('aria-current')).toBe(false)
    })

    it('ac2 edge: on unknown route "/unknown", no nav button has aria-current="page"', () => {
      const { container } = renderShell('/unknown')
      const navRail = rail(container)
      // Hardcoded kanban always has aria-current="page" → active.length is 1 ≠ 0 → FAIL
      const active = navRail.querySelectorAll('[data-surface][aria-current="page"]')
      expect(active.length).toBe(0)
    })

    it('ac2 boundary: aria-current is exactly "page" (not "true", not "")', () => {
      const { container } = renderShell('/decisions')
      // decisions button absent → throws → FAIL
      expect(navBtn(rail(container), 'decisions').getAttribute('aria-current')).toBe('page')
    })

    it('ac2 boundary: exactly one nav button has aria-current="page" on a known route', () => {
      const { container } = renderShell('/')
      const navRail = rail(container)
      // Button count check first — fails if count != 3
      expect(navRail.querySelectorAll('button[data-surface]').length).toBe(3)
      expect(navRail.querySelectorAll('[data-surface][aria-current="page"]').length).toBe(1)
    })
  })

  // ── AC3: validation gate — third routeConfig entry produces third button ───

  describe('AC3 — validation gate: third entry in routeConfig', () => {
    it('ac3 happy: third nav button renders with data-surface="test-route"', () => {
      const { container } = renderShell()
      expect(rail(container).querySelector('[data-surface="test-route"]')).not.toBeNull()
    })

    it('ac3 happy: clicking third nav button navigates to "/test-route"', () => {
      const { container } = renderShell('/')
      // navBtn throws if test-route button absent → FAIL
      fireEvent.click(navBtn(rail(container), 'test-route'))
      expect(capturedPathname).toBe('/test-route')
    })

    it('ac3 happy: on route "/test-route", third button has aria-current="page"', () => {
      const { container } = renderShell('/test-route')
      // navBtn throws if test-route button absent → FAIL
      expect(navBtn(rail(container), 'test-route').getAttribute('aria-current')).toBe('page')
    })

    it('ac3 happy: on "/test-route", kanban and decisions buttons have no aria-current', () => {
      const { container } = renderShell('/test-route')
      const navRail = rail(container)
      navBtn(navRail, 'test-route')  // throws if absent → FAIL
      expect(navBtn(navRail, 'kanban').hasAttribute('aria-current')).toBe(false)
      expect(navBtn(navRail, 'decisions').hasAttribute('aria-current')).toBe(false)
    })

    it('ac3 boundary: total nav-rail button count is 3, proving data-driven rendering', () => {
      // Hardcoded 2-button implementation yields 2 ≠ 3 → FAIL
      const { container } = renderShell()
      expect(rail(container).querySelectorAll('button[data-surface]').length).toBe(3)
    })
  })

  // ── AC1/AC3: falsifiability gate — proves buttons are derived from config ──
  //
  // The tests above pin the mock to exactly the same 3 icons the impl could
  // theoretically hardcode. These gate tests mutate routeConfigMut in-place
  // to use novel entries that no hardcoded impl would render, falsifying any
  // non-data-driven implementation.

  describe('AC1/AC3 — falsifiability gate: button count and surface track config entries', () => {
    // Snapshot the default 3 entries for restore after each test.
    const defaultEntries = routeConfigMut.slice()

    afterEach(() => {
      routeConfigMut.length = 0
      routeConfigMut.push(...defaultEntries)
    })

    it('ac1 falsify: 1-entry config renders exactly 1 nav button (falsifies hardcoded 3-button nav)', () => {
      routeConfigMut.length = 0
      routeConfigMut.push({ path: '/only', label: 'Only', icon: 'sentinel-1642', component: () => null })
      const { container } = renderShell()
      expect(rail(container).querySelectorAll('button[data-surface]').length).toBe(1)
    })

    it('ac1 falsify: novel sentinel-1642 button only present when config includes sentinel entry', () => {
      routeConfigMut.length = 0
      routeConfigMut.push({ path: '/s', label: 'Sentinel', icon: 'sentinel-1642', component: () => null })
      const { container } = renderShell()
      expect(rail(container).querySelector('[data-surface="sentinel-1642"]')).not.toBeNull()
    })

    it('ac3 falsify: 4-entry config renders exactly 4 nav buttons (falsifies any fixed-count nav)', () => {
      function Stub() {
        return null
      }
      routeConfigMut.push({ path: '/extra', label: 'Extra', icon: 'extra-gate-1642', component: Stub })
      const { container } = renderShell()
      expect(rail(container).querySelectorAll('button[data-surface]').length).toBe(4)
    })

    it('ac3 falsify: novel gate-1642 entry renders matching button that navigates to its path', () => {
      routeConfigMut.length = 0
      routeConfigMut.push({ path: '/', label: 'Kanban', icon: 'kanban', component: () => null })
      routeConfigMut.push({ path: '/gate-test-1642', label: 'Gate Test', icon: 'gate-1642', component: () => null })
      const { container } = renderShell()
      expect(rail(container).querySelector('[data-surface="gate-1642"]')).not.toBeNull()
      fireEvent.click(navBtn(rail(container), 'gate-1642'))
      expect(capturedPathname).toBe('/gate-test-1642')
    })
  })
})
