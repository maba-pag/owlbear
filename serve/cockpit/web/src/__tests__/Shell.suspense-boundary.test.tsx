/**
 * Durable Suspense-boundary contracts for Shell route loading.
 *
 * Consolidates archived lazy-route fallback coverage from task #1644.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

vi.mock('../routes', async () => {
  const { lazy } = await import('react')
  const SuspendingComponent = lazy((): Promise<never> => new Promise(() => {}))
  return {
    routeConfig: [{ path: '/', label: 'Kanban', icon: 'kanban', component: SuspendingComponent }],
  }
})

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
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
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

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

describe('ShellSuspenseBoundaryContracts', () => {
  it('shows the route-loading fallback while a lazy route component is still suspending', () => {
    renderShell('/')
    expect(screen.getByTestId('route-loading')).not.toBeNull()
  })
})
