/**
 * RED phase tests for #1227: Frontend polling refactor — Shell integration
 *
 * AC1 (td:2): /health polling removed; connection health derived from tasks poll.
 *   Traffic-light reflects tasks-poll health via useBoard (not /health endpoint).
 * AC4 (td:2): Tasks poll owned at Shell level; KanbanBoard receives board+tasks
 *   via props — no duplicate /api/tasks fetches, no internal useBoard call in KB.
 * AC5 (td:1): Traffic light visible (with board health) on all routes, including /hello.
 *
 * All tests FAIL until the builder implements the refactor in Shell.tsx,
 * useBoard.ts, and KanbanBoard.tsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../hooks/useBoard', () => ({
  useBoard: vi.fn(),
}))

vi.mock('../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}))

vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

// KanbanBoard spy: captures props passed by Shell
vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kb-stub" />),
  useBoard: vi.fn(),
}))

import { useBoard } from '../hooks/useBoard'
import type { Board, Task } from '../hooks/useBoard'
import { usePolling } from '../hooks/usePolling'
import { useScanPolling } from '../hooks/useScanPolling'
import { usePendingDRs } from '../hooks/usePendingDRs'
import KanbanBoard from '../KanbanBoard'
import Shell from '../Shell'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

const MOCK_TASKS: Task[] = [
  {
    id: 1,
    title: 'A task',
    status: 'todo',
    priority: 'needed',
    updated: '2026-01-01T00:00:00Z',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

// ─── Stub helpers ─────────────────────────────────────────────────────────────

type UseBoardHealth = 'green' | 'yellow' | 'red'

function stubUseBoard(health: UseBoardHealth = 'green'): void {
  // After refactoring, useBoard returns health derived from tasks-poll success/failure.
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

function stubUsePolling(): void {
  vi.mocked(usePolling).mockReturnValue({ health: 'green', skipNextPoll: vi.fn(), lastMtime: null })
}

function stubScan(): void {
  vi.mocked(useScanPolling).mockReturnValue({ items: [], isLoading: false, error: null, refetch: vi.fn() })
}

function stubPendingDRs(): void {
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <Shell />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_PollingRefactorShell', () => {
  beforeEach(() => {
    stubUseBoard()
    stubUsePolling()
    stubScan()
    stubPendingDRs()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // ─── AC1: Health derived from tasks poll — not /health endpoint ───────────

  describe('AC1: traffic-light reflects tasks-poll health', () => {
    it('traffic-light shows green when useBoard health is green (usePolling returns red to distinguish)', () => {
      // useBoard (tasks poll) reports green; usePolling (/health) reports red.
      // Shell must use useBoard's health — not usePolling's — for the traffic-light.
      stubUseBoard('green')
      // Override usePolling to return 'red' so the test distinguishes health sources:
      // if Shell reads from usePolling it shows 'red'; if from useBoard it shows 'green'.
      vi.mocked(usePolling).mockReturnValue({ health: 'red', skipNextPoll: vi.fn(), lastMtime: null })
      const { container } = renderShell()
      const tl = container.querySelector('[data-testid="traffic-light"]')
      // FAILS: Shell currently reads health from usePolling → shows 'red', not 'green'
      expect(tl).not.toBeNull()
      expect(tl?.getAttribute('data-health')).toBe('green')
    })

    it('traffic-light shows yellow when useBoard health is yellow (tasks-poll degraded)', () => {
      // useBoard (tasks poll) reports degraded health
      stubUseBoard('yellow')
      // usePolling (old /health poll) still returns green — Shell must NOT use this
      stubUsePolling()
      const { container } = renderShell()
      const tl = container.querySelector('[data-testid="traffic-light"]')
      // FAILS: Shell currently reads health from usePolling → shows 'green', not 'yellow'
      expect(tl?.getAttribute('data-health')).toBe('yellow')
    })

    it('traffic-light shows red when useBoard health is red (tasks-poll failed)', () => {
      stubUseBoard('red')
      stubUsePolling()
      const { container } = renderShell()
      const tl = container.querySelector('[data-testid="traffic-light"]')
      // FAILS: Shell binds to usePolling health → shows 'green', not 'red'
      expect(tl?.getAttribute('data-health')).toBe('red')
    })

    it('Shell does NOT call usePolling with the /health endpoint', () => {
      renderShell()
      // FAILS: Shell.tsx currently calls usePolling('/health')
      expect(vi.mocked(usePolling)).not.toHaveBeenCalledWith('/health')
    })
  })

  // ─── AC4: Tasks poll owned at Shell level — KanbanBoard receives props ────

  describe('AC4: Shell owns tasks poll; KanbanBoard receives board data as props', () => {
    it('Shell calls useBoard() on mount', () => {
      renderShell()
      // FAILS: Shell.tsx currently does not import or call useBoard
      expect(vi.mocked(useBoard)).toHaveBeenCalled()
    })

    it('KanbanBoard receives the board object as a prop from Shell', () => {
      renderShell()
      // FAILS: Shell currently renders <KanbanBoard /> with no props
      expect(vi.mocked(KanbanBoard)).toHaveBeenCalledWith(
        expect.objectContaining({ board: MOCK_BOARD }),
        expect.anything(),
      )
    })

    it('KanbanBoard receives the tasks array as a prop from Shell', () => {
      renderShell()
      // FAILS: Shell currently renders <KanbanBoard /> with no props
      expect(vi.mocked(KanbanBoard)).toHaveBeenCalledWith(
        expect.objectContaining({ tasks: MOCK_TASKS }),
        expect.anything(),
      )
    })

    it('KanbanBoard receives refetchTasks as a prop from Shell', () => {
      renderShell()
      // FAILS: Shell currently renders <KanbanBoard /> with no props.
      // After refactoring, Shell passes refetchTasks so KanbanBoard can
      // trigger manual re-polls (routed through health-marking path).
      expect(vi.mocked(KanbanBoard)).toHaveBeenCalledWith(
        expect.objectContaining({ refetchTasks: expect.any(Function) }),
        expect.anything(),
      )
    })
  })

  // ─── AC5: Traffic light visible with board health on all routes ───────────

  describe('AC5: traffic-light shows board health on non-board routes', () => {
    it('/hello route: traffic-light reflects tasks-poll health (yellow)', () => {
      stubUseBoard('yellow')
      const { container } = renderShell('/hello')
      const tl = container.querySelector('[data-testid="traffic-light"]')
      // FAILS: Shell uses usePolling('/health') → shows 'green', not 'yellow'
      expect(tl).not.toBeNull()
      expect(tl?.getAttribute('data-health')).toBe('yellow')
    })
  })
})
