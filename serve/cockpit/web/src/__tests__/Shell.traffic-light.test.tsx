/**
 * traffic-light wiring in Shell
 *
 * Shell.tsx must bind useBoard().health
 * to data-health on the [data-testid="traffic-light"] span.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import { useBoard } from '../hooks/useBoard'
import type { Board, Task } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

// ─── Module mock ──────────────────────────────────────────────────────────────
vi.mock('../hooks/useBoard', () => ({
  useBoard: vi.fn(),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(),
}))

// Shell renders ActivityTab which calls useSSEEvent — mock the provider hook so
// tests are not broken by missing EventSourceProvider context after PDS v4 alignment.
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kb-stub" />),
}))

// ─── Helpers ──────────────────────────────────────────────────────────────────
const MOCK_BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

const MOCK_TASKS: Task[] = [
  {
    id: 1,
    title: 'Task one',
    status: 'todo',
    priority: 'needed',
    updated: '2026-01-01T00:00:00Z',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

type HealthState = 'green' | 'yellow' | 'red'

function stubHealth(health: HealthState) {
  vi.mocked(useBoard).mockReturnValue({
    board: MOCK_BOARD,
    tasks: MOCK_TASKS,
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health,
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)
}

function stubAuxHooks() {
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)

  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)
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

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('TestFromAC_TrafficLight', () => {
  beforeEach(() => {
    stubAuxHooks()
    stubHealth('green')
  })

  afterEach(() => {
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

  describe('useBoard wiring', () => {
    it('Shell calls useBoard and uses it as the traffic-light source', () => {
      renderShell()
      expect(vi.mocked(useBoard)).toHaveBeenCalled()
    })
  })
})
