/**
 * Task #1646 — P2-03: Pending count badge on nav-rail decisions button
 *
 * AC1: Nav-rail decisions button ([data-surface="decisions"]) renders a child element
 *      with data-testid="nav-badge" displaying the numeric pending DR count when
 *      useDRState().count > 0.
 * AC2: Badge element (data-testid="nav-badge") is absent from DOM when pending DR
 *      count is 0.
 * AC3: When badge is visible, button aria-label includes the pending count (e.g.
 *      "Decisions (3 pending)"); when count is 0, aria-label is "Decisions".
 *
 * RED phase: Shell.tsx has no badge rendering code → all AC1/AC3 assertions fail.
 * AC2 assertions fail because count=0 is the default — badge must be conditionally
 * absent and aria-label must be "Decisions" exactly (not "Decisions (0 pending)").
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, type RenderResult } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import { usePendingDRs } from '../hooks/usePendingDRs'
import type { UsePendingDRsResult } from '../hooks/usePendingDRs'

// ─── Module mocks ──────────────────────────────────────────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// Two-entry routeConfig: kanban + decisions (sufficient to prove badge specificity)
vi.mock('../routes', () => {
  function Stub() {
    return null
  }
  return {
    routeConfig: [
      { path: '/', label: 'Kanban', icon: 'kanban', component: Stub },
      { path: '/decisions', label: 'Decisions', icon: 'decisions', component: Stub },
    ],
  }
})

// Default: count=0 — overridden per-test via setDRCount()
vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn((): UsePendingDRsResult => ({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

// ─── Fetch stub ────────────────────────────────────────────────────────────────

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
  // Restore default count=0 before each test
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// ─── Helpers ───────────────────────────────────────────────────────────────────

function setDRCount(count: number): void {
  vi.mocked(usePendingDRs).mockReturnValue({
    count,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })
}

function renderShell(initialRoute = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[initialRoute]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

function navRail(container: HTMLElement): Element {
  const el = container.querySelector('[data-region="nav-rail"]')
  if (!el) throw new Error('[data-region="nav-rail"] not found')
  return el
}

function decisionsBtn(container: HTMLElement): HTMLElement {
  const el = container.querySelector<HTMLElement>('[data-surface="decisions"]')
  if (!el) throw new Error('[data-surface="decisions"] not found')
  return el
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe('NavBadge', () => {
  // ── AC1: Badge renders when count > 0 ──────────────────────────────────────

  describe('AC1 — badge child element present inside decisions button when count > 0', () => {
    it('ac1 happy: badge element [data-testid="nav-badge"] present in decisions button when count=3', () => {
      setDRCount(3)
      const { container } = renderShell()
      const btn = decisionsBtn(container)
      expect(btn.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
    })

    it('ac1 happy: badge text content equals the numeric count "3"', () => {
      setDRCount(3)
      const { container } = renderShell()
      const btn = decisionsBtn(container)
      const badge = btn.querySelector('[data-testid="nav-badge"]')
      expect(badge?.textContent?.trim()).toBe('3')
    })

    it('ac1 boundary: badge present at count=1 (minimum positive threshold)', () => {
      setDRCount(1)
      const { container } = renderShell()
      const btn = decisionsBtn(container)
      expect(btn.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
    })

    it('ac1 boundary: badge text content equals "1" at minimum positive count', () => {
      setDRCount(1)
      const { container } = renderShell()
      const btn = decisionsBtn(container)
      const badge = btn.querySelector('[data-testid="nav-badge"]')
      expect(badge?.textContent?.trim()).toBe('1')
    })

    it('ac1 edge: badge is a descendant of [data-surface="decisions"], not of kanban button', () => {
      setDRCount(5)
      const { container } = renderShell()
      const btn = decisionsBtn(container)
      // Badge inside decisions button
      expect(btn.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
      // Badge NOT inside kanban button
      const kanbanBtn = container.querySelector('[data-surface="kanban"]')
      expect(kanbanBtn?.querySelector('[data-testid="nav-badge"]')).toBeNull()
    })

    it('ac1 edge: badge element lives inside the nav-rail, not elsewhere in DOM', () => {
      setDRCount(2)
      const { container } = renderShell()
      const rail = navRail(container)
      // Badge found inside nav-rail
      expect(rail.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
    })
  })

  // ── AC2: Badge absent when count=0 ────────────────────────────────────────
  //
  // All AC2 tests use rerender to transition from count>0 → count=0.
  // This proves conditional rendering (badge disappears) rather than trivially
  // asserting absence-before-implementation. The count>0 assertion fails in RED.

  describe('AC2 — badge element absent from DOM when count is 0', () => {
    function rerenderShell(view: RenderResult, initialRoute = '/') {
      view.rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={[initialRoute]}>
            <CockpitProvider>
              <Shell />
            </CockpitProvider>
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )
    }

    it('ac2 happy: badge disappears from decisions button when count changes 3 → 0', () => {
      setDRCount(3)
      const view = renderShell()
      // count=3 → badge must be present (fails until AC1 is implemented)
      expect(view.container.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
      // Transition to count=0
      setDRCount(0)
      rerenderShell(view)
      expect(view.container.querySelector('[data-testid="nav-badge"]')).toBeNull()
    })

    it('ac2 happy: no badge in entire nav-rail after count returns to 0 from 5', () => {
      setDRCount(5)
      const view = renderShell()
      // count=5 → badge present in nav-rail (fails until AC1 is implemented)
      expect(navRail(view.container).querySelector('[data-testid="nav-badge"]')).not.toBeNull()
      setDRCount(0)
      rerenderShell(view)
      expect(navRail(view.container).querySelector('[data-testid="nav-badge"]')).toBeNull()
    })

    it('ac2 boundary: badge absent at count=0 — count=1 shows badge, count=0 does not', () => {
      // count=1 is the minimum positive — must show badge (fails until AC1 implemented)
      setDRCount(1)
      const view = renderShell()
      expect(view.container.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
      // count=0 → badge must be absent (not zero-valued, fully absent from DOM)
      setDRCount(0)
      rerenderShell(view)
      expect(view.container.querySelector('[data-testid="nav-badge"]')).toBeNull()
    })

    it('ac2 edge: badge absent on /decisions route after count transitions 2 → 0', () => {
      setDRCount(2)
      const view = renderShell('/decisions')
      // count=2 → badge present (fails until AC1 implemented)
      expect(view.container.querySelector('[data-testid="nav-badge"]')).not.toBeNull()
      setDRCount(0)
      rerenderShell(view, '/decisions')
      expect(view.container.querySelector('[data-testid="nav-badge"]')).toBeNull()
    })
  })

  // ── AC3: aria-label reflects pending count ─────────────────────────────────

  describe('AC3 — decisions button aria-label updates with pending count', () => {
    it('ac3 happy: aria-label is "Decisions (3 pending)" when count=3', () => {
      setDRCount(3)
      const { container } = renderShell()
      expect(decisionsBtn(container).getAttribute('aria-label')).toBe('Decisions (3 pending)')
    })

    it('ac3 boundary: aria-label is "Decisions (1 pending)" when count=1', () => {
      setDRCount(1)
      const { container } = renderShell()
      expect(decisionsBtn(container).getAttribute('aria-label')).toBe('Decisions (1 pending)')
    })

    it('ac3 happy: aria-label is exactly "Decisions" when count=0', () => {
      // Uses rerender: proves aria-label reverts (count>0 assertion fails in RED)
      setDRCount(3)
      const view = renderShell()
      // count=3 → label must include count (fails until AC3 is implemented)
      expect(decisionsBtn(view.container).getAttribute('aria-label')).toBe('Decisions (3 pending)')
      // Transition to count=0 → label must revert to exactly "Decisions"
      setDRCount(0)
      view.rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <CockpitProvider>
              <Shell />
            </CockpitProvider>
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )
      expect(decisionsBtn(view.container).getAttribute('aria-label')).toBe('Decisions')
    })

    it('ac3 edge: aria-label contains the word "pending" when count > 0', () => {
      setDRCount(7)
      const { container } = renderShell()
      const label = decisionsBtn(container).getAttribute('aria-label') ?? ''
      expect(label).toContain('pending')
    })

    it('ac3 edge: aria-label does NOT contain "pending" after count reverts from 4 to 0', () => {
      setDRCount(4)
      const view = renderShell()
      // count=4 → label contains "pending" (fails until AC3 implemented)
      expect(decisionsBtn(view.container).getAttribute('aria-label')).toContain('pending')
      setDRCount(0)
      view.rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <CockpitProvider>
              <Shell />
            </CockpitProvider>
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )
      expect(decisionsBtn(view.container).getAttribute('aria-label')).not.toContain('pending')
    })
  })
})
