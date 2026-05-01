/**
 * RED phase tests for #1228: Wire DetailTab + ActivityTab into sidecar.
 *
 * Covers:
 *   AC1 (td:2) — Card click sets Shell selectedTaskId, propagated to KanbanBoard
 *   AC2 (td:2) — Selected task fetched via GET /api/tasks/{id}, passed to DetailTab;
 *                null selection shows placeholder text in detail panel
 *   AC3 (td:1) — DetailTab mounted inside sidecar "Detail" tab-panel
 *   AC4 (td:1) — ActivityTab mounted inside sidecar "Activity" tab-panel;
 *                onSelectTask wired to Shell selection state
 *   AC6 (td:1) — /hello route removed from Shell
 *
 * All tests FAIL (RED phase) — Shell.tsx has not yet:
 *   - Added selectedTaskId state or onSelectTask prop to KanbanBoard
 *   - Mounted DetailTab or ActivityTab in the sidecar panels
 *   - Removed the /hello route
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted) ───────────────────────────────────────────────────

vi.mock('../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}))

vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/HealthBadge', () => ({
  default: vi.fn(() => null),
}))

// KanbanBoard mock: captures onSelectTask + selectedId props and exposes test
// buttons so tests can trigger task selection without real card rendering.
vi.mock('../KanbanBoard', () => ({
  default: vi.fn(
    ({
      onSelectTask,
      selectedId,
    }: {
      onSelectTask?: (taskId: number) => void
      selectedId?: number | null
    }) => (
      <div
        data-testid="kanban-board-mock"
        data-selected-id={selectedId === null ? 'null' : String(selectedId ?? 'undefined')}
      >
        <button data-testid="select-task-42" onClick={() => onSelectTask?.(42)}>
          Select 42
        </button>
        <button data-testid="select-task-99" onClick={() => onSelectTask?.(99)}>
          Select 99
        </button>
      </div>
    ),
  ),
}))

// DetailTab mock: exposes the task prop as a data attribute for assertions.
vi.mock('../components/DetailTab', () => ({
  default: vi.fn(
    ({
      task,
    }: {
      task?: { id: number } | null
      onSelectTask?: (taskId: number, subtab?: string) => void
    }) => (
      <div
        data-testid="detail-tab-mock"
        data-task-id={task ? String(task.id) : 'null'}
      />
    ),
  ),
}))

// ActivityTab mock: exposes whether onSelectTask was provided and has a button
// that fires it so cross-tab selection wiring can be tested.
vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(
    ({
      onSelectTask,
    }: {
      onSelectTask?: (taskId: number, subtab?: string) => void
    }) => (
      <div
        data-testid="activity-tab-mock"
        data-has-on-select-task={typeof onSelectTask === 'function' ? 'true' : 'false'}
      >
        <button
          data-testid="activity-select-99"
          onClick={() => onSelectTask?.(99)}
        >
          Select 99 from Activity
        </button>
      </div>
    ),
  ),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { usePolling } from '../hooks/usePolling'
import { useScanPolling } from '../hooks/useScanPolling'
import { usePendingDRs } from '../hooks/usePendingDRs'
import KanbanBoard from '../KanbanBoard'
import DetailTab from '../components/DetailTab'
import ActivityTab from '../components/ActivityTab'
import Shell from '../Shell'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK_42 = {
  id: 42,
  title: 'Task Forty-Two',
  status: 'todo',
  priority: 'needed',
  body: '',
  updated: '2026-01-01T00:00:00+00:00',
  created: '2026-01-01T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  claimed: false,
}

const TASK_99 = { ...TASK_42, id: 99, title: 'Task Ninety-Nine' }

// ─── Helpers ──────────────────────────────────────────────────────────────────

function stubHooks() {
  vi.mocked(usePolling).mockReturnValue({ health: 'green', skipNextPoll: vi.fn(), lastMtime: null })
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })
  vi.mocked(usePendingDRs).mockReturnValue({ count: 0, items: [], refetch: vi.fn() })
}

function stubFetch(taskMap: Record<number, object> = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const match = /\/api\/tasks\/(\d+)$/.exec(url)
      if (match) {
        const id = parseInt(match[1], 10)
        const data = taskMap[id]
        if (data) {
          return { ok: true, json: async () => data } as Response
        }
      }
      // Non-matched URLs pend until aborted (prevents act() warnings)
      return new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      })
    }),
  )
  return vi.mocked(fetch)
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

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_CardSelection', () => {
  beforeEach(() => {
    stubHooks()
    stubFetch()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC1 happy: Shell wires onSelectTask into KanbanBoard

  it('Shell passes an onSelectTask function prop to KanbanBoard', () => {
    renderShell()
    const calls = vi.mocked(KanbanBoard).mock.calls
    expect(calls.length).toBeGreaterThan(0)
    const props = calls[0][0]
    expect(typeof props.onSelectTask).toBe('function')
  })

  // AC1 boundary: selectedId starts null

  it('Shell passes selectedId=null to KanbanBoard before any card is clicked', () => {
    const { container } = renderShell()
    const board = container.querySelector('[data-testid="kanban-board-mock"]')
    expect(board).not.toBeNull()
    // Must be the string 'null', not 'undefined' — Shell owns the state at null
    expect(board!.getAttribute('data-selected-id')).toBe('null')
  })

  // AC1 happy: clicking a card stores its ID in Shell and propagates back

  it('invoking onSelectTask(42) propagates selectedId=42 to KanbanBoard', async () => {
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(() => {
      const board = container.querySelector('[data-testid="kanban-board-mock"]')
      expect(board!.getAttribute('data-selected-id')).toBe('42')
    })
  })

  // AC1 edge: clicking a different card moves selection

  it('clicking a second card replaces the first selection', async () => {
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="kanban-board-mock"]')!.getAttribute('data-selected-id'),
      ).toBe('42')
    })
    fireEvent.click(container.querySelector('[data-testid="select-task-99"]')!)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="kanban-board-mock"]')!.getAttribute('data-selected-id'),
      ).toBe('99')
    })
  })
})

describe('TestFromAC_TaskDetailFetch', () => {
  beforeEach(() => {
    stubHooks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC2 happy: selecting a task triggers GET /api/tasks/{id}

  it('selecting task 42 triggers GET /api/tasks/42', async () => {
    const mockFetch = stubFetch({ 42: TASK_42 })
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/tasks/42',
        expect.any(Object),
      )
    })
  })

  // AC2 happy: DetailTab receives fetched task data as props

  it('DetailTab receives the fetched task object after selection', async () => {
    stubFetch({ 42: TASK_42 })
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(() => {
      const mock = container.querySelector('[data-testid="detail-tab-mock"]')
      expect(mock).not.toBeNull()
      expect(mock!.getAttribute('data-task-id')).toBe('42')
    })
  })

  // AC2 edge: null selection shows placeholder text in detail panel

  it('detail panel shows placeholder text when no task is selected', () => {
    stubFetch()
    const { container } = renderShell()
    const detailPanel = container.querySelector('[data-tab-content="detail"]')
    expect(detailPanel).not.toBeNull()
    const placeholder = detailPanel!.querySelector('[data-testid="detail-placeholder"]')
    expect(placeholder).not.toBeNull()
  })

  // AC2 edge: changing selection triggers a new fetch

  it('changing selection from task 42 to task 99 fetches /api/tasks/99', async () => {
    const mockFetch = stubFetch({ 42: TASK_42, 99: TASK_99 })
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/tasks/42', expect.any(Object))
    })
    fireEvent.click(container.querySelector('[data-testid="select-task-99"]')!)
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/tasks/99', expect.any(Object))
    })
  })

  // AC2 boundary: DetailTab data updates to reflect new task after selection change

  it('DetailTab reflects the new task ID after selection changes from 42 to 99', async () => {
    stubFetch({ 42: TASK_42, 99: TASK_99 })
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="detail-tab-mock"]')!.getAttribute('data-task-id'),
      ).toBe('42')
    })
    fireEvent.click(container.querySelector('[data-testid="select-task-99"]')!)
    await waitFor(() => {
      expect(
        container.querySelector('[data-testid="detail-tab-mock"]')!.getAttribute('data-task-id'),
      ).toBe('99')
    })
  })
})

describe('TestFromAC_SidecarWiring', () => {
  beforeEach(() => {
    stubHooks()
    stubFetch()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC3: DetailTab mounted inside sidecar detail panel

  it('DetailTab is rendered inside [data-tab-content="detail"]', () => {
    const { container } = renderShell()
    const detailPanel = container.querySelector('[data-tab-content="detail"]')
    expect(detailPanel).not.toBeNull()
    expect(detailPanel!.querySelector('[data-testid="detail-tab-mock"]')).not.toBeNull()
  })

  // AC4: ActivityTab mounted inside sidecar activity panel

  it('ActivityTab is rendered inside [data-tab-content="activity"]', () => {
    const { container } = renderShell()
    const activityPanel = container.querySelector('[data-tab-content="activity"]')
    expect(activityPanel).not.toBeNull()
    expect(activityPanel!.querySelector('[data-testid="activity-tab-mock"]')).not.toBeNull()
  })

  // AC4: ActivityTab receives onSelectTask wired to Shell's setSelectedTaskId

  it('ActivityTab receives an onSelectTask prop; invoking it updates KanbanBoard selectedId', async () => {
    const { container } = renderShell()
    const activityMock = container.querySelector('[data-testid="activity-tab-mock"]')
    expect(activityMock).not.toBeNull()
    // Verify the prop was provided (not missing/undefined)
    expect(activityMock!.getAttribute('data-has-on-select-task')).toBe('true')
    // Invoke it via the activity tab's test button and verify Shell state propagates
    fireEvent.click(container.querySelector('[data-testid="activity-select-99"]')!)
    await waitFor(() => {
      const board = container.querySelector('[data-testid="kanban-board-mock"]')
      expect(board!.getAttribute('data-selected-id')).toBe('99')
    })
  })
})

describe('TestFromAC_HelloRouteRemoval', () => {
  beforeEach(() => {
    stubHooks()
    stubFetch()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC6: /hello route removed — navigating to /hello yields no hello content

  it('navigating to /hello does not render hello content in the workspace', () => {
    const { container } = renderShell('/hello')
    const workspace = container.querySelector('[data-region="workspace"]')
    expect(workspace).not.toBeNull()
    // The builder must remove the <Route path="/hello"> entry; after removal
    // the workspace area renders nothing (or falls through to the default route
    // without displaying the hello div).
    expect(workspace!.textContent).not.toContain('hello')
  })
})
