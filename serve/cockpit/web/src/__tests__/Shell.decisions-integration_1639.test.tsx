/**
 * Task #1639 — P1-01: Tab routing infrastructure
 * Retry: AC2 integration proof (gap from Review Evidence finding #1)
 *
 * The prior Shell.tab-routing_1639.test.tsx mocked '../routes', so no test
 * would fail if the real /decisions routeConfig entry pointed to the wrong
 * component. This file renders Shell with the REAL routeConfig to lock in
 * the wiring between the /decisions path and DecisionsPage.
 *
 * '../routes' is intentionally NOT mocked here.
 */
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// Stub fetch with a never-resolving promise so board/scan/DR hooks stay in
// loading state without triggering state updates after assertions.
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

function renderShell(route: string) {
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

describe('TestFromAC_DecisionsIntegration', () => {
  // ── AC2 integration: real routeConfig → real DecisionsPage ───────────────

  it('ac2 integration happy: real routeConfig wires /decisions to DecisionsPage testid', () => {
    // If routeConfig["/decisions"].component were changed to any other component,
    // data-testid="decisions-page" would not appear and this test would fail.
    renderShell('/decisions')
    expect(screen.getByTestId('decisions-page')).not.toBeNull()
  })

  it('ac2 integration boundary: decisions-page testid absent at / (path-specific routing)', () => {
    // Confirms the testid is rendered only for the /decisions path, not all routes.
    renderShell('/')
    expect(screen.queryByTestId('decisions-page')).toBeNull()
  })

  it('ac2 integration edge: decisions-page testid absent at unmatched route', () => {
    // No route match → no route component rendered → testid absent.
    renderShell('/unknown-path')
    expect(screen.queryByTestId('decisions-page')).toBeNull()
  })
})
