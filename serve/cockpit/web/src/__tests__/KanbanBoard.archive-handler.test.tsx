/**
 * Implement handleTransitionClick archive intercept.
 *
 * Covers:
 *   AC1 — handleTransitionClick opens ArchivalModal instead of immediately POSTing
 *          when targetStatus === "archived"
 *   AC2 — Non-archival transitions are unchanged (POST still fires)
 *   AC3 — ArchivalModal receives taskId, taskStatus, expectedUpdated props
 *   AC4 — expectedUpdated is frozen at context-menu-open time; not re-read from a
 *          polling-updated task reference while the modal is open
 *   AC5 (lifecycle) — onClose callback dismisses the modal (setArchivalModal(null))
 *   AC5 (lifecycle) — onRefresh callback invokes the refetchTasks prop
 *
 * Note: task.status passed as taskStatus reflects the LIVE status at click time
 * (tasks.find(...)?.status), not the frozen context-menu-open status — this is
 * correct per brief F3 ("task.status at intercept time, for completed filter").
 *
 * Harness: KanbanBoard is prop-driven (board + tasks passed directly). ArchivalModal
 * is stubbed via vi.mock to (a) expose props as data-attributes, and (b) capture
 * onClose / onRefresh callbacks for lifecycle assertions.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

// ─── ArchivalModal stub ───────────────────────────────────────────────────────
// Captures all 5 props so:
//   - data-attributes let us assert AC3 values
//   - captured callbacks let us drive AC5 lifecycle tests
interface ModalStubProps {
  taskId: number
  taskStatus: string
  expectedUpdated: string
  onClose: () => void
  onRefresh: () => void
}

let capturedOnClose: (() => void) | null = null
let capturedOnRefresh: (() => void) | null = null

vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(
    ({ taskId, taskStatus, expectedUpdated, onClose, onRefresh }: ModalStubProps) => {
      capturedOnClose = onClose
      capturedOnRefresh = onRefresh
      return (
        <div
          data-testid="archival-modal-stub"
          data-task-id={String(taskId)}
          data-task-status={taskStatus}
          data-expected-updated={expectedUpdated}
        />
      )
    },
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

// Board: done → archived (F3 intercept target); backlog → todo (AC2 regression guard)
const BOARD = {
  statuses: [
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'done' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'done'],
    done: ['archived'],
  } as Record<string, string[]>,
}

const TASK_DONE = {
  id: 1,
  title: 'Completed task',
  status: 'done',
  priority: 'needed',
  updated: '2026-01-01T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

const TASK_BACKLOG = {
  id: 2,
  title: 'Backlog task',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-01-02T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

// ─── Fetch stub ───────────────────────────────────────────────────────────────

function stubFetch() {
  const mockFetch = vi.fn((url: string) => {
    if (/\/api\/tasks\/\d+\/move/.test(url)) {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`))
  })
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderBoard(refetchSpy = vi.fn()) {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={[TASK_DONE, TASK_BACKLOG]}
          loading={false}
          error={null}
          refetchTasks={refetchSpy}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Context-menu helper ──────────────────────────────────────────────────────

async function openContextMenuForTask(container: HTMLElement, taskId: number) {
  await waitFor(() => {
    expect(
      container.querySelector(`[data-testid="task-card"][data-id="${taskId}"]`),
    ).not.toBeNull()
  })
  fireEvent.contextMenu(
    container.querySelector(`[data-testid="task-card"][data-id="${taskId}"]`)!,
  )
  await waitFor(() => {
    expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
  })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ArchiveIntercept', () => {
  beforeEach(() => {
    capturedOnClose = null
    capturedOnRefresh = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC1: archived click opens ArchivalModal, no immediate POST ────────────

  it('clicking → archived opens ArchivalModal instead of firing a move POST', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      expect(container.querySelector('[data-testid="archival-modal-stub"]')).not.toBeNull()
    })
  })

  it('clicking → archived does not fire POST /api/tasks/{id}/move immediately', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await new Promise((resolve) => setTimeout(resolve, 50))
    const moveCalls = mockFetch.mock.calls.filter(([url]: [string]) =>
      /\/api\/tasks\/\d+\/move/.test(url),
    )
    expect(moveCalls).toHaveLength(0)
  })

  it('context menu is dismissed after clicking → archived', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).toBeNull()
    })
  })

  // ─── AC2: non-archived transitions unchanged (regression guard) ────────────

  it('non-archived transition still fires POST /api/tasks/{id}/move', async () => {
    const mockFetch = stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 2) // backlog → todo
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="todo"]')!,
    )
    await waitFor(() => {
      const moveCalls = mockFetch.mock.calls.filter(([url]: [string]) =>
        /\/api\/tasks\/\d+\/move/.test(url),
      )
      expect(moveCalls).toHaveLength(1)
      expect(moveCalls[0][0]).toContain('/api/tasks/2/move')
    })
  })

  // ─── AC3: ArchivalModal receives correct props ─────────────────────────────

  it('ArchivalModal receives taskId matching the archived task', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      const modal = container.querySelector('[data-testid="archival-modal-stub"]')
      expect(modal?.getAttribute('data-task-id')).toBe('1')
    })
  })

  it('ArchivalModal receives taskStatus equal to task.status at click time', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1) // task status = 'done'
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      const modal = container.querySelector('[data-testid="archival-modal-stub"]')
      expect(modal?.getAttribute('data-task-status')).toBe('done')
    })
  })

  it('ArchivalModal receives expectedUpdated equal to task.updated at context-menu-open time', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1) // updated = '2026-01-01T00:00:00+00:00'
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await waitFor(() => {
      const modal = container.querySelector('[data-testid="archival-modal-stub"]')
      expect(modal?.getAttribute('data-expected-updated')).toBe('2026-01-01T00:00:00+00:00')
    })
  })

  // ─── AC4: expectedUpdated frozen at context-menu-open time ─────────────────

  it('expectedUpdated is frozen at menu-open time even when tasks rerender with updated value', async () => {
    const FROZEN = '2026-01-01T00:00:00+00:00'
    const POLLED = '2026-02-01T00:00:00+00:00'

    stubFetch()

    const { container, rerender } = render(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <KanbanBoard
            board={BOARD}
            tasks={[TASK_DONE, TASK_BACKLOG]}
            loading={false}
            error={null}
            refetchTasks={vi.fn()}
          />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    await openContextMenuForTask(container, 1)

    // Simulate polling update arriving after menu opened
    rerender(
      <PorscheDesignSystemProvider>
        <MemoryRouter>
          <KanbanBoard
            board={BOARD}
            tasks={[{ ...TASK_DONE, updated: POLLED }, TASK_BACKLOG]}
            loading={false}
            error={null}
            refetchTasks={vi.fn()}
          />
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )
    await act(async () => {})

    const modal = container.querySelector('[data-testid="archival-modal-stub"]')
    expect(modal).not.toBeNull()
    expect(modal?.getAttribute('data-expected-updated')).toBe(FROZEN)
  })
})

describe('TestFromAC_ModalLifecycle', () => {
  beforeEach(() => {
    capturedOnClose = null
    capturedOnRefresh = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC5 (lifecycle): onClose dismisses the modal ─────────────────────────

  it('invoking the onClose callback dismisses ArchivalModal', async () => {
    stubFetch()
    const { container } = renderBoard()
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )

    await waitFor(() => {
      expect(container.querySelector('[data-testid="archival-modal-stub"]')).not.toBeNull()
      expect(capturedOnClose).not.toBeNull()
    })

    act(() => {
      capturedOnClose?.()
    })

    await waitFor(() => {
      expect(container.querySelector('[data-testid="archival-modal-stub"]')).toBeNull()
    })
  })

  // ─── AC5 (lifecycle): onRefresh invokes refetchTasks ──────────────────────

  it('invoking the onRefresh callback calls the refetchTasks prop', async () => {
    stubFetch()
    const refetchSpy = vi.fn()
    const { container } = renderBoard(refetchSpy)
    await openContextMenuForTask(container, 1)
    fireEvent.click(
      container.querySelector('[data-testid="transition-item"][data-status="archived"]')!,
    )

    await waitFor(() => {
      expect(container.querySelector('[data-testid="archival-modal-stub"]')).not.toBeNull()
      expect(capturedOnRefresh).not.toBeNull()
    })

    act(() => {
      capturedOnRefresh?.()
    })

    expect(refetchSpy).toHaveBeenCalledTimes(1)
  })
})

