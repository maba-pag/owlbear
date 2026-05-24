/**
 * Durable Shell integration contracts for the real /decisions route wiring.
 *
 * Consolidates archived route-to-page integration coverage from task #1639.
 */

import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { act } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

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

describe('ShellDecisionsIntegrationContracts', () => {
  it('renders the DecisionsPage test id when the real /decisions route is matched', async () => {
    await act(async () => {
      renderShell('/decisions')
    })

    await waitFor(() => {
      expect(screen.getByTestId('decisions-page')).not.toBeNull()
    })
  })

  it('does not render the DecisionsPage test id at the home route', () => {
    renderShell('/')
    expect(screen.queryByTestId('decisions-page')).toBeNull()
  })

  it('does not render the DecisionsPage test id for an unmatched route', () => {
    renderShell('/unknown-path')
    expect(screen.queryByTestId('decisions-page')).toBeNull()
  })
})
