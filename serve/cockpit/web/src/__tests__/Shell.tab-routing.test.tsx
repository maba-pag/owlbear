/**
 * Task #1639 — P1-01: Tab routing infrastructure
 * AC1 coverage: Shell renders route components from routeConfig
 * AC2 coverage: /decisions route component is called; / renders kanban with existing props
 * AC3 coverage: extra entry in routeConfig renders without modifying Shell.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Hoisted stubs ────────────────────────────────────────────────────────────
// vi.hoisted runs before module imports are evaluated.
// No JSX — all stubs return null (React.FC<any> is satisfied by () => null).

const {
  MockKanbanRouteComponent,
  MockDecisionsComponent,
  MockCustomComponent,
  getKanbanRouteProps,
  getDecisionsRouteProps,
  getCustomRouteProps,
} =
  vi.hoisted(() => {
    let capturedKanbanProps: Record<string, unknown> = {}
    let capturedDecisionsProps: Record<string, unknown> = {}
    let capturedCustomProps: Record<string, unknown> = {}

    const MockKanbanRouteComponent = vi.fn((props: unknown) => {
      capturedKanbanProps = props as Record<string, unknown>
      return null
    })
    const MockDecisionsComponent = vi.fn((props: unknown) => {
      capturedDecisionsProps = props as Record<string, unknown>
      return null
    })
    const MockCustomComponent = vi.fn((props: unknown) => {
      capturedCustomProps = props as Record<string, unknown>
      return null
    })

    return {
      MockKanbanRouteComponent,
      MockDecisionsComponent,
      MockCustomComponent,
      getKanbanRouteProps: () => capturedKanbanProps,
      getDecisionsRouteProps: () => capturedDecisionsProps,
      getCustomRouteProps: () => capturedCustomProps,
    }
  })

// ─── Module mocks ─────────────────────────────────────────────────────────────

// Controlled routeConfig: 2 real entries + 1 extension entry (AC3 proof).
vi.mock('../routes', () => ({
  routeConfig: [
    { path: '/', label: 'Kanban', icon: 'kanban', component: MockKanbanRouteComponent },
    { path: '/decisions', label: 'Decisions', icon: 'decisions', component: MockDecisionsComponent },
    { path: '/custom-test', label: 'Custom', icon: 'custom-icon', component: MockCustomComponent },
  ],
}))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))
vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))
vi.mock('../hooks/useWorkspaceHealth', () => ({
  useWorkspaceHealth: vi.fn(() => ({
    health: { status: 'healthy', modules: {} },
    connectionError: null,
    isFetching: false,
    receipt: null,
    refresh: vi.fn(),
    refreshAfterMutation: vi.fn(),
    mergeRepair: vi.fn(),
    dismissReceipt: vi.fn(),
  })),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => null),
}))
vi.mock('../components/ActivityTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DetailTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DRStatusIndicator', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/RepairPanel', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ResolveModal', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ThemeToggle', () => ({ default: vi.fn(() => null) }))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { Board, Task } from '../hooks/useBoard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

const MOCK_TASKS: Task[] = [
  {
    id: 42,
    title: 'Sample task',
    status: 'todo',
    priority: 'needed',
    updated: '2026-01-01T00:00:00Z',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

function stubShellHooks(): void {
  vi.mocked(useBoard).mockReturnValue({
    board: MOCK_BOARD,
    tasks: MOCK_TASKS,
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)

  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)

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

describe('ShellTabRouting', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    stubShellHooks()
  })

  // ── AC1: Shell renders route components via routeConfig map ───────────────

  it('ac1 happy: kanban component from routeConfig is rendered at "/"', () => {
    renderShell('/')
    expect(MockKanbanRouteComponent).toHaveBeenCalled()
  })

  it('ac1 happy: decisions component from routeConfig is rendered at "/decisions"', () => {
    renderShell('/decisions')
    expect(MockDecisionsComponent).toHaveBeenCalled()
  })

  // ── AC2: DecisionsPage route component activation ─────────────────────────
  // data-testid="decisions-page" contract is in DecisionsPage_1639.test.tsx.

  it('ac2 happy: decisions route component is invoked exactly once at "/decisions"', () => {
    renderShell('/decisions')
    expect(MockDecisionsComponent).toHaveBeenCalledTimes(1)
  })

  // ── AC2: KanbanBoard receives existing props unchanged ────────────────────

  it('ac2 regression: kanban route component receives board prop at "/"', () => {
    renderShell('/')
    expect(getKanbanRouteProps()).toHaveProperty('board')
    expect(getKanbanRouteProps().board).toEqual(MOCK_BOARD)
  })

  it('ac2 regression: kanban route component receives tasks prop at "/"', () => {
    renderShell('/')
    expect(getKanbanRouteProps()).toHaveProperty('tasks')
    expect(getKanbanRouteProps().tasks).toEqual(MOCK_TASKS)
  })

  it('ac2 regression: kanban route component receives loading and error props at "/"', () => {
    renderShell('/')
    const props = getKanbanRouteProps()
    expect(props).toHaveProperty('loading')
    expect(props).toHaveProperty('error')
  })

  it('ac2 regression: kanban route component receives onSelectTask callback at "/"', () => {
    renderShell('/')
    expect(typeof getKanbanRouteProps().onSelectTask).toBe('function')
  })

  it('ac2 regression: kanban route component receives refetchTasks callback at "/"', () => {
    renderShell('/')
    expect(typeof getKanbanRouteProps().refetchTasks).toBe('function')
  })

  it('ac2 regression: decisions route component receives no kanban board props', () => {
    renderShell('/decisions')
    expect(getDecisionsRouteProps()).toEqual({})
  })

  // ── AC3: extra routeConfig entry renders without modifying Shell.tsx ───────

  it('ac3 happy: extra route entry renders at its path without Shell.tsx modification', () => {
    renderShell('/custom-test')
    expect(MockCustomComponent).toHaveBeenCalled()
  })

  it('ac3 regression: non-kanban extension route receives no kanban board props', () => {
    renderShell('/custom-test')
    expect(getCustomRouteProps()).toEqual({})
  })

  it('ac3 happy: kanban route renders when extra entry is present', () => {
    // Verify extra entry does not break "/" route resolution.
    renderShell('/')
    expect(MockKanbanRouteComponent).toHaveBeenCalled()
  })

  it('ac3 happy: decisions route renders when extra entry is present', () => {
    // Verify extra entry does not break "/decisions" route resolution.
    renderShell('/decisions')
    expect(MockDecisionsComponent).toHaveBeenCalled()
  })

  it('ac3 boundary: only one route component is called per navigation', () => {
    // Shell must render exactly one matched component; no multi-route rendering.
    renderShell('/decisions')
    expect(MockDecisionsComponent).toHaveBeenCalledTimes(1)
    expect(MockKanbanRouteComponent).toHaveBeenCalledTimes(0)
    expect(MockCustomComponent).toHaveBeenCalledTimes(0)
  })
})
