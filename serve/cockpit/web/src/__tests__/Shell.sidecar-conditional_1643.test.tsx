/**
 * Task #1643 — P1-03: Route-conditional sidecar
 * Tests sidecar conditional rendering, navigation state, and grid column adjustment
 * based on the routeConfig entry's `hasSidecar` field.
 *
 * Real routeConfig (routes.ts) is intentionally NOT mocked — these are integration
 * tests that lock in the wiring between /decisions and hasSidecar:false suppression.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter, useNavigate } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// Never-resolving fetch keeps board/scan/DR hooks in loading state, preventing
// React state updates after assertions and eliminating act() warnings.
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

/** Navigation helper rendered inside the same MemoryRouter as Shell. */
function NavHelper({ testId, to }: { testId: string; to: string }) {
  const navigate = useNavigate()
  return <button data-testid={testId} onClick={() => navigate(to)} />
}

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

/** Renders Shell with navigation helpers inside the same MemoryRouter context. */
function renderShellWithNav(startRoute = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[startRoute]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
        <NavHelper testId="go-decisions" to="/decisions" />
        <NavHelper testId="go-home" to="/" />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

describe('TestFromAC_SidecarConditional', () => {
  // ── AC1: sidecar absent from DOM on /decisions ────────────────────────────

  it('ac1 happy: [data-region="sidecar"] absent from DOM on /decisions route', () => {
    const { container } = renderShell('/decisions')
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })

  // ── AC2: navigation removes and restores sidecar ──────────────────────────

  it('ac2 happy remove: navigating from / to /decisions removes sidecar from DOM', () => {
    const { container } = renderShellWithNav('/')
    // Sidecar present at /
    expect(container.querySelector('[data-region="sidecar"]')).not.toBeNull()
    // Navigate to /decisions
    fireEvent.click(container.querySelector('[data-testid="go-decisions"]')!)
    // Sidecar must be absent after navigation
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })

  it('ac2 happy restore: navigating from /decisions back to / restores sidecar in DOM', () => {
    const { container } = renderShellWithNav('/decisions')
    // Start at /decisions — sidecar absent
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    // Navigate back to /
    fireEvent.click(container.querySelector('[data-testid="go-home"]')!)
    // Sidecar must be restored
    expect(container.querySelector('[data-region="sidecar"]')).not.toBeNull()
  })

  it('ac2 edge preserve-collapsed: isSidecarCollapsed state persists through / → /decisions → / round-trip', () => {
    const { container } = renderShellWithNav('/')
    // Collapse the sidecar at /
    const toggle = container.querySelector('[data-testid="sidecar-collapse"]') as HTMLButtonElement
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    // Navigate to /decisions — sidecar removed from DOM
    fireEvent.click(container.querySelector('[data-testid="go-decisions"]')!)
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    // Navigate back to / — sidecar restored in its previous collapsed state
    fireEvent.click(container.querySelector('[data-testid="go-home"]')!)
    const restoredToggle = container.querySelector('[data-testid="sidecar-collapse"]') as HTMLButtonElement
    expect(restoredToggle.getAttribute('aria-expanded')).toBe('false')
  })

  // ── AC3: shell grid narrows to 2 columns when sidecar is absent ───────────

  it('ac3 happy: shell element carries data-no-sidecar attribute on /decisions route', () => {
    const { container } = renderShell('/decisions')
    const shell = container.querySelector('.shell')
    expect(shell).not.toBeNull()
    // data-no-sidecar drives the CSS --shell-columns override to 2-column layout
    expect(shell!.hasAttribute('data-no-sidecar')).toBe(true)
  })

})
