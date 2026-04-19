/**
 * Failing tests for #966: traffic-light wiring in Shell
 *
 * Shell.tsx must call usePolling('/health') and bind the returned health
 * state to data-health on the [data-testid="traffic-light"] span.
 * All tests are RED (failing) until the builder implements the wiring.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { HealthState } from '../hooks/usePolling'

// ─── Module mock ──────────────────────────────────────────────────────────────
// usePolling is mocked so tests control which health state Shell receives.
// The factory produces a vi.fn() with no default impl; beforeEach sets it.
vi.mock('../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}))

import { usePolling } from '../hooks/usePolling'

// ─── Helpers ──────────────────────────────────────────────────────────────────
function stubHealth(health: HealthState) {
  vi.mocked(usePolling).mockReturnValue({ health, skipNextPoll: vi.fn(), lastMtime: null })
}

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <Shell />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

import Shell from '../Shell'

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('TestFromAC_TrafficLight', () => {
  beforeEach(() => {
    // KanbanBoard fires fetch on mount; never-resolving keeps it in loading
    // state, preventing act() warnings.
    vi.stubGlobal('fetch', vi.fn(() => new Promise<never>(() => {})))
    stubHealth('green')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── Happy path: green ────────────────────────────────────────────────────

  describe('green state', () => {
    it('traffic-light span carries data-health="green" when poll is healthy', () => {
      stubHealth('green')
      const { container } = renderShell()
      const span = container.querySelector('[data-testid="traffic-light"]')
      expect(span?.getAttribute('data-health')).toBe('green')
    })
  })

  // ─── Boundary: yellow ─────────────────────────────────────────────────────

  describe('yellow state', () => {
    it('traffic-light span carries data-health="yellow" when poll is stale', () => {
      stubHealth('yellow')
      const { container } = renderShell()
      const span = container.querySelector('[data-testid="traffic-light"]')
      expect(span?.getAttribute('data-health')).toBe('yellow')
    })
  })

  // ─── Error path: red ──────────────────────────────────────────────────────

  describe('red state', () => {
    it('traffic-light span carries data-health="red" when poll has errored', () => {
      stubHealth('red')
      const { container } = renderShell()
      const span = container.querySelector('[data-testid="traffic-light"]')
      expect(span?.getAttribute('data-health')).toBe('red')
    })
  })

  // ─── Wiring: correct URL ──────────────────────────────────────────────────

  describe('usePolling wiring', () => {
    it('Shell calls usePolling with /health endpoint', () => {
      renderShell()
      expect(vi.mocked(usePolling)).toHaveBeenCalledWith('/health')
    })
  })
})
