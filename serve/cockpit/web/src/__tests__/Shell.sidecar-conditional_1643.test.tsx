/**
 * Task #1643 — P1-03: retired route-conditional sidecar contract
 * Tests that task detail no longer occupies the PCanvas end sidebar and route
 * navigation does not restore the old sidecar.
 *
 * Real routeConfig (routes.ts) is intentionally NOT mocked — these are integration
 * tests that lock in the no-right-sidecar shell contract.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
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

  // ── AC2: navigation keeps the task sidecar retired ───────────────────────

  it('ac2 happy: navigating from / to /decisions keeps sidecar absent', async () => {
    const { container } = renderShellWithNav('/')
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    // Navigate to /decisions
    fireEvent.click(container.querySelector('[data-testid="go-decisions"]')!)
    // Sidecar must be absent after navigation
    await waitFor(() => {
      expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    })
  })

  it('ac2 happy: navigating from /decisions back to / does not restore sidecar', () => {
    const { container } = renderShellWithNav('/decisions')
    // Start at /decisions — sidecar absent
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    // Navigate back to /
    fireEvent.click(container.querySelector('[data-testid="go-home"]')!)
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
  })

  it('ac2 edge: legacy custom sidecar-collapse control is absent after PCanvas migration', async () => {
    const { container } = renderShellWithNav('/')
    expect(container.querySelector('[data-testid="sidecar-collapse"]')).toBeNull()

    fireEvent.click(container.querySelector('[data-testid="go-decisions"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    })

    fireEvent.click(container.querySelector('[data-testid="go-home"]')!)
    await waitFor(() => {
      expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
      expect(container.querySelector('[data-testid="sidecar-collapse"]')).toBeNull()
    })
  })

  // ── AC3: shell declares no-right-sidecar layout ───────────────────────────

  it('ac3 happy: shell element carries data-no-sidecar attribute on /decisions route', () => {
    const { container } = renderShell('/decisions')
    const shell = container.querySelector('.shell')
    expect(shell).not.toBeNull()
    expect(shell!.hasAttribute('data-no-sidecar')).toBe(true)
  })

})
